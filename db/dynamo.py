import boto3
import os

stage = os.environ.get("STAGE", "SANDBOX").upper()

dynamodb = boto3.resource('dynamodb')
appointments_table = dynamodb.Table(f'{stage}_APPOINTMENTS')
tokens_table = dynamodb.Table(f'{stage}_TOKENS')
clinics_table = dynamodb.Table(f'{stage}_CLINICS')
clinic_locations_table = dynamodb.Table(f'{stage}_CLINIC_LOCATIONS')
patients_table = dynamodb.Table(f'{stage}_PATIENTS')
s3_client = boto3.client('s3')


def get_appointment(clinic_id, appointment_id):
    dynamo_response = appointments_table.get_item(Key={"appointment_id": appointment_id}, ConsistentRead=True)
    appointment = dynamo_response.get("Item", None)
    if appointment["clinic_id"] != clinic_id:
        return None
    return appointment


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
                                               FilterExpression=boto3.dynamodb.conditions.Attr("clinic_id").eq(clinic_id))
    appointments = dynamo_response["Items"]
    return appointments

def put_appointment(appointment):
    appointments_table.put_item(Item=appointment)


def get_clinics():
    # TODO: Needs pagination (and optimization) when we start rolling in customers
    dynamo_response = clinics_table.scan()
    clinics = dynamo_response["Items"]
    return clinics


def get_clinic_locations():
    # TODO: Needs pagination (and optimization) when we start rolling in customers
    dynamo_response = clinic_locations_table.scan()
    clinic_locations = dynamo_response["Items"]
    return clinic_locations

def get_waitlist_priority(location_id, priority):
    dynamo_response = appointments_table.query(IndexName='waitlist-index',
                             KeyConditions={
                                 "clinic_location_id": {"AttributeValueList": [location_id],
                                                        "ComparisonOperator": "EQ"},
                                 "waitlist_priority": {"AttributeValueList": [priority],
                                                       "ComparisonOperator": "LT"}})
    return dynamo_response["Count"] + 1