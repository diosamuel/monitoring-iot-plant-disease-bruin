#!/usr/bin/env python3
"""
Simple DHT22 Sensor Simulator
Publishes temperature and humidity to MQTT.
"""

import paho.mqtt.client as mqtt
import time
import random

# Simple configuration
broker = "localhost"
port = 1883
topic = "esp32/dht22"

def main():
    print("Starting DHT22 simulator...")
    print(f"Publishing to {broker}:{port} topic: {topic}")
    
    client = mqtt.Client()
    
    try:
        client.connect(broker, port)
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