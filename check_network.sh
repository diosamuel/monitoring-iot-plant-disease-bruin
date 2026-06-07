#!/bin/bash

RPI_HOST="192.168.1.29"
SSH_PORT="22"
ESP32_CAM="192.168.1.30"

echo " Network Connectivity Check"

# Check SSH Host
echo "[1/3] Checking Raspberry Pi SSH (${RPI_HOST}:${SSH_PORT})..."

if timeout 3 bash -c "</dev/tcp/${RPI_HOST}/${SSH_PORT}" 2>/dev/null; then
    echo "OK: SSH service available"
else
    echo "ERROR: SSH service unavailable"
fi

echo ""

# Check MQTT Broker
echo "[2/3] Checking MQTT Broker (${RPI_HOST}:1883)..."

if timeout 3 bash -c "</dev/tcp/${RPI_HOST}/1883" 2>/dev/null; then
    echo "OK: MQTT broker available"
else
    echo "ERROR: MQTT broker unavailable"
fi

echo ""

# Check ESP32-CAM
echo "[3/3] Checking ESP32-CAM (${ESP32_CAM})..."

if ping -c 2 -W 2 "${ESP32_CAM}" >/dev/null 2>&1; then
    echo "OK: ESP32-CAM reachable"
else
    echo "ERROR: ESP32-CAM unreachable"
fi