from flask_restplus import Resource, Namespace
import uuid

appointments = [{"id": "guid",
                 "name": "Brian",
                 "status": "SCHEDULED",
                 "appointment_time": "1587791538037",
                 "display_address": "",
                 "lat_long": "",
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
AppointmentParser.add_argument("lat_long", type=str, help="Latitute and Longitude of Doctor's Address",
                               required=True, location="form")

# Example API with arg routing
@api.route("/")
class Appointments(Resource):
    def get(self):
        return appointments

    @api.expect(AppointmentParser)
    def post(self):
        appointment = AppointmentParser.parse_args()
        appointment["status"] = "SCHEDULED"
        appointment["id"] = str(uuid.uuid4())
        appointments.append(appointment)
        return appointment

# Example API with arg routing
@api.route("/<string:appointment_id>")
class Appointment(Resource):
    def get(self, appointment_id):
        appointment = next((ap for ap in appointments if ap["id"] == appointment_id), None);
        return appointment if appointment else ({}, 404)

    @api.expect(AppointmentParser)
    def post(self):
        args = AppointmentParser.parse_args()
        # check location
        #if close, check in
        if "id" in args:
            appointments.append({"id": args["id"]})
            return True
        else:
            return "Missing username!"
