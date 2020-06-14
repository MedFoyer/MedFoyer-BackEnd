import jwt
import uuid
import time

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

def create_jwt_token(appointment_id):
    # expire 4 hour after now
    expiration = int(time.time() / 1000 / 1000) + 60 * 60 * 4
    auth_session = str(uuid.uuid4())
    print("Created JWT Token for appointment id %d with session id %d", appointment_id, auth_session)
    jwt_token = jwt.encode({"exp": expiration,
                            "appointment_id": appointment_id,
                            "session_id": auth_session},
                           key=hsa_key,
                           algorithm="HS256")
    return jwt_token