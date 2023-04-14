import threading

import circuit_handler
from app import app, socketio

if __name__ == "__main__":
    # the circuit handler client needs to be launched as soon as the web app is launched
    # i.e. they need to run in parallel
    # the web app was relieved of circuit handling logic because of the infinite loop that checks for overdue scans
    # (inside function 'analyse_checkins' in file 'circuit_handler.py')
    # therefore, to make the web app and circiut handler run in parallel, the circuit handler
    # will be launched on a SEPARATE, BACKGROUND THREAD to the one(s) running the web app
    # the handler needs to:
    # 1. run in the background
    # 2. launch when the web app (server) is launched
    # 3. close when the web app (server) is down
    # hence running it as a daemon (daemon=True)

    # this is implemented below
    mqtt_client = threading.Thread(target=circuit_handler.launch_circuit_handler, daemon=True)
    mqtt_client.start()

    # launching the web app
    # use of socketio (Flask-SocketIO) was recommended in Flask-MQTT's documentation (example)
    socketio.run(app=app, debug=True, use_reloader=False)
