import requests
import hashlib
from datetime import datetime, timedelta
import time
import paho.mqtt.client as mqtt
import json
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning

hass_options = json.load(open('/data/options.json'))
mqtt_response = requests.get("http://supervisor/services/mqtt", headers={
    "Authorization": "Bearer " + os.environ.get('SUPERVISOR_TOKEN')
}).json()["data"]

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
currentToken = ""


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
    currentToken = requests.post(
        url, json=data, headers=headers, verify=False).json()["result"]["stok"]

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


def move(direction):
    global headers
    global url
    global currentToken
    return requests.post(
        url + "/stok=" + currentToken + "/ds",
        json={
            "method": "do", "motor": {
                "move": {
                    "x_coord": "-10" if direction == "left" else "10" if direction == "right" else "0",
                    "y_coord": "-10" if direction == "down" else "10" if direction == "up" else "0"
                }
            }
        },
        headers=headers,
        verify=False
    )


def on_message(client, userdata, message):
    payload = str(message.payload.decode("utf-8")).lower()
    print(message.topic)
    if message.topic == hass_options["mqtt_client_id"] + "/privacy/set" and (payload == "on" or payload == "off"):
        if privacy_set(payload).json()["error_code"] == 0:
            client.publish(
                hass_options["mqtt_client_id"] + "/privacy", payload.upper())
    if message.topic == hass_options["mqtt_client_id"] + "/move/right" or message.topic == hass_options["mqtt_client_id"] + "/move/left" or message.topic == hass_options["mqtt_client_id"] + "/move/up" or message.topic == hass_options["mqtt_client_id"] + "/move/down":
        print(move(message.topic.split("/")[2]).json())


def on_connect(client, userdata, flags, rc):
    client.subscribe(hass_options["mqtt_client_id"] + "/move/right")
    client.subscribe(hass_options["mqtt_client_id"] + "/move/left")
    client.subscribe(hass_options["mqtt_client_id"] + "/move/up")
    client.subscribe(hass_options["mqtt_client_id"] + "/move/down")
    client.subscribe(hass_options["mqtt_client_id"] + "/privacy/set")


client = mqtt.Client(client_id=hass_options["mqtt_client_id"])
client.username_pw_set(username=mqtt_username, password=mqtt_password)
client.on_message = on_message
client.on_connect = on_connect
client.connect(mqtt_response["host"], mqtt_response["port"], 60)

token_every_minutes = 30
timer = datetime.now() + timedelta(minutes=token_every_minutes)

client.loop_start()
while True:
    if (datetime.now() - timer).seconds >= token_every_minutes*60:
        try:
            refresh_token()
        except:
            print("Oops, seems like something went wrong!")
        timer = datetime.now()
    time.sleep(.1)
