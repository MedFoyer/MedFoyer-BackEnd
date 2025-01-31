import os
from twilio.rest import Client
import boto3

ssm_client = boto3.client('ssm')

stage = os.environ.get("STAGE", "SANDBOX").upper()

account = None
auth_token = None
twilio_client = None


def send_message(message, destination):
    twilio_client.messages.create(
        body=message,
        from_="+1 833 531 0351",
        to=destination
    )


def init_client():
    global twilio_client
    if not twilio_client:
        ssm_response = ssm_client.get_parameters(Names=["twilio_account_sid", "twilio_auth_token"], WithDecryption=True)
        parameters = ssm_response["Parameters"]
        account = next((parameter for parameter in parameters if parameter["Name"] == "twilio_account_sid"))["Value"];
        auth_token = next((parameter for parameter in parameters if parameter["Name"] == "twilio_auth_token"))["Value"];
        twilio_client = Client(account, auth_token)


def notify_for_summon(patient):
    init_client()
    patient_number = patient["phone_number"]
    send_message("""Your doctor is ready to see you!  Please proceed in and check in with the front desk.""",
                 patient_number)


def notify_for_appointment(patient, token_id):
    init_client()
    patient_number = patient["phone_number"]
    subdomain = "app" if stage == "PROD" else "dev"
    send_message(
        f"""
You have an upcoming appointment, and your clinic uses MedFoyer to ensure a safe and smooth check-in.

Please open this link to check-in remotely when you arrive in the parking lot.

If you do not have a smartphone or would like to opt-out, please reply "STOP".
        
https://{subdomain}.medfoyer.com/patient/appt/{token_id}
        """,
        patient_number
    )


def notify_for_telehealth(patient, practitioner):
    init_client()
    patient_number = patient["phone_number"]
    if "telehealth_link" not in practitioner:
        send_message(
            f"""
                    Your doctor is requesting a telehealth consultation. Please contact them for a link.
                    """
            , patient_number)
    else:
        send_message(
            f"""
            Your doctor is requesting a telehealth consultation. Please join with this link {practitioner[
                'telehealth_link']}
            """
            , patient_number)
