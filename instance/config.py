from dotenv import dotenv_values

# BROKER'S CREDENTIALS - stored in a file called '.env'
# retrieved as a dictionary {var_name: var_value}
mqtt_configs = dict(dotenv_values(".env"))
# broker's hostname
MQTT_BROKER_URL = mqtt_configs.get("MQTT_HOST")
MQTT_BROKER_PORT = 1883
# broker's username
MQTT_USERNAME = mqtt_configs.get("MQTT_UNAME")
# broker's password
MQTT_PASSWORD = mqtt_configs.get("MQTT_PASS")

# Secret key for Flask-SocketIO
SECRET_KEY = "3ac20a2d9e49ba3df314f867e59ca95b"
# Database connection details for Flask-SQLAlchemy
SQLALCHEMY_DATABASE_URI = "sqlite:///platform.db"

# More MQTT details for Flask-MQTT
MQTT_CLIENT_ID = "sentry-platform"
MQTT_KEEPALIVE = 3600
MQTT_LAST_WILL_TOPIC = "sentry-platform/backend-server/shift-status"
MQTT_LAST_WILL_MESSAGE = "OFF"
MQTT_LAST_WILL_QOS = 2

password = "$2b$12$PqffSm1f9TGFmU0MwYTCXOz70YS3XjeW0B6iYybiv6IBlZpqjV59O"
