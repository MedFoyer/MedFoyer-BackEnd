from flask_restplus import Resource, Namespace

appointments = [{"id": "guid",
                 "Name": "Brian",
                 "status": "SCHEDULED",
                 "appointment_time": "1587791538037",
                 "Display Address": "",
                 "Lat long": "",
                 }]

# First param will be URL Prefix unless explicitly set when attaching to api object in Main.py
api = Namespace("appointment", description="Example Namespace")

AppointmentParser = api.parser()
AppointmentParser.add_argument("user", type=str, help="Playbook as a JSON String",
                               required=True, location="json", dest="username")


# Example API with arg routing
@api.route("/")
class Appointment(Resource):
    def get(self):
        return appointments

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
