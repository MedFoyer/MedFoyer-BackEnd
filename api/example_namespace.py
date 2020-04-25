from flask_restplus import Resource, Namespace

users = [{"username": "brian"}]

# First param will be URL Prefix unless explicitly set when attaching to api object in Main.py
api = Namespace("example", description="Example Namespace")

UserParser = api.parser()
UserParser.add_argument("user", type=str, help="Playbook as a JSON String",
                        required=True, location="json", dest="username")


# Example API with arg routing
@api.route("/User")
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
