import json
import time
import boto3
import os
import uuid
import handlers.integrations.twilio as twilio
from geopy import distance
import db.dynamo as dynamo
import auth.patient as patient_auth
from decimal import Decimal

s3_client = boto3.client('s3')

stage = os.environ.get("STAGE", "sandbox")


def check_in_handler(event, context):
    jwt_token = event["headers"]["x-auth-token"].split(" ")[-1]
    print(jwt_token)
    decoded_token = patient_auth.get_token_verify_id(jwt_token)
    appointment_id = decoded_token["appointment_id"]
    clinic_id = decoded_token["clinic_id"]
    body = json.loads(event["body"])
    check_in_latitude = body["latitude"]
    check_in_longitude = body["longitude"]
    patient_location = (check_in_latitude, check_in_longitude)
    appointment = dynamo.get_appointment(clinic_id, appointment_id)
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


def submit_form_handler(event, context):
    headers = {k.lower(): v for k, v in event["headers"].items()}
    jwt_token = headers["x-auth-token"].split(" ")[-1]
    decoded_token = patient_auth.get_token_verify_id(jwt_token)
    appointment_id = decoded_token["appointment_id"]
    clinic_id = decoded_token["clinic_id"]
    body = json.loads(event["body"])
    form = json.loads(body["form"])
    appointment = dynamo.get_appointment(clinic_id, appointment_id)
    clinic_id = appointment["clinic_id"]
    form_id = str(uuid.uuid4())
    s3_client.put_object(Bucket=f"medfoyer-{stage}-forms", Key=f"{clinic_id}/{form_id}",
                         Body=json.dumps(form).encode("UTF-8"))
    if not appointment:
        return {"statusCode": 404,
                "body": json.dumps("Appointment not found.", 404)}
    covid_flag = "NORMAL"
    priority = 0
    for question in form:
        flags = question.get("flags", [])
        for flag in flags:
            if question.get("value", None) in flag["flaggable_answers"] and priority < flag["priority"]:
                priority = flag["priority"]
                covid_flag = flag["state"]

    appointment["covid_flag"] = covid_flag
    if "submitted_form_metadata" not in appointment:
        appointment["submitted_form_metadata"] = []
    appointment["submitted_form_metadata"].append(
        {"form_id": form_id, "form_type_id": "COVID", "form_type_version": "1"})
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
    clinic_id = event["clinic_id"]
    forms = []
    for form_metadata in forms_metadata:
        form_id = form_metadata["form_id"]
        form_s3_obj = s3_client.get_object(Bucket=f"medfoyer-{stage}-forms", Key=f"{clinic_id}/{form_id}")
        form = form_s3_obj["Body"].read()
        forms.append(form)
    return forms


def summon_patient_handler(event, context):
    appointment_id = event['appointment_id']
    clinic_id = event["clinic_id"]
    appointment = dynamo.get_appointment(clinic_id, appointment_id)
    if not appointment:
        return ("Appointment not found.", 404)
    if "special_instructions" in event:
        appointment["special_instructions"] = event["special_instructions"]
    appointment["status"] = "SUMMONED"
    appointment.pop("waitlist_priority", None)
    patient = dynamo.get_patient(clinic_id, appointment["patient_id"])
    twilio.notify_for_summon(patient)
    dynamo.put_appointment(appointment)
    return appointment


def dispatch_telehealth_handler(event, context):
    appointment_id = event['appointment_id']
    clinic_id = event['clinic_id']
    appointment = dynamo.get_appointment(clinic_id, appointment_id)
    patient = dynamo.get_patient(clinic_id, appointment.patient_id)
    practitioner = dynamo.get_Practitioner(clinic_id, appointment.practitioner_id)
    twilio.notify_for_telehealth(patient, practitioner)
    appointment["status"] = "TELEHEALTH"
    appointment.pop("waitlist_priority", None)
    dynamo.put_appointment(appointment)
    return True


def list_appointments_handler(event, context):
    clinic_id = event["clinic_id"]
    clinic_location_id = event.get("clinic_location_id", None)
    start_time = event.get("start_time", 0)
    # Default here is 2030-01-01.  TODO: Remove once we can make this field required
    end_time = event.get("end_time", 1893484800000)
    if clinic_location_id:
        return dynamo.list_appointments_by_location(clinic_id, clinic_location_id, start_time, end_time)
    return dynamo.list_appointments(clinic_id, start_time, end_time)


def get_waitlist_position_handler(event, context):
    jwt_token = event["headers"]["x-auth-token"].split(" ")[-1]
    decoded_token = patient_auth.get_token_verify_id(jwt_token)
    appointment_id = decoded_token["appointment_id"]
    clinic_id = decoded_token["clinic_id"]
    appointment = dynamo.get_appointment(clinic_id, appointment_id)
    if not appointment:
        return {"statusCode": 404,
                "body": json.dumps("Appointment not found."),
                "headers": {
                    "Access-Control-Allow-Headers": "Content-Type, X-Auth-Token",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Credentials": "true",
                }
                }
    status = appointment["status"]
    if status == "SUMMONED":
        return {"statusCode": 200,
                "body": json.dumps({"summoned": True}),
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
    patient = dynamo.get_patient(appointment["clinic_id"], appointment["patient_id"])
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
        appointments = dynamo.list_appointments_by_location(clinic_location["clinic_id"],
                                                            clinic_location["clinic_location_id"], now, end_time)
        print("Checking %d appointments" % len(appointments))
        for appointment in appointments:
            appointment_id = appointment["appointment_id"]
            if appointment.get("reminder_status", None) in [None, "NONE_SENT", "FIRST_REMINDER_SENT"]:
                send_check_in_text(appointment)


def send_check_in_text_handler(event, context):
    appointment_id = event["appointment_id"]
    clinic_id = event["clinic_id"]
    appointment = dynamo.get_appointment(clinic_id, appointment_id)
    if not appointment or appointment["clinic_id"] != clinic_id:
        raise RuntimeError("Appointment not found.")
    send_check_in_text(appointment)
    return True


def get_clinic_lat_long_handler(event, context):
    print(event["headers"])
    jwt_token = event["headers"]["x-auth-token"].split(" ")[-1]
    decoded_token = patient_auth.get_token_verify_id(jwt_token)
    appointment_id = decoded_token["appointment_id"]
    clinic_id = decoded_token["clinic_id"]
    appointment = dynamo.get_appointment(clinic_id, appointment_id)
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
