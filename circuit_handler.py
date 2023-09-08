import json
import time
from collections import deque
from datetime import datetime
from operator import itemgetter
import threading

import paho.mqtt.client as mqtt
from dotenv import dotenv_values

from app.mqtts import (
    ALARM,
    ALERTS,
    DONE,
    MONITOR_SENTRY_CIRCUIT,
    SENTRY_SCAN_INFO,
    SHIFT_ON_OFF,
    CHKS_OVERDUE,
)
from app.utils import CHECK_IN_WINDOW

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

# alarm on or off flag
ALARM_ON_OFF = False

# DEFINING MQTT TOPICS

# SUBSCRIBE:

# topic to receive the shift started/over message - SHIFT_ON_OFF

# topic to receive a scan to validate - SENTRY_SCAN_INFO

# topic to receive the generated sentry circuit - MONITOR_SENTRY_CIRCUIT

# topic to receive the alarm signal - ALARM


# PUBLISH:

# topic to publish on when connected to the broker
CONNECTED = "sentry-platform/circuit-handler/connected"

# topic to publish when the circuit is exhausted - DONE

# topic to publish relevant scan results to the broker - ALERTS


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
    chk, id, time = list(check_in.values())
    # check if the card should be on duty
    if id not in CARDS:
        # check if card is in database
        return {"valid": False, "reason": "card not on duty"} | check_in

    valid_id = False
    valid_time = False

    for item in CIRCUIT:
        # if scan is valid (right sentry, right checkpoint, right time), return message
        if (
            id == item["id"]
            and chk == item["checkpoint"]
            and time in range(item["time"] - CHECK_IN_WINDOW, item["time"] + (CHECK_IN_WINDOW + 1))
        ):
            item["checked"] = True
            return {"valid": True, "reason": ""} | check_in

        # if an on-duty card is scanned at the right time but the wrong checkpoint
        # sets flags that indicate this as true
        elif id == item["id"] and time in range(
            item["time"] - CHECK_IN_WINDOW, item["time"] + (CHECK_IN_WINDOW + 1)
        ):
            valid_id = True
            valid_time = True

        # breaks loop when the subsequent check-in times are in the future
        # either scan was too early or at the wrong checkpoint
        elif time < (item["time"] - CHECK_IN_WINDOW):
            return (
                {"valid": False, "reason": "wrong checkpoint"} | check_in
                if valid_id and valid_time
                else {"valid": False, "reason": "wrong time of scan"} | check_in
            )


def analyse_checkins(client: mqtt.Client):
    """
    handles overdue scans by checking whether the soonest expected scan was validated
    """

    # for as long as a shift is ongoing, these checks need be made
    while SHIFT_STATUS:
        # if all check-ins have been validated / circuit is exhausted
        print("checking")
        if not ALARM_ON_OFF and not CIRCUIT:
            client.publish(topic=DONE, payload=None, qos=2)
            break

        # 1. check the current time
        # 2. compare it against the soonest expected check-in (reason for sorting)
        # 3. if the check-in time has passed, remove it from the queue. if not, proceed
        # 4. if it reads False, some sentry hasn't checked-in in time and that's a problem, snitch
        # 5. if the shift was validated, the checked flag should read True and the shift proceeds

        time_now = int(datetime.timestamp(datetime.now()))  # 1

        if time_now > CIRCUIT[0]["time"] + CHECK_IN_WINDOW:  # 2
            print("analysed")
            current = CIRCUIT.popleft()  # 3
            if not ALARM_ON_OFF and not current["checked"]:  # 4 -> only checked if alarm is off
                client.publish(topic=CHKS_OVERDUE, payload=json.dumps(current), qos=2)

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
        payload = {"id": CLIENT_ID, "connected": True}
        client.publish(topic=CONNECTED, payload=json.dumps(payload), qos=2)

        # subscribe to relevant topics each time it connects
        # this includes at startup and reconnection
        # list of (topic, QoS) tuples
        client.subscribe(
            [(MONITOR_SENTRY_CIRCUIT, 2), (SHIFT_ON_OFF, 2), (SENTRY_SCAN_INFO, 2), (ALARM, 2)]
        )

    # using connect_async() will retry connection until established


