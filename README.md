# multiroom
Home assistant multiroom component

This is custom components for Home Assistant.

The multiroom platform allows you to control a Multiroom player from Home Assistant. Unfortunately you will not be able to manipulate the playlist (add or delete songs).

Even though no playlist manipulation is possible, it is possible to use the play_media service to load an existing saved playlist as part of an automation or scene.

To add multiroom to your installation, add the following to your configuration.yaml file:

To add MPD to your installation, add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
media_player:
  - platform: multiroom
    host: IP_ADDRESS
```
Configuration options

host:  IP address of the Host where Music Player Daemon is running.<br>
port:  Port of the Music Player Daemon.<br>
name:  Name of your Music Player Daemon.<br>



