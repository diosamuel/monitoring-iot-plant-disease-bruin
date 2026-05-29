#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

#define DHTPIN 23
#define DHTTYPE DHT22

#define SOIL_PIN 34   // AO soil moisture ke GPIO34

const char* ssid = "SigmaFam";
const char* password = "MIMPIsukses";

const char* mqtt_server = "192.168.1.23";
const int mqtt_port = 1883;
const char* mqtt_topic = "plant/sensor";

WiFiClient espClient;
PubSubClient client(espClient);
DHT dht(DHTPIN, DHTTYPE);

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void reconnect_mqtt() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT... ");

    String clientId = "ESP32-DHT22-SOIL-";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" retry in 2 seconds");
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);

  dht.begin();

  pinMode(SOIL_PIN, INPUT);

  setup_wifi();

  client.setServer(mqtt_server, mqtt_port);

  Serial.println("DHT22 + Soil Moisture MQTT Publisher Started");
}

void loop() {
  if (!client.connected()) {
    reconnect_mqtt();
  }

  client.loop();

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  int soilRaw = analogRead(SOIL_PIN);

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read from DHT22 sensor!");
    delay(2000);
    return;
  }

  String payload = "temp=" + String(temperature, 2) +
                   ";humid=" + String(humidity, 2) +
                   ";soil=" + String(soilRaw);

  client.publish(mqtt_topic, payload.c_str());

  Serial.print("Published: ");
  Serial.println(payload);

  delay(2000);
}