import db.dynamo as dynamo

def update_practitioner_handler(event, context):
    clinic_id = event["clinic_id"]
    practitioner = event["practitioner"]
    practitioner_id = event["practitioner_id"]
    return dynamo.update_practitioner(clinic_id, practitioner_id, practitioner)
