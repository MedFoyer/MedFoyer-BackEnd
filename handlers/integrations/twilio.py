import os
from twilio.rest import Client
import boto3

ssm_client = boto3.client('ssm')

account = None
auth_token = None
twilio_client = None


def send_message(message, destination):
    twilio_client.messages.create(
        body=message,
        from_="+1 833 531 0351",
        to=destination
    )


def notify_for_appointment(appointment):
    global twilio_client
    if not twilio_client:
        parameters = ssm_client.get_parameters(Names=["twilio_account_sid, twilio_auth_token"], WithDecryption=True)
        account = next((parameter for parameter in parameters if parameter["Name"] == "twilio_account_sid"))["Value"];
        auth_token = next((parameter for parameter in parameters if parameter["Name"] == "twilio_auth_token"))["Value"];
        twilio_client = Client(account, auth_token)
    appointment_id = appointment["id"]
    patient_number = appointment["phone_number"]
    send_message(
        """
You have an upcoming appointment, and your clinic uses MedFoyer to ensure a safe and smooth check-in.

Please open this link to check-in remotely when you arrive in the parking lot.

If you do not have a smartphone, please reply "NO".
        
https://medfoyer.com/patient/appt/%s
        """ % appointment_id,
        patient_number
    )
