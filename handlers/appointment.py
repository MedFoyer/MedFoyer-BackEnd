import json

appointments = [{"id": "guid",
                 "name": "Brian",
                 "status": "SCHEDULED",
                 "appointment_time": "1587791538037",
                 "display_address": "",
                 "lat": "1",
                 "long": "1",
                 }]

def handler(event, context):
    appointment_id = event.payload.id
    appointment = next((ap for ap in appointments if ap["id"] == appointment_id), None);
    return appointment
