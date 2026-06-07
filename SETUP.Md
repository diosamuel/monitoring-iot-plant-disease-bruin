# Setup Server

Assume the Raspberry Pi is running and SSH (port 22) and MQTT (port 1883) services are already enabled.

## 1. Follow the Wiring Diagram

Connect all components according to the provided wiring image.

## 2. Verify Network Connectivity

Make sure the following devices and services are reachable:

### a. Raspberry Pi SSH Service

Verify that the Raspberry Pi is online and SSH is accessible.

Current host: `192.168.1.29`  
> Note: the IP address may change depending on the Wi-Fi network.

### b. MQTT Broker

Verify that the sensor can connect to the MQTT broker running on the Raspberry Pi.

- MQTT Broker: `192.168.1.29:1883`
- Topic: `esp32/sensor`
- Payload format:

```text
temp=n;humid=n;soil=n;
```

### c. ESP32-CAM

Verify that the ESP32-CAM is online and reachable.

Current host: `192.168.1.30`  
> Note: the IP address may change depending on the Wi-Fi network.

### Connectivity Check

Run the following script to verify the network status:

```bash
./check_network.sh
```

## 3. Connect to the Raspberry Pi

Using the default credentials:

```bash
ssh pi@192.168.1.29
```

Password:

```text
raspberrypi
```

## 4. Clone the Repository

```bash
git clone <repository-url>
cd <repository-name>
```

## 5. Configure Environment Variables

Create the `.env` file from the provided example:

```bash
cp .env.example .env
```

Update the values in `.env` according to your environment.

## 6. Configure the Google Cloud Service Account

Place your Google Cloud service account credentials in the appropriate location and update the related configuration in the `.env` file.

## 7. Run the Bruin Pipeline

```bash
bruin run
```

Verify that all services start successfully and that sensor, image, and weather data are processed correctly.