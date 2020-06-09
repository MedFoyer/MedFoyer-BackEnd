import json
import time
import boto3
import uuid
from geopy import distance

dynamodb = boto3.resource('dynamodb')
appointments_table = dynamodb.Table('SANDBOX_APPOINTMENTS')
s3_client = boto3.client('s3')

def get_appointment(appointment_id):
    dynamo_response = appointments_table.get_item(Key={"appointment_id" : appointment_id})
    appointment = dynamo_response.get("Item", None)
    return appointment

appointments = [{"appointment_id": "guid",
                 "name": "Brian",
                 "status": "SCHEDULED",
                 "appointment_time": "1587791538037",
                 "display_address": "",
                 "lat": "1",
                 "long": "1",
                 }]

def handler(event, context):
    appointment_id = event['appointment_id']
    appointment = next((ap for ap in appointments if ap["appointment_id"] == appointment_id), None);
    return appointment

def check_in_handler(event, context):
    appointment_id = event['appointment_id']
    appointment = get_appointment(appointment_id)
    if not appointment:
        raise RuntimeError("Appointment not found.")
    patient_location = (event["latitude"], event["longitude"])
    dr_location = (appointment["latitude"], appointment["longitude"])
    dist = distance.distance(patient_location, dr_location).km
    if dist > 1:
        raise RuntimeError("Distance of " + str(dist) + " is greater than 1 km, check in not possible.")
    appointment["status"] = "FILLING_FORMS"
    appointment["check_in_latitude"] = event["latitude"]
    appointment["check_in_longitude"] = event["longitude"]
    appointment["check_in_time"] = int(time.time() * 1000)
    appointment["waitlist_priority"] = appointment["check_in_time"]
    #TODO String sanitzation
    #TODO Synchronization for multiple writes
    appointments_table.put_item(Item=appointment)
    return appointment


true_values = frozenset(["yes", "1", "2", "3", "4", "true", True])

def submit_form_handler(event, context):
    appointment_id = event['appointment_id']
    form = json.loads(event["form"])
    appointment = get_appointment(appointment_id)
    form_id = str(uuid.uuid4())
    s3_client.put_object(Bucket="sandbox-forms", Key=form_id, Body=json.dumps(form).encode("UTF-8"))
    if not appointment:
        return ("Appointment not found.", 404)
    covid_flag = "NORMAL"
    for question in form:
        if question.get("value", None) in true_values:
            covid_flag = "AT_RISK"

    appointment["covid_flag"] = covid_flag
    if "submitted_form_metadata" not in appointment:
        appointment["submitted_form_metadata"] = []
    appointment["submitted_form_metadata"].append({"form_id" : form_id, "form_type_id" : "COVID", "form_type_version" : "0"})
    appointment["status"] = "CHECKED_IN"
    appointments_table.put_item(Item=appointment)
    return appointment

def get_forms_handler(event, context):
    forms_metadata = event.get('submitted_form_metadata', [])
    forms = []
    for form_metadata in forms_metadata:
        form_s3_obj = s3_client.get_object(Bucket="sandbox-forms", Key=form_metadata["form_id"])
        form = form_s3_obj["Body"].read()
        forms.append(form)
    return forms


def summon_patient_handler(event, context):
    appointment_id = event['appointment_id']
    appointment = get_appointment(appointment_id)
    if not appointment:
        return ("Appointment not found.", 404)
    if "special_instructions" in event:
        appointment["special_instructions"] = event["special_instructions"]
    appointment["status"] = "SUMMONED"
    del appointment["waitlist_priority"]
    appointments_table.put_item(Item=appointment)
    return appointment

def get_waitlist_position_handler(event, context):
    appointment_id = event['appointment_id']
    appointment = get_appointment(appointment_id)
    if not appointment:
        return ("Appointment not found.", 404)
    status = appointment["status"]
    if status != "CHECKED_IN":
        raise RuntimeError("Appointment not CHECKED_IN, can't check waitlist status.")
    location_id = appointment['clinic_location_id']
    priority = appointment['waitlist_priority']

    #TODO: Implement pagination, although if it's needed the waitlist is really really really long
    #TODO: Cache the waitlist somehow, so we're not doing a dynamo fetch each time
    dynamo_waitlist = appointments_table.query(IndexName='waitlist-index',
                             KeyConditions={"clinic_location_id" : {"AttributeValueList" : [location_id],
                                                                    "ComparisonOperator" : "EQ"},
                                            "waitlist_priority" : {"AttributeValueList" : [priority],
                                                                   "ComparisonOperator" : "LT"}})
    waitlist = dynamo_waitlist["Items"]
    return len(waitlist) + 1
