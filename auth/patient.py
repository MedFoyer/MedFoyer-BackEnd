import jwt

ssm_client = boto3.client('ssm')
hsa_key = None

def get_hsa_key():
    global hsa_key
    if not hsa_key:
        parameter = ssm_client.get_parameter(Name="sandbox_patient_jwt_hsa_key", WithDecryption=True)
        hsa_key = parameter["Parameter"]["Value"]
    return hsa_key

def get_appointment_verify_id(jwt_token):
    decoded_token = jwt.decode(jwt_token, get_hsa_key(), algorithms=["HS256"])
    print("Verified token with session %s and appointment id %s", decoded_token["session_id"], decoded_token["appointment_id"])
    return decoded_token["appointment_id"]