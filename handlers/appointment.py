import json
import time
from geopy import distance

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
    appointment = next((ap for ap in appointments if ap["appointment_id"] == appointment_id), None);
    if not appointment:
        raise RuntimeError("Appointment not found.")
    patient_location = (event["latitude"], event["longitude"])
    dr_location = (appointment["lat"], appointment["long"])
    dist = distance.distance(patient_location, dr_location).km
    if dist > 1:
        raise RuntimeError("Distance of " + str(dist) + " is greater than 1 km, check in not possible.")
    appointment["status"] = "FILLING_FORMS"
    appointment["patient_location"] = patient_location
    appointment["check_in_time"] = int(time.time() * 1000)
    return appointment