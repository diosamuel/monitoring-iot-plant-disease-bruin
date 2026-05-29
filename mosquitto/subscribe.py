import json
import paho.mqtt.client as mqtt
import duckdb 
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()


BROKER_HOST = os.getenv("MQTT_HOST")   # Mosquitto is on Raspberry Pi
BROKER_PORT = os.getenv("MQTT_PORT")
TOPIC = "esp32/dht22"

conn = duckdb.connect("sources/stg_sensor.duckdb")

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    raw_payload = msg.payload.decode()
    # Split payload
    temp, humid, soil = raw_payload.split(";")
    # Take value after "="
    temp = float(temp.split("=")[1])
    humid = float(humid.split("=")[1])
    soil = float(soil.split("=")[1])
    event_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        INSERT INTO sensor VALUES (?, ?, ?,NULL,?)
    """, (temp, humid, soil, event_time))

    print("Raw message:", raw_payload)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER_HOST, BROKER_PORT, 60)
client.loop_forever()
