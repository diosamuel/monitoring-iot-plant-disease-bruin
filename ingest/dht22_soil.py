import json
import os
from datetime import datetime

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

BROKER_HOST = os.getenv("MQTT_HOST")
BROKER_PORT = int(os.getenv("MQTT_PORT"))
TOPIC = "esp32/dht22"

JSONL_PATH = os.path.join(os.path.dirname(__file__), "..", "sources", "esp32_sensor.jsonl")


def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    raw_payload = msg.payload.decode()
    temp, humid, soil = raw_payload.split(";")
    temp = float(temp.split("=")[1])
    humid = float(humid.split("=")[1])
    soil = float(soil.split("=")[1])
    event_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "temp": temp,
        "humid": humid,
        "soil": soil,
        "filename": None,
        "event_time": event_time,
    }

    with open(JSONL_PATH, "a") as f:
        f.write(json.dumps(row) + "\n")

    print(f"Saved: {row}")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER_HOST, BROKER_PORT, 60)
client.loop_forever()
