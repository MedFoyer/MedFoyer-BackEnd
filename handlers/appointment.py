import json
import time
import boto3
import uuid
import handlers.integrations.twilio as twilio
from geopy import distance
import db.dynamo as dynamo
import auth.patient as patient_auth
from decimal import Decimal

s3_client = boto3.client('s3')


def check_in_handler(event, context):
    jwt_token = event["headers"]["x-auth-token"].split(" ")[-1]
    print(jwt_token)
    appointment_id = patient_auth.get_appointment_verify_id(jwt_token)
    body = json.loads(event["body"])
    check_in_latitude = body["latitude"]
    check_in_longitude = body["longitude"]
    patient_location = (check_in_latitude, check_in_longitude)
    appointment = dynamo.get_appointment(appointment_id)
    clinic_location = dynamo.get_clinic_location(appointment["clinic_id"], appointment["clinic_location_id"])
    dr_location = (clinic_location["latitude"], clinic_location["longitude"])
    if not appointment:
        raise RuntimeError("Appointment not found.")
    dist = distance.distance(patient_location, dr_location).km
    if dist > 1:
        raise RuntimeError("Distance of " + str(dist) + " is greater than 1 km, check in not possible.")
    appointment["status"] = "FILLING_FORMS"
    appointment["check_in_latitude"] = Decimal(str(check_in_latitude))
    appointment["check_in_longitude"] = Decimal(str(check_in_longitude))
    appointment["check_in_time"] = int(time.time() * 1000)
    appointment["waitlist_priority"] = appointment["check_in_time"]
    # TODO String sanitzation
    # TODO Synchronization for multiple writes
    dynamo.put_appointment(appointment)
    return {"statusCode": 200,
            "body": json.dumps({"status": "FILLING_FORMS"}),
            "headers": {
                "Access-Control-Allow-Headers": "Content-Type, X-Auth-Token",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
            }}


true_values = frozenset(["yes", "1", "2", "3", "4", "true", True])


def submit_form_handler(event, context):
    jwt_token = event["headers"]["x-auth-token"].split(" ")[-1]
    appointment_id = patient_auth.get_appointment_verify_id(jwt_token)
    body = json.loads(event["body"])
    form = json.loads(body["form"])
    appointment = dynamo.get_appointment(appointment_id)
    form_id = str(uuid.uuid4())
    s3_client.put_object(Bucket="sandbox-forms", Key=form_id, Body=json.dumps(form).encode("UTF-8"))
    if not appointment:
        return {"statusCode": 404,
                "body": json.dumps("Appointment not found.", 404)}
    covid_flag = "NORMAL"
    for question in form:
        if question.get("value", None) in true_values:
            covid_flag = "AT_RISK"

    appointment["covid_flag"] = covid_flag
    if "submitted_form_metadata" not in appointment:
        appointment["submitted_form_metadata"] = []
    appointment["submitted_form_metadata"].append(
        {"form_id": form_id, "form_type_id": "COVID", "form_type_version": "0"})
    appointment["status"] = "CHECKED_IN"
    dynamo.put_appointment(appointment)
    return {"statusCode": 200,
            "body": json.dumps({"status": "CHECKED_IN", "covid_flag": covid_flag}),
            "headers": {
                "Access-Control-Allow-Headers": "Content-Type, X-Auth-Token",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
            }}


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
    appointment = dynamo.get_appointment(appointment_id)
    if not appointment:
        return ("Appointment not found.", 404)
    if "special_instructions" in event:
        appointment["special_instructions"] = event["special_instructions"]
    appointment["status"] = "SUMMONED"
    appointment.pop("waitlist_priority", None)
    patient = dynamo.get_patient(appointment["patient_id"])
    twilio.notify_for_summon(patient)
    dynamo.put_appointment(appointment)
    return appointment


