from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

app = Flask(__name__)

# configure SECRET_KEY and SQLALCHEMY_DATABASE_URI in separate config.py file
app.config.from_pyfile("../instance/config.py")


# connecting to and manipulating (CRUD) the app's database
db = SQLAlchemy(app)
# handling supervisor logins and online sessions
login_manager = LoginManager(app)
# handling password encryption and decryption
bcrypt = Bcrypt(app)

# if try to access page that needs authentication if not logged in, redirect to this route
login_manager.login_view = "home"
login_manager.login_message_category = "info"

from . import routes
