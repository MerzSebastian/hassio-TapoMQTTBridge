## Home Assistant Addon: Tapo MQTT Bridge

# Installation
To install this add-on, follow these steps:
1. Open the Home Assistant web interface
2. Click on the Supervisor tab
3. Click on Add-on Store
4. Add the following URL to the "Repositories" field: https://github.com/MerzSebastian/hassio-TapoMQTTBridge
5. Click on the "Add" button
6. Find the add-on you want to install and click on it
7. Click on the "Install" button

# Configuration
The add-on can be configured using the config tab.
Here's an overview of the available options:
* ```ip```: The ip of the tapo c200 cam
* ```username```: The username for the tapo c200 cam
* ```password```: The password for the tapo c200 cam
* ```mqtt_client_id```: Custom mqtt client name (default: tapo-cam)


Add the following to your configuration.yaml (replace <username>, <password> and <ip>)
```yaml
mqtt:
  button:
    - unique_id: tapo-cam_up
      name: "Tapo Cam - UP"
      command_topic: "tapo-cam/move/up"
      payload_press: "10"
    - unique_id: tapo-cam_down
      name: "Tapo Cam - DOWN"
      command_topic: "tapo-cam/move/down"
      payload_press: "10"
    - unique_id: tapo-cam_left
      name: "Tapo Cam - LEFT"
      command_topic: "tapo-cam/move/left"
      payload_press: "10"
    - unique_id: tapo-cam_right
      name: "Tapo Cam - RIGHT"
      command_topic: "tapo-cam/move/right"
      payload_press: "10"
  switch:
    - unique_id: tapo-cam_privacy_switch
      name: "Tapo Cam - Privacy Switch"
      command_topic: "tapo-cam/privacy/set"
      payload_on: "ON"
      payload_off: "OFF"
camera:
  - platform: ffmpeg
    name: Tapo-C200
    input: -rtsp_transport tcp -i rtsp://<username>:<password>@<ip>:554/stream1
```

Add the following to lovelance to have a basic integration
```yaml
type: vertical-stack
cards:
  - show_state: true
    show_name: true
    camera_view: auto
    type: picture-entity
    entity: camera.tapo_c200
  - square: false
    columns: 3
    type: grid
    cards:
      - show_name: false
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: switch.tapo_cam_privacy_switch
        icon: mdi:eye-off
        icon_height: 22px
      - show_name: false
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: button.tapo_cam_up
        icon: mdi:arrow-up-bold
        icon_height: 22px
      - show_name: false
        show_icon: true
        type: button
        tap_action:
          action: call-service
          service: camera.snapshot
          target:
            entity_id: camera.tapo_c200
          data:
            filename: /media/snapshot.jpg
        icon: mdi:fullscreen
        icon_height: 22px
      - show_name: false
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: button.tapo_cam_left
        icon: mdi:arrow-left-bold
        icon_height: 22px
      - show_name: false
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: button.tapo_cam_down
        icon: mdi:arrow-down-bold
        icon_height: 22px
      - show_name: false
        show_icon: true
        type: button
        tap_action:
          action: toggle
        entity: button.tapo_cam_right
        icon: mdi:arrow-right-bold
        icon_height: 22px
```
# Usage
If you followed the setup steps correctly you now should have a lovelance element which can controll your tapo-c200 cam
![](https://github.com/MerzSebastian/hassio-TapoMQTTBridge/blob/main/sample.PNG)

# Credits
This add-on was created by Sebastian Merz.

# Support
If you have any issues or feature requests, please open an issue on the GitHub repository.
