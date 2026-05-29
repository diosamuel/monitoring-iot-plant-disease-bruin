#!/usr/bin/env python3
"""
Simple Soil Moisture Sensor Simulator
Publishes soil moisture to MQTT.
"""

import paho.mqtt.client as mqtt
import time
import random

# Simple configuration
broker = "localhost"
port = 1883
topic = "sensors/soil"

def main():
    print("Starting soil moisture simulator...")
    print(f"Publishing to {broker}:{port} topic: {topic}")
    
    client = mqtt.Client()
    moisture = 50.0  # Start at 50%
    
    try:
        client.connect(broker, port)
        client.loop_start()
        
        while True:
            # Change moisture slightly
            change = random.uniform(-2, 2)
            moisture += change
            
            # Keep between 0-100%
            moisture = max(0, min(100, moisture))
            
            # Create payload
            payload = f"soil={round(moisture, 1)}"
            
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