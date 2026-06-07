import json
import os
from datetime import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

BROKER_HOST = os.getenv("MQTT_HOST")
BROKER_PORT = int(os.getenv("MQTT_PORT"))
TOPIC = os.getenv("MQTT_TOPIC")

print(BROKER_HOST, BROKER_PORT, TOPIC)

JSONL_PATH = os.path.join(os.path.dirname(__file__), "..", "sources", "esp32_sensor.jsonl")


def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    raw_payload = msg.payload.decode()

    try:
        values = {}

        for item in raw_payload.split(";"):
            if not item.strip():
                continue

            key, value = item.split("=", 1)

            if key in {"temp", "humid", "soil"}:
                values[key] = float(value)

        if not all(k in values for k in ["temp", "humid", "soil"]):
            print(f"Ignored invalid payload: {raw_payload}")
            return

        event_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        row = {
            "temp": values["temp"],
            "humid": values["humid"],
            "soil": values["soil"],
            "filename": None,
            "event_time": event_time,
        }

        with open(JSONL_PATH, "a") as f:
            f.write(json.dumps(row) + "\n")

        print(f"Saved: {row}")

    except Exception as e:
        print(f"Ignored payload error: {raw_payload} | {e}")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER_HOST, BROKER_PORT, 60)
client.loop_forever()
