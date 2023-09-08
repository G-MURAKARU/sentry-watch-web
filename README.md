# Sentry Watch Platform
### Authors: [G-MURAKARU](https://github.com/G-MURAKARU), [tkamara](https://github.com/tkamara) , [AlvyneZ](https://github.com/AlvyneZ)

## Environment
The requirements.txt file for setting up a python virtual environment is provided.  
A Dockerfile ("EnvDockerfile") for building an image for the python environment is also provided. The following are the required commands for this approach:
```
$   docker build -t sentry-platform-env -f EnvDockerfile.
$   docker run -it --name sentry-platform --rm \
		--volume "$(pwd):/usr/src/app" \
		--net=host sentry-platform-env:latest \
		sh
```

## Database
The system as currently set up uses a local SQLite database file, the database can however be changed.  
[Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/en/3.0.x/) is the chosen ORM to interact with the database.  
In order to change the database, the **"SQLALCHEMY_DATABASE_URI"** key in *"instance/config.py"* can be changed as required.  

## MQTT Broker
For local testing, a local MQTT broker is required.  
The project will use [Eclipse Mosquitto](https://github.com/eclipse/mosquitto) maintained by The Eclipse Foundation.  
Eclipse Mosquitto is an open source message broker which implements MQTT version 5, 3.1.1 and 3.1  

### Configuration
To ease deployment, Docker containerisation of the mosquitto broker was preferred.  
The (eclipse-mosquitto docker image)[https://hub.docker.com/_/eclipse-mosquitto] version 2.0.17 was used.  
The configuration file *"${PROJECT_DIR}/mqtt_broker/mosquitto.conf"* needs to be mounted on the container to *"/mosquitto/config/mosquitto.conf"*.  
The password file *"${PROJECT_DIR}/mqtt_broker/data/mqtt_pass.txt"* also needs to be mounted on the container to *"/mosquitto/data/mqtt_pass.txt"*.
 This can be done by mounting "${PROJECT_DIR}/mqtt_broker/data" to "/mosquitto/data".  
**Note:** For testing the username and password in ${PROJECT_DIR}/.env was used to set up the password file.
 In order to delete and add credentials, the following first 2 commands are to be run on a mosquitto container, respectively:
```
#   mosquitto_passwd -D /mosquitto/data/mqtt_pass.txt broker-user
#   mosquitto_passwd -b /mosquitto/data/mqtt_pass.txt new_user new_password
#   chmod o-r /mosquitto/data/mqtt_pass.txt
```

### Running
The following command can be used to run a detached container of the mosquitto broker:
```
$   docker run -d -p 1883:1883 -p 9001:9001 --name mosquitto --rm \
		-v "$(pwd)/mqtt_broker/mosquitto.conf:/mosquitto/config/mosquitto.conf" \
		-v "$(pwd)/mqtt_broker/data:/mosquitto/data" \
		-v "$(pwd)/mqtt_broker/mosquitto.log:/mosquitto/log/mosquitto.log" \
		eclipse-mosquitto:2.0.17
```