def on_mqtt_message(client: mqtt.Client, userdata, message):
    """
    callback event handler, called when a message is published on any subscribed topic
    """

    topic = message.topic

    global CIRCUIT
    global SHIFT_STATUS
    global ALARM_ON_OFF

    # circuit sent by the broker
    if topic == MONITOR_SENTRY_CIRCUIT:
        # the sentry circuit will be sent as a JSON bytearray over MQTT
        payload: dict = json.loads(message.payload)

        # at this point, payload is now a list of Python dictionaries - the generated route
        # the goal is to construct another list of python dictionaries of the form:

        # [{
        #     id: sentry ID to expect
        #     checkpoint: checkpoint at which above sentry is expected
        #     time: time at which the sentry is expected (epoch)
        #     checked: whether the sentry has validly checked in or not
        # },
        # others...]

        # which is what is stored in the 'route' key of each dict in the 'payload' list
        # this is essentially a list/queue of check-ins

        CIRCUIT = generate_checkins(payload)

        # passing the analyser to a separate thread to avoid blocking the main thread
        # since the analyser has a conditional infinite loop, running it on this thread
        # will halt all other processes until the loop is terminated, which is undesirable
        analyser = threading.Thread(target=analyse_checkins, args=[client], daemon=True)
        analyser.start()

    # check-in sent by any checkpoint
    elif topic == SENTRY_SCAN_INFO:
        # the check-in info will be sent as a JSON bytearray over MQTT
        payload: dict = json.loads(message.payload)

        # at this point, payload is now a Python dictionary of the form
        # {
        #     checkpoint-id: checkpoint ID at which the sentry has checked in
        #     sentry-id: ID of the card assigned to that sentry
        #     scan-time: time at which the sentry has scanned
        # }

        # these are checked against the checkpoint, id, and time keys respectively, of each dict in CIRCUIT
        # if a match is found, the value of the checked key is set to True
        # else send validation result to web app

        # pass in a list of relevent values: [chk, id, time]
        validation_result = validate_scan(check_in=payload)
        client.publish(topic=ALERTS, payload=json.dumps(validation_result), qos=2)

    # checker for shift status message
    elif topic == SHIFT_ON_OFF:
        payload: str = message.payload.decode("utf-8")

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

    # checker for alarm signal
    elif topic == ALARM:
        payload: str = message.payload.decode("utf-8")

        if payload == "ON":
            ALARM_ON_OFF = True
            print("alarm triggered")
        elif payload == "OFF":
            ALARM_ON_OFF = False
            print("alarm silenced")


def on_mqtt_disconnect(client: mqtt.Client, userdata, rc):
    print("MQTT disconnected")


def on_mqtt_log(client, userdata, level, buf):
    print("MQTT log:", buf)


def launch_circuit_handler():
    # create client instance
    handler = mqtt.Client(client_id=CLIENT_ID, clean_session=True, reconnect_on_failure=True)
    # configure client with broker credentials
    handler.username_pw_set(username=MQTT_UNAME, password=MQTT_PASS)
    # set LWT message, sent on unprecedented disconnect
    lwt = {"id": CLIENT_ID, "connected": False}
    handler.will_set(topic=CONNECTED, payload=json.dumps(lwt))
    # attach defined event callback functions to created client
    handler.on_connect = on_mqtt_connect
    handler.on_message = on_mqtt_message
    handler.on_disconnect = on_mqtt_disconnect
    handler.on_log = on_mqtt_log
    # connect to broker asynchronously
    time.sleep(2)  # wait for 5 seconds after web app launch to connect
    handler.connect_async(host=MQTT_HOST, keepalive=3600)
    # start listening loop on a background thread
    handler.loop_start()


if __name__ == "__main__":
    launch_circuit_handler()
