sudo systemctl daemon-reload
sudo systemctl enable mqtt-ingest.service
sudo systemctl start mqtt-ingest.service
sudo systemctl status mqtt-ingest.service
journalctl -u mqtt-ingest.service -f