def get_waitlist_position_handler(event, context):
    jwt_token = event["headers"]["x-auth-token"].split(" ")[-1]
    appointment_id = patient_auth.get_appointment_verify_id(jwt_token)
    appointment = dynamo.get_appointment(appointment_id)
    if not appointment:
        return {"statusCode" : 404,
                "body" : json.dumps("Appointment not found."),
                "headers": {
                    "Access-Control-Allow-Headers": "Content-Type, X-Auth-Token",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
                }
    status = appointment["status"]
    if status == "SUMMONED":
        return {"statusCode" : 200,
                "body" : json.dumps({"summoned" : True}),
                "headers": {
                    "Access-Control-Allow-Headers": "Content-Type, X-Auth-Token",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
                }
    if status != "CHECKED_IN":
        raise RuntimeError("Appointment not CHECKED_IN, can't check waitlist status.")
    location_id = appointment['clinic_location_id']
    priority = appointment['waitlist_priority']

    # TODO: Implement pagination, although if it's needed the waitlist is really really really long
    # TODO: Cache the waitlist somehow, so we're not doing a dynamo fetch each time
    waitlist_count = dynamo.get_waitlist_priority(location_id, priority)
    return {"statusCode": 200,
            "body": json.dumps({"position": waitlist_count,
                                # TODO: Make this value more useful
                                "expected_wait_time": waitlist_count * 300}),
            "headers": {
                "Access-Control-Allow-Headers": "Content-Type, X-Auth-Token",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
            }}


def send_check_in_text(appointment):
    appointment_id = appointment["appointment_id"]
    print(f"Creating token for {appointment_id}")
    token_id = patient_auth.create_link_token(appointment)
    print("Fetching patient information.")
    patient = dynamo.get_patient(appointment["patient_id"])
    print("Sending text message.")
    twilio.notify_for_appointment(patient, token_id)
    print("Setting new appointment reminder status.")
    appointment["reminder_status"] = "CHECK_IN_REMINDER_SENT"
    dynamo.put_appointment(appointment)

def send_appointment_reminders_handler(event, context):
    # TODO: Cache this
    clinic_locations = dynamo.get_clinic_locations()
    now = int(time.time() * 1000)
    end_time = now + 1000 * 60 * 60
    print("Checking appointments between {} and {}".format(now, end_time))
    for clinic_location in clinic_locations:
        # TODO: A lot of room for optimization here.  Use a sparse index instead of the base one and use a filter query
        # Get all appointments from now until an hour from now for check in text
        appointments = dynamo.get_appointments(clinic_location["clinic_location_id"], now, end_time)
        print("Checking %d appointments" % len(appointments))
        for appointment in appointments:
            appointment_id = appointment["appointment_id"]
            if appointment.get("reminder_status", None) in [None, "NONE_SENT", "FIRST_REMINDER_SENT"]:
                send_check_in_text(appointment)

def send_check_in_text_handler(event, context):
    appointment_id = event["appointment_id"]
    clinic_id = event["clinic_id"]
    appointment = dynamo.get_appointment(appointment_id)
    if not appointment or appointment["clinic_id"] != clinic_id:
        raise RuntimeError("Appointment not found.")
    send_check_in_text(appointment)
    return True

def get_clinic_lat_long_handler(event, context):
    print(event["headers"])
    jwt_token = event["headers"]["x-auth-token"].split(" ")[-1]
    appointment_id = patient_auth.get_appointment_verify_id(jwt_token)
    appointment = dynamo.get_appointment(appointment_id)
    if not appointment:
        return {"statusCode": 404,
                "body": json.dumps("Appointment not found.", 404)}
    clinic_location = dynamo.get_clinic_location(appointment["clinic_id"], appointment["clinic_location_id"])
    return_body = {"latitude": clinic_location["latitude"],
                   "longitude": clinic_location["longitude"]}
    return {"statusCode": 200,
            "body": json.dumps(return_body),
            "headers": {
                "Access-Control-Allow-Headers": "Content-Type, X-Auth-Token",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": "true",
            }
            }
