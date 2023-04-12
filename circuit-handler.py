import paho.mqtt.client as mqtt
import json
from operator import itemgetter
from collections import deque
from datetime import datetime
import time
from dotenv import dotenv_values

# CLIENT CREDENTIALS

# client's client ID
CLIENT_ID = "circuit-handler"

# BROKER'S CREDENTIALS - stored in a file called '.env'
# retrieved as a dictionary {var_name: var_value}
mqtt_configs = dict(dotenv_values(".env"))

# broker's hostname
MQTT_HOST = mqtt_configs.get("MQTT_HOST")
# broker's username
MQTT_UNAME = mqtt_configs.get("MQTT_UNAME")
# broker's password
MQTT_PASS = mqtt_configs.get("MQTT_PASS")

# global variables to store shift/circuit information

# circuit's time-validating queue
CIRCUIT = None

# on-duty cards (IDs)
CARDS = None

# shift ongoing (true) or shift over (false)
SHIFT_STATUS = False

# check-in window - x seconds before and after the set check-in time within which a scan is considered valid
CHECK_IN_WINDOW = 120

# DEFINING MQTT TOPICS

# SUBSCRIBE:

# topic to receive the generated sentry circuit
SENTRY_CIRCUIT = "sentry-platform/backend-server/sentry-circuit"
# topic to receive the shift started/over message
SHIFT_ON_OFF = "sentry-platform/backend-server/shift-status"
# topic to receive a scan to validate
SENTRY_SCAN = "sentry-platform/checkpoints/sentry-scan-info"

# PUBLISH:

# topics to publish when a scan is overdue, for each cehckpoint A, B, C, D
# NOTE: the backend server will subscribe to all below topics
CHK_A_OVERDUE = "sentry-platform/checkpoints/A/overdue-scan"
CHK_B_OVERDUE = "sentry-platform/checkpoints/B/overdue-scan"
CHK_C_OVERDUE = "sentry-platform/checkpoints/C/overdue-scan"
CHK_D_OVERDUE = "sentry-platform/checkpoints/D/overdue-scan"

# topic to publish on when connected to the broker
CONNECTED = "sentry-platform/circuit-handler/connected"

# topic to publish alerts - valid and invalid scans with reasons, if shift done
ALERTS = "sentry-platform/circuit-handler/alerts"

# topic to publish when shift is over
DONE = "sentry-platform/circuit-handler/circuit-complete"

# DEFINING UTILITY FUNCTIONS


def generate_checkins(circuits: list[dict]):
    """
    generates a queue of instantaneous check-in info dicts i.e. check-ins
    used to check overdue scans and trigger alarms if necessary
    """

    check_ins = []
    global CARDS
    CARDS = [circuit["id"] for circuit in circuits]

    # accessing each dict in the list
    for circuit in circuits:
        # before a check-in is added to the check-ins list, the time is first validated
        # i.e. check-ins with past/expired timestamps are irrelevant and hence discarded
        # the check-ins list is extended with a list of relevant check-ins

        check_ins.extend(
            route
            for route in circuit["route"]
            if route["time"] > datetime.timestamp(datetime.now())
        )

    # sorting the list in ascending order of check-in time and then converting it to a python queue
    # a queue is used because the validation algorithm will pop values off the beginning of the list
    # when the check-in window for that check-in has elapsed
    # queues are more efficient than lists when it comes to deleting from the beginning (index 0)
    # this queue will be saved in the CIRCUIT global variable

    check_ins.sort(key=itemgetter("time"))
    return deque(check_ins)


def validate_scan(check_in: dict):
    """
    checks and validates a scan at a checkpoint
    """

    # check if the card should be on duty
    if check_in["sentry-id"] not in CARDS:
        # TODO: check if card is in the database
        return {"valid": False, "reason": "card not on duty"}

    valid_id = False
    valid_time = False

    for item in CIRCUIT:
        # if scan is valid (right sentry, right checkpoint, right time), return message
        if (
            check_in["sentry-id"] == item["id"]
            and check_in["checkpoint"] == item["checkpoint"]
            and check_in["scan-time"]
            in range(item["time"] - CHECK_IN_WINDOW, item["time"] + CHECK_IN_WINDOW)
        ):
            item["checked"] = True
            return {"valid": True, "reason": ""}

        # if an on-duty card is scanned at the right time but the wrong checkpoint
        # sets flags that indicate this as true
        elif check_in["sentry-id"] == item["id"] and check_in["scan-time"] in range(
            item["time"] - CHECK_IN_WINDOW, item["time"] + (CHECK_IN_WINDOW + 1)
        ):
            valid_id = True
            valid_time = True

        # breaks loop when the subsequent check-in times are in the future
        # either scan was too early or at the wrong checkpoint
        elif check_in["time"] < (item["time"] - CHECK_IN_WINDOW):
            return (
                {"valid": False, "reason": "wrong checkpoint"}
                if valid_id and valid_time
                else {"valid": False, "reason": "wrong time of scan"}
            )


