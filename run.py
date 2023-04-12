from app import app
import threading
import trial


# def countdown():
#     for num, _ in enumerate(range(20)):
#         print(threading.current_thread().name)
#         print(num)
#         time.sleep(3)
#         sth()
#         time.sleep(3)


# def sth():
#     print("sth")


if __name__ == "__main__":
    mqtt_client = threading.Thread(target=trial.launch_circuit_handler, daemon=True)
    mqtt_client.start()
    app.run(debug=False)
