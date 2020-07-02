import boto3
import os

stage = os.environ.get("STAGE", "SANDBOX").upper()

dynamodb = boto3.resource('dynamodb')
appointments_table = dynamodb.Table(f'{stage}_APPOINTMENTS')
tokens_table = dynamodb.Table(f'{stage}_TOKENS')
clinics_table = dynamodb.Table(f'{stage}_CLINICS')
clinic_locations_table = dynamodb.Table(f'{stage}_CLINIC_LOCATIONS')
patients_table = dynamodb.Table(f'{stage}_PATIENTS')
practitioners_table = dynamodb.Table(f'{stage}_PRACTITIONERS')
s3_client = boto3.client('s3')

def update_item(table, key, object):
    clinic_id = object.get("clinic_id", None)
    clinic_id = key.get("clinic_id", clinic_id)
    if not clinic_id:
        raise RuntimeError("Clinic id must be set on key or update object.")
    attribute_names = {}
    attribute_values = {}
    updates = []
    removes = []
    for x, attr in zip(range(len(object)), object.items()):
        attribute_name = f"#attribute{x}"
        attribute_value_name = f":attribute{x}"
        attribute_names[attribute_name] = attr[0]
        if attr[1] is not None:
            updates.append(f"{attribute_name} = {attribute_value_name}")
            attribute_values[attribute_value_name] = attr[1]
        else:
            removes.append(attribute_name)
    update_expression = ""
    if updates:
        update_expression += "SET " + ", ".join(updates)
    if removes:
        update_expression += " REMOVE " + ", ".join(removes)

    dynamo_response = table.update_item(
        Key = key,
        UpdateExpression = update_expression,
        ExpressionAttributeNames = attribute_names,
        ExpressionAttributeValues = attribute_values,
        ConditionExpression = boto3.dynamodb.conditions.Attr("clinic_id").eq(clinic_id),
        ReturnValues = "ALL_NEW"
    )
    return dynamo_response["Attributes"]



def get_practitioner(clinic_id, practitioner_id):
    dynamo_response = practitioners_table.get_item(Key={"clinic_id":clinic_id,
                                                        "practitioner_id":practitioner_id})
    practitioner = dynamo_response.get("Item", None)
    if practitioner['clinic_id'] != clinic_id:
        return None
    return practitioner

def update_practitioner(clinic_id, practitioner_id, practitioner):
    return update_item(practitioners_table, {"clinic_id" : clinic_id, "practitioner_id" : practitioner_id}, practitioner)


def get_appointment(clinic_id, appointment_id):
    dynamo_response = appointments_table.get_item(Key={"appointment_id": appointment_id}, ConsistentRead=True)
    appointment = dynamo_response.get("Item", None)
    if appointment["clinic_id"] != clinic_id:
        return None
    return appointment

def update_appointment(appointment_id, appointment):
    return update_item(appointments_table, {"appointment_id" : appointment_id}, appointment)

def get_clinic_location(clinic_id, clinic_location_id):
    dynamo_response = clinic_locations_table.get_item(Key={"clinic_id": clinic_id,
                                                           "clinic_location_id": clinic_location_id})
    clinic_location = dynamo_response.get("Item", None)
    return clinic_location


def get_token(token_id):
    dynamo_response = tokens_table.get_item(Key={"token_id": token_id})
    token = dynamo_response.get("Item", None)
    return token


def put_token(token):
    tokens_table.put_item(Item=token)


def get_patient(clinic_id, patient_id):
    dynamo_response = patients_table.get_item(Key={"patient_id": patient_id})
    patient = dynamo_response.get("Item", None)
    if patient["clinic_id"] != clinic_id:
        return None
    return patient


def list_appointments(clinic_id, start_time, end_time):
    dynamo_response = appointments_table.query(IndexName='clinic-index',
                                               KeyConditions={
                                                   "clinic_id": {"AttributeValueList": [clinic_id],
                                                                 "ComparisonOperator": "EQ"},
                                                   "appointment_time": {"AttributeValueList": [start_time, end_time],
                                                                        "ComparisonOperator": "BETWEEN"}})
    appointments = dynamo_response["Items"]
    return appointments


def list_appointments_by_location(clinic_id, clinic_location_id, start_time, end_time):
    dynamo_response = appointments_table.query(IndexName='clinic-location-index',
                                               KeyConditions={
                                                   "clinic_location_id": {"AttributeValueList": [clinic_location_id],
                                                                          "ComparisonOperator": "EQ"},
                                                   "appointment_time": {"AttributeValueList": [start_time, end_time],
                                                                        "ComparisonOperator": "BETWEEN"}},
                                               FilterExpression=boto3.dynamodb.conditions.Attr("clinic_id").eq(
                                                   clinic_id))
    appointments = dynamo_response["Items"]
    return appointments


def put_appointment(appointment):
    appointments_table.put_item(Item=appointment)


def get_clinics():
    # TODO: Needs pagination (and optimization) when we start rolling in customers
    dynamo_response = clinics_table.scan()
    clinics = dynamo_response["Items"]
    return clinics

def update_patient(patient_id, patient):
    return update_item(patients_table, {"patient_id" : patient_id}, patient)

def get_clinic_locations():
    # TODO: Needs pagination (and optimization) when we start rolling in customers
    dynamo_response = clinic_locations_table.scan()
    clinic_locations = dynamo_response["Items"]
    return clinic_locations

def update_clinic_location(clinic_id, clinic_location_id, clinic_location):
    return update_item(clinic_locations_table, {"clinic_id" : clinic_id, "clinic_location_id" : clinic_location_id}, clinic_location)


def get_waitlist_priority(location_id, priority):
    dynamo_response = appointments_table.query(IndexName='waitlist-index',
                                               KeyConditions={
                                                   "clinic_location_id": {"AttributeValueList": [location_id],
                                                                          "ComparisonOperator": "EQ"},
                                                   "waitlist_priority": {"AttributeValueList": [priority],
                                                                         "ComparisonOperator": "LT"}})
    return dynamo_response["Count"] + 1
