import json
import time
import boto3
import uuid
from integrations import twilio
from geopy import distance

dynamodb = boto3.resource('dynamodb')
appointments_table = dynamodb.Table('SANDBOX_APPOINTMENTS')
clinics_table = dynamodb.Table('SANDBOX_CLINICS')
clinic_locations_table = dynamodb.Table('SANDBOX_CLINIC_LOCATIONS')
s3_client = boto3.client('s3')

def get_appointment(appointment_id):
    dynamo_response = appointments_table.get_item(Key={"appointment_id" : appointment_id})
    appointment = dynamo_response.get("Item", None)
    return appointment

def get_appointments(clinic_location_id, start_time, end_time):
    dynamo_response = appointments_table.query(IndexName='clinic-location-index',
                                               KeyConditions={"clinic_location_id" : {"AttributeValueList" : [clinic_location_id],
                                                                                      "ComparisonOperator" : "EQ"},
                                                              "appointment_time" : {"AttributeValueList" : [start_time, end_time],
                                                                                     "ComparisonOperator" : "BETWEEN"}})
    appointments = dynamo_response["Items"]
    return appointments

def get_clinics():
    #TODO: Needs pagination (and optimization) when we start rolling in customers
    dynamo_response = clinics_table.scan()
    clinics = dynamo_response["Items"]
    return clinics

def get_clinic_locations():
    #TODO: Needs pagination (and optimization) when we start rolling in customers
    dynamo_response = clinic_locations_table.scan()
    clinic_locations = dynamo_response["Items"]
    return clinic_locations

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
    waitlist_count = dynamo_waitlist["Count"] + 1
    return {"position" : waitlist_count,
            #TODO: Make this value more useful
            "expected_wait_time" : waitlist_count * 300}

def send_appointment_reminders_handler(event, context):
    #TODO: Cache this
    clinic_locations = get_clinic_locations()
    now = int(time.time() * 1000)
    for clinic_location in clinic_locations:
        #TODO: A lot of room for optimization here.  Use a sparse index instead of the base one and use a filter query
        #Get all appointments from now until an hour from now for check in text
        appointments = get_appointments(clinic_location["clinic_location_id"], now, now + 1000 * 60 * 60 * 60)
        for appointment in appointments:
            if appointment.get("reminder_status", None) in ["NONE_SENT", "FIRST_REMINDER_SENT"]:
                twilio.notify_for_appointment(appointment)
