import boto3
import jwt
import db.dynamo
import time
import uuid

dynamodb = boto3.resource('dynamodb')
appointments_table = dynamodb.Table('SANDBOX_APPOINTMENTS')
patients_table = dynamodb.Table("SANDBOX_PATIENTS")
ssm_client = boto3.client('ssm')
hsa_key = None

#This function is used by Cognito to add the clinic ID to the JWT claims
def claim_add_handler(event, context):
    attributes = event["request"]["userAttributes"]
    clinic_id = attributes.get("custom:clinic_ident", None)
    if clinic_id:
        event["response"]["claimsOverrideDetails"] = {
            "claimsToAddOrOverride" : {
                "clinic_id": clinic_id
            }
        }
    return event

def auth_appointment_handler(event, context):
    print("EVENT:" + str(event))
    print("CONTEXT" + str(context))
    requested_token = event["token"]
    birthday_assertion = event["birthday"]
    token = dynamo.get_token(requested_token)
    if token:
        if token["failed_attempts"] >= 5:
            return {statusCode: 403,
                    body: "Too many failed attempts, please call your clinic to check in."}
        appointment_id = token["appointment_id"]
        patient = dynamo.get_patient(token["patient_id"])
        birthday = patient["birthday"]
        if birthday_assertion is birthday:
            global hsa_key
            if not hsa_key:
                parameter = ssm_client.get_parameter(Name="sandbox_patient_jwt_hsa_key", WithDecryption=True)
                hsa_key = parameter["Value"]
            #expire 4 hour after now
            expiration = int(time.time() / 1000 / 1000) + 60 * 60 * 4
            auth_session = str(uuid.uuid4())
            print("Created JWT Token for appointment id %d with session id %d", appointment_id, auth_session)
            jwt_token = jwt.encode({"exp" : expiration,
                        "appointment_id" : appointment_id,
                        "session_id" : auth_session},
                       key = hsa_key,
                       algorithms=["HS256"])
            token["failed_attempts"] = 0
            dynamo.put_token(token)
            return {statusCode: 200,
                    body: jwt_token}
        token["failed_attempts"]+= 1
        dynamo.put_token(token)
    #We're using the same message for both missing token and unable to find token.  Could eventually split them out,
    #but better to be safe on protecting against scrapes for now.
    return {statusCode: 403,
            body: "Authentication Failed."}


