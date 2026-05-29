# Simple Plant Monitoring Simulators

Minimal simulators for testing.

## Files

### cam.py - Camera Server
- Serves leaf.jpg on http://localhost:3000/
- Download with: `curl -O http://localhost:3000/`
- Run: `python3 cam.py`

### dht22.py - Temperature/Humidity Simulator
- Publishes to MQTT topic: `sensors/dht22`
- Format: `temp=25.5;humid=60.2`
- Run: `python3 dht22.py`

### soil.py - Soil Moisture Simulator
- Publishes to MQTT topic: `sensors/soil`
- Format: `soil=45.3`
- Run: `python3 soil.py`

## Requirements
```bash
pip install paho-mqtt fastapi uvicorn
```

## Quick Start
1. Start MQTT broker: `mosquitto -v`
2. Run camera: `python3 cam.py`
3. Run DHT22: `python3 dht22.py`
4. Run soil: `python3 soil.py`

## Test
- View image: http://localhost:3000/
- Download: `curl -O http://localhost:3000/`
- Subscribe to MQTT: `mosquitto_sub -t "sensors/#" -v`