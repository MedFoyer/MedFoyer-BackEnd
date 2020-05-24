from flask_restplus import Resource, Namespace
from flask import abort
import uuid
from geopy import distance
import json

appointments = [{"id": "guid",
                 "name": "Brian",
                 "status": "SCHEDULED",
                 "appointment_time": 1587791538037,
                 "display_address": "",
                 "lat": "39.28244",
                 "long": "-94.65516",
                 }]

# First param will be URL Prefix unless explicitly set when attaching to api object in Main.py
api = Namespace("appointment", description="Example Namespace")

AppointmentParser = api.parser()
# AppointmentParser.add_argument("name", type=str, help="Patient name",
#                                required=True, location="json")
# AppointmentParser.add_argument("appointment_time", type=str, help="Time of appointment in unix epoch time",
#                                required=True, location="json")
# AppointmentParser.add_argument("display_address", type=str, help="Visible Address of Doctor's Address",
#                                required=True, location="json")
# AppointmentParser.add_argument("lat", type=str, help="Latitute of Doctor's Address",
#                                required=True, location="json")
# AppointmentParser.add_argument("long", type=str, help="Longitude of Doctor's Address",
#                                required=True, location="json")
AppointmentParser.add_argument("form", help="Stringified JSON blob for appointment",
                               required=True, location="json")


# Example API with arg routing
@api.route("/")
class Appointments(Resource):
    def get(self):
        return appointments

    @api.expect(AppointmentParser)
    def post(self):
        args = AppointmentParser.parse_args()
        appointment_raw = json.loads(args.form)
        appointment = {
            "status": "SCHEDULED",
            "id": str(uuid.uuid4()),
            "name": next((it for it in appointment_raw if it["name"] == "name")).get("value"),
            "appointment_time": next((it for it in appointment_raw if it["name"] == "appointment_time")).get("value"),
            "display_address": next((it for it in appointment_raw if it["name"] == "display_address")).get("value"),
            "lat": next((it for it in appointment_raw if it["name"] == "lat")).get("value"),
            "long": next((it for it in appointment_raw if it["name"] == "long")).get("value"),
            "dob": next((it for it in appointment_raw if it["name"] == "dob")).get("value")
        }
        appointments.append(appointment)
        return appointment


@api.route("/<string:appointment_id>")
class Appointment(Resource):
    def get(self, appointment_id):
        appointment = next((ap for ap in appointments if ap["id"] == appointment_id), None);
        return appointment if appointment else ("Appointment not found.", 404)

    def delete(self, appointment_id):
        appointment = next((ap for ap in appointments if ap["id"] == appointment_id), None);
        if appointment:
            appointments.remove(appointment)
            return ("Deleted", 200)
        else:
            return ("Appointment not found.", 404)


CheckInParser = api.parser()
CheckInParser.add_argument("current_lat", type=str, help="Latitute of Patient checking in",
                           required=True, location="json")
CheckInParser.add_argument("current_long", type=str, help="Longitude of Patient checking in",
                           required=True, location="json")


@api.route("/<string:appointment_id>/checkin")
class CheckIn(Resource):
    @api.expect(CheckInParser)
    def post(self, appointment_id):
        # TODO validate valid decimal for lat long
        appointment = next((ap for ap in appointments if ap["id"] == appointment_id), None);
        if not appointment:
            return ("Appointment not found.", 404)

        args = CheckInParser.parse_args()
        patient_location = (args.current_lat, args.current_long)
        dr_location = (appointment["lat"], appointment["long"])
        dist = distance.distance(patient_location, dr_location).km
        if dist > 1:
            abort(400, "Distance of " + str(dist) + " is greater than 1 km, check in not possible.")
        appointment["status"] = "FILLING_FORMS"
        return appointment


SubmitFormParser = api.parser()
SubmitFormParser.add_argument("form", help="Stringified JSON blob as COVID check in form",
                              required=True, location="json")

true_values = frozenset(["yes", "1", "2", "3", "4", "true", True])


# TODO: needs validation
@api.route("/<string:appointment_id>/submitform")
class SubmitForm(Resource):
    @api.expect(SubmitFormParser)
    def post(self, appointment_id):
        args = SubmitFormParser.parse_args()
        form = json.loads(args.form)
        appointment = next((ap for ap in appointments if ap["id"] == appointment_id), None);
        if not appointment:
            return ("Appointment not found.", 404)
        covid_flag = "NORMAL"
        for question in form:
            if question.get("value", None) in true_values:
                covid_flag = "AT_RISK"

        appointment["covid_flag"] = covid_flag
        appointment["form"] = form
        appointment["status"] = "CHECKED_IN"
        return appointment


SummonPatientParser = api.parser()
SummonPatientParser.add_argument("special_instructions", type=str,
                                 help="Special instructions for patients to enter, due to COVID risk or something else",
                                 required=False, location="form")


@api.route("/<string:appointment_id>/summonpatient")
class SubmitForm(Resource):
    @api.expect(SummonPatientParser)
    def post(self, appointment_id):
        args = SummonPatientParser.parse_args()
        appointment = next((ap for ap in appointments if ap["id"] == appointment_id), None);
        if not appointment:
            return ("Appointment not found.", 404)
        if args.special_instructions:
            appointment["special_instructions"] = args.special_instructions
        appointment["status"] = "SUMMONED"
        return appointment
