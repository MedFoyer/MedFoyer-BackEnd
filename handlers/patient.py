import db.dynamo as dynamo

def update_patient_handler(event, context):
    clinic_id = event["clinic_id"]
    patient = event["patient"]
    patient_id = event["patient_id"]
    patient["clinic_id"] = clinic_id
    dynamo.update_patient(patient_id, patient)
