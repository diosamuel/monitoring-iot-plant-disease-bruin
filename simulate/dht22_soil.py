#!/usr/bin/env python3
"""
Simple DHT22 Sensor Simulator
Publishes temperature and humidity to MQTT.
"""
import os
import paho.mqtt.client as mqtt
import time
import random

from dotenv import load_dotenv

load_dotenv()

BROKER_HOST = os.getenv("MQTT_HOST")
BROKER_PORT = int(os.getenv("MQTT_PORT"))
TOPIC = os.getenv("MQTT_TOPIC")

def main():
    print("Starting DHT22 simulator...")
    print(f"Publishing to {BROKER_HOST}:{BROKER_PORT} topic: {topic}")
    
    client = mqtt.Client()
    
    try:
        client.connect(BROKER_HOST, BROKER_PORT)
        client.loop_start()
        
        while True:
            # Generate random temperature (20-30°C) and humidity (40-80%)
            temp = round(20 + random.random() * 10, 1)
            humid = round(40 + random.random() * 40, 1)
            soil = round(50 + random.random() * 50, 1)
            
            # Create payload
            payload = f"temp={temp};humid={humid};soil={soil}"
            
            # Publish
            client.publish(topic, payload)
            print(f"Published: {payload}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        client.loop_stop()
        client.disconnect()

main()