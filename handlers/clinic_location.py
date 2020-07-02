import db.dynamo as dynamo

def update_clinic_location_handler(event, context):
    clinic_id = event["clinic_id"]
    clinic_location = event["clinic_location"]
    clinic_location_id = event["clinic_location_id"]
    return dynamo.update_practitioner(clinic_id, clinic_location_id, clinic_location)
