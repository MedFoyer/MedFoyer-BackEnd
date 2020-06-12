import os
from twilio.rest import Client

account = os.getenv("twilio_account_sid")
auth_token = os.getenv("twilio_auth_token")
client = Client(account, auth_token)


def send_message(message, destination):
    client.messages.create(
        body=message,
        from_="+1 833 531 0351",
        to=destination
    )


def notify_for_appointment(appointment):
    # TODO: Get Patient Phone Number
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
