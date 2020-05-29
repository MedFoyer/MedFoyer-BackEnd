import os
from flask import Flask, url_for
from flask_restplus import Api
from flask_cors import CORS

from api import appointment

dev = os.getenv("DEV")

app = Flask(__name__)
api = Api(app, version="0.0", title="MedFoyer API", doc="/" if dev else False)
CORS(app)

api.add_namespace(appointment, path="/appointment")

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')

# This is needed so we can deliver the swagger.json over https
if os.environ.get('HTTPS'):
    @property
    def specs_url(self):
        """Monkey patch for HTTPS"""
        return url_for(self.endpoint('specs'), _external=True, _scheme='https')


    Api.specs_url = specs_url
