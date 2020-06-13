import boto3

dynamodb = boto3.resource('dynamodb')
appointments_table = dynamodb.Table('SANDBOX_APPOINTMENTS')
tokens_table = dynamodb.Table('SANDBOX_TOKENS')
clinics_table = dynamodb.Table('SANDBOX_CLINICS')
clinic_locations_table = dynamodb.Table('SANDBOX_CLINIC_LOCATIONS')
patients_table = dynamodb.Table('SANDBOX_PATIENTS')
s3_client = boto3.client('s3')

def get_appointment(appointment_id):
    dynamo_response = appointments_table.get_item(Key={"appointment_id" : appointment_id})
    appointment = dynamo_response.get("Item", None)
    return appointment

def get_token(token_id):
    dynamo_response = tokens_table.get_item(Key={"token_id" : token_id})
    token = dynamo_response.get("Item", None)
    return token

def put_token(token):
    tokens_table.put_item(Item=token)

def get_patient(patient_id):
    dynamo_response = patients_table.get_item(Key={"patient_id" : patient_id})
    patient = dynamo_response.get("Item", None)
    return patient

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