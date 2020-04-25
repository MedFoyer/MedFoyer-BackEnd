import os
from flask import Flask, url_for
from flask_restplus import Api
from flask_cors import CORS

from api import example_namespace

dev = os.getenv("DEV")

app = Flask(__name__)
api = Api(app, version="0.0", title="MedFoyer API", doc="/" if dev else False)
CORS(app)

api.add_namespace(example_namespace, path="/path")

WaitlistParser = api.parser()
WaitlistParser.add_argument("user", type=str, help="Playbook as a JSON String",
                        required=True, location="json", dest="username")


@api.route("/Waitlist")
class User(Resource):
    def get(self):
        return users

    @api.expect(UserParser)
    def post(self):
        args = UserParser.parse_args()
        if "username" in args:
            users.append({"username": args["username"]})
            return True
        else:
            return "Missing username!"


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')

# This is needed so we can deliver the swagger.json over https
if os.environ.get('HTTPS'):
    @property
    def specs_url(self):
        """Monkey patch for HTTPS"""
        return url_for(self.endpoint('specs'), _external=True, _scheme='https')


    Api.specs_url = specs_url