def analyse_checkins(client: mqtt.Client):
    """
    handles overdue scans by checking whether the soonest expected scan was validated
    """

    # for as long as a shift is ongoing, these checks need be made

    while SHIFT_STATUS:
        # if all check-ins have been validated / circuit is exhausted
        if not CIRCUIT:
            client.publish(topic=DONE, payload=None)
            break

        # 1. check the current time
        # 2. compare it against the soonest expected check-in (reason for sorting)
        # 3. if the check-in time has passed, remove it from the queue. if not, proceed
        # 4. if it reads False, some sentry hasn't checked-in in time and that's a problem, snitch
        # 5. if the shift was validated, the checked flag should read True and the shift proceeds

        time_now = int(datetime.timestamp(datetime.now()))  # 1

        if time_now > CIRCUIT[0]["time"] + 120:  # 2
            current = CIRCUIT.popleft()  # 3
            if not current["checked"]:  # 4
                for topic in [CHK_A_OVERDUE, CHK_B_OVERDUE, CHK_C_OVERDUE, CHK_D_OVERDUE]:
                    client.publish(topic=topic, payload=json.dumps(current))
                    break

            # 5. else do nothing

        # runs this loop every second
        time.sleep(1)


# DEFINING CALLBACK FUNCTIONS FOR MQTT EVENTS
# necessary callbacks:
# when the client connects to the broker
# when the client receives a message from the broker


def on_mqtt_connect(client: mqtt.Client, userdata, flags, rc):
    """
    callback event handler, called when this client connects to the broker
    """

    if rc == 0:
        client.publish(topic=CONNECTED, payload="connected")

        # subscribe to relevant topics each time it connects
        # this includes at startup and reconnection
        # list of (topic, QoS) tuples
        client.subscribe([(SENTRY_CIRCUIT, 2), (SHIFT_ON_OFF, 2), (SENTRY_SCAN, 2)])

    # using connect_async() will retry connection until established


def on_mqtt_message(client, userdata, message):
    """ """

    topic = message.topic

    # circuit sent by the broker
    if topic == SENTRY_CIRCUIT:
        # the sentry circuit will be sent as a JSON bytearray over MQTT
        payload = json.loads(message.payload)

        # at this point, payload is now a list of Python dictionaries - the generated route
        # the goal is to construct another list of python dictionaries of the form:

        # [{
        #     id: sentry ID to expect
        #     checkpoint: checkpoint at which above sentry is expected
        #     time: time at which the sentry is expected (epoch)
        #     checked: whether the sentry has validly checked in or not
        # },
        # others...]

        # which is what is stored in the 'route' key of each dict
        # this is essentially a list/queue of check-ins

        global CIRCUIT
        CIRCUIT = generate_checkins(payload)
        analyse_checkins(client=client)

    # check-in sent by any checkpoint
    elif topic == SENTRY_SCAN:
        # the check-in info will be sent as a JSON bytearray over MQTT
        payload = json.loads(message.payload)

        # at this point, payload is now a Python dictionary of the form
        # {
        #     checkpoint: checkpoint ID at which the sentry has checked in
        #     sentry-id: ID of the card assigned to that sentry
        #     scan-time: time at which the sentry has scanned
        # }

        # these are checked against the checkpoint, id, and time keys respectively, of each dict in CIRCUIT
        # if a match is found, the value of the checked key is set to True
        # else send validation result to web app

        validation_result = validate_scan(payload)
        client.publish(topic=ALERTS, payload=json.dumps(validation_result))

    # checker for shift status message
    elif topic == SHIFT_ON_OFF:
        payload = message.payload.decode("utf-8")

        global CIRCUIT
        global SHIFT_STATUS

        # if shift is on, set shift_status to active(True)
        # if not, set shift status to inactive(False) and clear the check-ins being analysed

        # shift inactive
        if payload == "OFF":
            SHIFT_STATUS = False
            time.sleep(1)
            CIRCUIT = None

        # shift active
        elif payload == "ON":
            SHIFT_STATUS = True


def launch_circuit_handler():
    # create client instance
    handler = mqtt.Client(client_id=CLIENT_ID, clean_session=True, reconnect_on_failure=True)
    # configure client with broker credentials
    handler.username_pw_set(username=MQTT_UNAME, password=MQTT_PASS)
    # attach defined event callback functions to created client
    handler.on_connect = on_mqtt_connect
    handler.on_message = on_mqtt_message
    # connect to broker asynchronously
    handler.connect_async(host=MQTT_HOST, keepalive=3600)
    # start listening loop on a background thread
    handler.loop_start()


if __name__ == "__main__":
    launch_circuit_handler()
