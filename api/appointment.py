from flask_restplus import Resource, Namespace
from flask import abort
import uuid
from geopy import distance

appointments = [{"id": "guid",
                 "name": "Brian",
                 "status": "SCHEDULED",
                 "appointment_time": "1587791538037",
                 "display_address": "",
                 "lat": "1",
                 "long": "1",
                 }]

# First param will be URL Prefix unless explicitly set when attaching to api object in Main.py
api = Namespace("appointment", description="Example Namespace")

AppointmentParser = api.parser()
AppointmentParser.add_argument("name", type=str, help="Patient name",
                               required=True, location="form")
AppointmentParser.add_argument("appointment_time", type=str, help="Time of appointment in unix epoch time",
                               required=True, location="form")
AppointmentParser.add_argument("display_address", type=str, help="Visible Address of Doctor's Address",
                               required=True, location="form")
AppointmentParser.add_argument("lat", type=str, help="Latitute of Doctor's Address",
                               required=True, location="form")
AppointmentParser.add_argument("long", type=str, help="Longitude of Doctor's Address",
                               required=True, location="form")

# Example API with arg routing
@api.route("/")
class Appointments(Resource):
    def get(self):
        return appointments

    @api.expect(AppointmentParser)
    def post(self):
        appointment = AppointmentParser.parse_args()
        # TODO validate valid decimal for lat long
        appointment["status"] = "SCHEDULED"
        appointment["id"] = str(uuid.uuid4())
        appointments.append(appointment)
        return appointment

@api.route("/<string:appointment_id>")
class Appointment(Resource):
    def get(self, appointment_id):
        appointment = next((ap for ap in appointments if ap["id"] == appointment_id), None);
        return appointment if appointment else ("Appointment not found.", 404)

CheckInParser = api.parser()
CheckInParser.add_argument("current_lat", type=str, help="Latitute of Patient checking in",
                               required=True, location="form")
CheckInParser.add_argument("current_long", type=str, help="Longitude of Patient checking in",
                               required=True, location="form")

@api.route("/<string:appointment_id>/checkin")
class CheckIn(Resource):
    @api.expect(CheckInParser)
    def post(self, appointment_id):
        #TODO validate valid decimal for lat long
        appointment = next((ap for ap in appointments if ap["id"] == appointment_id), None);
        if not appointment:
            return ("Appointment not found.", 404)

        args = CheckInParser.parse_args()
        patient_location = (args.current_lat, args.current_long)
        dr_location = (appointment["lat"], appointment["long"])
        dist = distance.distance(patient_location, dr_location).km
        if dist > 1:
            abort(400, "Distance of " + str(dist) + " is greater than 1, check in not possible.")
        appointment["status"] = "FILLING_FORMS"
        return appointment
