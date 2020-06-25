import boto3
import jwt
import db.dynamo as dynamo
import time
import uuid
import json
import auth.patient as patient_auth


# This function is used by Cognito to add the clinic ID to the JWT claims
def claim_add_handler(event, context):
    attributes = event["request"]["userAttributes"]
    clinic_id = attributes.get("custom:clinic_ident", None)
    clinic_id = attributes.get("custom:clinic_id", clinic_id)
    if clinic_id:
        event["response"]["claimsOverrideDetails"] = {
            "claimsToAddOrOverride": {
                "clinic_id": clinic_id
            }
        }
    return event


def auth_appointment_handler(event, context):
    body = json.loads(event["body"])
    requested_token = body.get("token", None)
    birth_date_assertion = body.get("birth_date", None)
    if not (requested_token and birth_date_assertion):
        return {"statusCode": 400,
                "headers": {
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Origin": "*"
                }}
    token = dynamo.get_token(requested_token)
    if token:
        if token["failed_attempts"] >= 5:
            print(f"Token {requested_token} has too many failed attempts")
            return {"statusCode": 403,
                    "body": json.dumps("Too many failed attempts, please call your clinic to check in."),
                    "headers": {
                        "Access-Control-Allow-Headers": "Content-Type",
                        "Access-Control-Allow-Origin": "*"
                    }}
        appointment_id = token["appointment_id"]
        clinic_id = token["clinic_id"]
        patient = dynamo.get_patient(clinic_id, token["patient_id"])
        clinic_id = patient["clinic_id"]
        birth_date = patient["birth_date"]
        if birth_date_assertion == birth_date:
            jwt_token = patient_auth.create_jwt_token(appointment_id, clinic_id)
            token["failed_attempts"] = 0
            dynamo.put_token(token)
            return {"statusCode": 200,
                    "body": json.dumps(jwt_token.decode("utf-8")),
                    "headers": {
                        "Access-Control-Allow-Headers": "Content-Type",
                        "Access-Control-Allow-Origin": "*"
                    }}
        token["failed_attempts"] = token["failed_attempts"] + 1
        dynamo.put_token(token)
        print(f"Token {requested_token} was passed with an incorrect birthday {birth_date_assertion}")
    else:
        print(f"Token {requested_token} is invalid")
    # We're using the same message for both missing token and unable to find token.  Could eventually split them out,
    # but better to be safe on protecting against scrapes for now.

    return {"statusCode": 403,
            "body": json.dumps("Authentication Failed."),
            "headers": {
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Origin": "*"
            }}
