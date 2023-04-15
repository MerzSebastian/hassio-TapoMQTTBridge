import requests
import hashlib
from datetime import datetime, timedelta
import time
import paho.mqtt.client as mqtt
import json
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import sys
import subprocess
import uuid

currentToken = ""
f = open('/data/options.json')
hass_options = json.load(f)
f.close()
censorString = lambda token: (len(token) - 4) * "*" + token[len(token)-4:]
log = lambda value: subprocess.run(f'echo "{datetime.now().strftime("%m/%d/%Y, %H:%M:%S")} | {str(value).replace(currentToken, censorString(currentToken)).replace(hass_options["password"], censorString(hass_options["password"]))}"', shell=True) if hass_options["logging"] else lambda: None

mqtt_response = requests.get("http://supervisor/services/mqtt", headers={ "Authorization": "Bearer " + os.environ.get('SUPERVISOR_TOKEN') }).json()
if "data" not in mqtt_response.keys():
    sys.exit(datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + ' | FATAL ERROR | Seems like no mqtt service could be found. Are you sure you installed Mosquitto?')
else:
    mqtt_response = mqtt_response["data"]

mqtt_username = mqtt_response["username"]
mqtt_password = mqtt_response["password"]
url = "https://" + hass_options["ip"] + ":443"
headers = {
    "Host": hass_options["ip"],
    "Referer": url,
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": "Tapo CameraClient Android",
    "Connection": "close",
    "requestByApp": "true",
    "Content-Type": "application/json; charset=UTF-8",
}


def register_mqtt_device():
    f = open('device.json')
    data = json.load(f)
    f.close()
    for cam in hass_options['cams']:
        device_data = {
            "identifiers": [str(uuid.uuid4())],
            "name": "TP-Link Tapo C200 WiFi Security Camera",
            "model": "Tapo C200",
            "manufacturer": "TP-Link"
        }
        for btn in data["mqtt"]["button"]:
            unique_id = f'{cam["unique_id"]}_{btn["unique_id"]}'
            client.publish(f'homeassistant/button/{unique_id}/config', json.dumps({
                "name": btn["name"],
                "object_id": unique_id,
                "unique_id": unique_id,
                "command_topic": f'{cam["unique_id"]}/{btn["command_topic"]}',
                "payload_press": f'{cam["unique_id"]}/{btn["payload_press"]}',
                "device": device_data,
            }))
        for switch in data["mqtt"]["switch"]:
            unique_id = f'{cam["unique_id"]}_{btn["unique_id"]}'
            client.publish(f'homeassistant/switch/{unique_id}/config', json.dumps({
                "name": switch["name"],
                "object_id": unique_id,
                "unique_id": unique_id,
                "command_topic": f'{cam["unique_id"]}/{switch["command_topic"]}',
                "state_topic": f'{cam["unique_id"]}/{switch["state_topic"]}',
                "payload_on": "ON",
                "payload_off": "OFF",
                "state_on": "ON",
                "state_off": "OFF"
                "device": device_data,
            }))

register_mqtt_device()

def refresh_token():
    global headers
    global url
    global currentToken
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    data = {
        "method": "login",
        "params": {
            "hashed": "true",
            "password": hashlib.md5(hass_options["password"].encode('ascii')).hexdigest().upper(),
            "username": hass_options["username"]
        }
    }
    res = requests.post(url, json=data, headers=headers, verify=False)
    if res.status_code == 200:
        currentToken = res.json()["result"]["stok"]


    log(f'Refresh Token => Status code: { str(res.status_code) }, response text: { res.text }' )


# def privacy_get():
#    global headers
#    global currentToken
#    global url
#    return requests.post(
#        url + "/stok=" + currentToken + "/ds",
#        json='{"method": "get", "lens_mask": {"name": ["lens_mask_info"]}}',
#        headers=headers,
#        verify=False
#    )#["lens_mask"]["lens_mask_info"]


def privacy_set(status):
    global headers
    global url
    global currentToken
    return requests.post(
        url + "/stok=" + currentToken + "/ds",
        json={"method": "set", "lens_mask": {
            "lens_mask_info": {"enabled": status}}},
        headers=headers,
        verify=False
    )

def move(direction, steps):
    global headers
    global url
    global currentToken
    requests.post(
        url + "/stok=" + currentToken + "/ds",
        json={
            "method": "do", "motor": {
                "move": {
                    "x_coord": "-" + steps if direction == "left" else steps if direction == "right" else "0",
                    "y_coord": "-" + steps if direction == "down" else steps if direction == "up" else "0"
                }
            }
        },
        headers=headers,
        verify=False
    )

def publish(client, topic, payload):
    log(f'MQTT | Publish => Topic: { topic }, Payload: { payload }')
    client.publish(topic, payload)

def on_message(client, userdata, message):
    payload = str(message.payload.decode("utf-8")).lower()
    log(f'MQTT | Message => Incoming => topic: { message.topic }, payload: { payload }')

    # Privacy
    if message.topic == hass_options["mqtt_client_id"] + "/privacy/set" and (payload == "on" or payload == "off"):
        if privacy_set(payload).json()["error_code"] == 0:
            publish(client, f'{ hass_options["mqtt_client_id"] }/privacy', payload.upper())

    # Move
    valid_topics = [f"{hass_options['mqtt_client_id']}/move/{direction}" for direction in ["right", "left", "up", "down"]]
    if message.topic in valid_topics:
        move(message.topic.split("/")[-1], payload)

def subscribe(client, topic):
    log(f'MQTT | Subscribing => Topic: { topic }')
    client.subscribe(topic)

def on_connect(client, userdata, flags, rc):
    subscribe(client, f'{ hass_options["mqtt_client_id"] }/move/right')
    subscribe(client, f'{ hass_options["mqtt_client_id"] }/move/left')
    subscribe(client, f'{ hass_options["mqtt_client_id"] }/move/up')
    subscribe(client, f'{ hass_options["mqtt_client_id"] }/move/down')
    subscribe(client, f'{ hass_options["mqtt_client_id"] }/privacy/set')


client = mqtt.Client(client_id=hass_options["mqtt_client_id"])
client.username_pw_set(username=mqtt_username, password=mqtt_password)
client.on_message = on_message
client.on_connect = on_connect
client.connect(mqtt_response["host"], mqtt_response["port"], 60)

token_every_minutes = hass_options["refresh_token_polling_interval_minutes"]
timer = datetime.now() + timedelta(minutes=token_every_minutes)

client.loop_start()
while True:
    if (datetime.now() - timer).seconds >= token_every_minutes*60:
        try:
            refresh_token()
            timer = datetime.now()
        except:
            log("ERROR => Seems like the tapo-cam ist not reachable!")
    time.sleep(1)
