sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto.service
mosquitto_sub -h localhost -t plant/sensor