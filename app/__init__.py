import eventlet

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mqtt import Mqtt
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

# from Flask-MQTT docs example
eventlet.monkey_patch()

app = Flask(__name__)

# configure SECRET_KEY, SQLALCHEMY_DATABASE_URI and MQTT credentials in separate config.py file, 'import' them
app.config.from_pyfile("../instance/config.py")

# connecting to and manipulating (CRUD) the app's database
db = SQLAlchemy(app)
# handling supervisor logins and online sessions
login_manager = LoginManager(app)
# handling password encryption and decryption
bcrypt = Bcrypt(app)

# for MQTT, initialising the web app as an MQTT client
mqtt = Mqtt(app=app, connect_async=True)
# enabling use of WebSockets in the web app for flow of MQTT alert messages from server to client and vice-versa
socketio = SocketIO(app)

# if not logged in and try to access page that needs authentication, redirect to this route
login_manager.login_view = "home"
# flash a default message telling the user they need to log in
login_manager.login_message_category = "info"

from . import mqtts
from . import routes
