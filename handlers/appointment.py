import json
import time
import boto3
from geopy import distance

dynamodb = boto3.resource('dynamodb')
appointments_table = dynamodb.Table('SANDBOX_APPOINTMENTS')

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
    #TODO String sanitzation
    #TODO Synchronization for multiple writes
    appointments_table.put_item(Item=appointment)
    return appointment


true_values = frozenset(["yes", "1", "2", "3", "4", "true", True])

def submit_form_handler(event, context):
    appointment_id = event['appointment_id']
    form = json.loads(event["form"])
    get_appointment(appointment_id)
    if not appointment:
        return ("Appointment not found.", 404)
    covid_flag = "NORMAL"
    for question in form:
        if question.get("value", None) in true_values:
            covid_flag = "AT_RISK"

    appointment["covid_flag"] = covid_flag
    #appointment["form"] = form
    #appointment["submitted_form_ids"]
    appointment["status"] = "CHECKED_IN"
    return appointment


def summon_patient_handler(event, context):
    appointment_id = event['appointment_id']
    get_appointment(appointment_id)
    if not appointment:
        return ("Appointment not found.", 404)
    if args.special_instructions:
        appointment["special_instructions"] = args.special_instructions
    appointment["status"] = "SUMMONED"
    return appointment