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
from ruamel.yaml import YAML, representer
from ruamel.yaml.compat import StringIO
representer.RoundTripRepresenter.ignore_aliases = lambda x, y: True

currentToken = ""
hass_options = json.load(open('/data/options.json'))
censorString = lambda token: (len(token) - 4) * "*" + token[len(token)-4:]
log = lambda value: subprocess.run(f'echo "{datetime.now().strftime("%m/%d/%Y, %H:%M:%S")} | {str(value).replace(currentToken, censorString(currentToken)).replace(hass_options["password"], censorString(hass_options["password"]))}"', shell=True) if hass_options["logging"] else lambda: None


def update_yaml_file(yaml_file_path, update_value):
    with open(yaml_file_path, "r") as yaml_file:
        data = yaml.load(yaml_file)
        initial_data = str(data)

    # mqtt config
    if "mqtt" not in data.keys():
        data["mqtt"] = update_value["mqtt"]
    else:
        for key in update_value["mqtt"].keys():
            for i, button in enumerate(update_value["mqtt"][key]):
                if len([i for i in update_value["mqtt"][key] if i["unique_id"] == button["unique_id"]]) == 1:
                    if key not in data["mqtt"].keys():
                        data["mqtt"][key] = []
                    index_map = [i for i, s in enumerate(data["mqtt"][key]) if s["unique_id"] == button["unique_id"]]
                    if len(index_map) == 0:
                        data["mqtt"][key].append(button)
                    else:
                        data["mqtt"][key][index_map[0]] = button
    # camera config
    if "camera" not in data.keys():
        data["camera"] = update_value["camera"]
    else:
        for i, button in enumerate(update_value["camera"]):
            if len([i for i in update_value["camera"] if i["name"] == button["name"]]) == 1:
                index_map = [i for i, s in enumerate(data["camera"]) if s["name"] == button["name"]]
                if len(index_map) == 0:
                    data["camera"].append(button)
                else:
                    data["camera"][index_map[0]] = button

    # Write the updated data back to the YAML file
    with open(yaml_file_path, "w") as yaml_file:
        yaml.dump(data, yaml_file)

    return initial_data != str(data)

# would be good to make a backup for the config
log("Configuration editor | Checking if configuration.yaml needs update...")
yaml = YAML()
yaml.preserve_quotes = True
update_value = yaml.load(open('/config_update.yaml'))

# replace placeholder in update_Value
update_value["camera"][0]["input"] = update_value["camera"][0]["input"].replace("<username>", hass_options["username"]).replace("<password>", hass_options["password"]).replace("<ip>", hass_options["ip"])
log("Configuration editor | Checking for configuration.yaml updates and applying them if needed")
changes = update_yaml_file('/config/configuration.yaml', update_value)
log("Configuration editor | Where there any updates?: " + str(changes))
if changes:
    log("Configuration editor | Update finished! Restarting Home Assistant")
    # Restart hass core (a bit shitty 'should' work for now), would be nice if i can only reload json somehow. Prob. possible. getting a 403 anyways
    res = requests.post("http://supervisor/core/restart", headers={
        "Authorization": "Bearer " + os.environ.get('SUPERVISOR_TOKEN')
    })
    if res.status_code != 200:
        log("Configuration editor | ERROR => Reloading configuration.yaml resulted in the following response: " + res.text)
    else:
        log("Configuration editor | Good bye!")










#log(yaml.safe_load(open('/config/configuration.yaml')))

# if threse is not mosquito installed or mqtt service available, this will throw an error, maybe use something descriptive to log here instead
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
