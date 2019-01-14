"""
Support to interface with the MPC-HC Web API.
For more details about this platform, please refer to the documentation at

https://home-assistant.io/components/media_player.mpchc/
"""
import logging
import re
from datetime import timedelta
import requests
import voluptuous as vol
import json

from homeassistant.components.media_player import (
    MEDIA_TYPE_MUSIC, MEDIA_TYPE_PLAYLIST, SUPPORT_SELECT_SOURCE, PLATFORM_SCHEMA, SUPPORT_NEXT_TRACK, SUPPORT_PAUSE, SUPPORT_PLAY,
    SUPPORT_PREVIOUS_TRACK, SUPPORT_STOP, SUPPORT_VOLUME_MUTE, SUPPORT_TURN_OFF, SUPPORT_TURN_ON, SUPPORT_VOLUME_STEP, MediaPlayerDevice)
from homeassistant.const import (
    CONF_HOST, CONF_NAME, CONF_PORT, STATE_IDLE, STATE_OFF, STATE_PAUSED,
    STATE_PLAYING)
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'multiroom'
DEFAULT_PORT = 1234
DEFAULT_ID = 0

PLAYLIST_UPDATE_INTERVAL = timedelta(seconds=120)


SUPPORT_MPCHC = SUPPORT_VOLUME_MUTE | SUPPORT_PAUSE | SUPPORT_STOP | \
    SUPPORT_PREVIOUS_TRACK | SUPPORT_NEXT_TRACK | SUPPORT_SELECT_SOURCE | SUPPORT_VOLUME_STEP | \
    SUPPORT_PLAY | SUPPORT_TURN_OFF | SUPPORT_TURN_ON

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
})




def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the MPC-HC platform."""
    name = config.get(CONF_NAME)
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)

    url = '{}:{}'.format(host, port)

    add_entities([MpcHcDevice(name, url)], True)


class MpcHcDevice(MediaPlayerDevice):
    """Representation of a MPC-HC server."""

    def __init__(self, name, url):
        """Initialize the MPC-HC device."""
        self._name = name
        self._url = url
        self._player_variables = {'state': None}
        self._playlists = None
        self._currentplaylist = None
        
        
    def update(self):
        """Get the latest details."""
        if self._player_variables['state'] is not None:
            try:
                response = requests.get(
                    '{}/?command=status'.format(self._url), params={'player_name':self._name}, timeout=3)
                
                self._player_variables = json.loads(response.text)
                if self._playlists is None:
                    response = requests.get('{}/?command=playlist'.format(self._url), params={'player_name':self._name}, timeout=3)
                    response_data = json.loads(response.text)
                    self._playlists = response_data['playlist']
            except requests.exceptions.RequestException:
                _LOGGER.warning("not update mediaplayer")

    def _send_command(self, command_id):
        """Send a command to MPC-HC via its window message ID."""
        try:
            playlist_id = self._playlists.index(self._currentplaylist) if self._currentplaylist in self._playlists else None 
            params = {"command": command_id, "playlist": playlist_id, "player_name": self._name}
            requests.get("{}/".format(self._url),
                         params=params, timeout=3)
        except requests.exceptions.RequestException:
            _LOGGER.error("Could not send command %d to Multiroom at: %s",
                          command_id, self._url)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        state = self._player_variables.get('state', None)

        if state is None:
            return STATE_OFF
        if state == 'connect':
            return STATE_OFF    
        if state == 'playing':
            return STATE_PLAYING
        if state == 'paused':
            return STATE_PAUSED
		
        return STATE_IDLE

    @property
    def media_title(self):
        """Return the title of current playing media."""
        return self._player_variables.get('file', None)

    @property
    def volume_level(self):
        """Return the volume level of the media player (0..1)."""
        return float(self._player_variables.get('volumelevel', 0)) * 100.0

    @property
    def is_volume_muted(self):
        """Return boolean if volume is currently muted."""
        return self._player_variables.get('muted', '0') == '1'

    @property
    def media_duration(self):
        """Return the duration of the current playing media in seconds."""
        duration = self._player_variables.get(
            'durationstring', "00:00:00").split(':')
        return \
            int(duration[0]) * 3600 + \
            int(duration[1]) * 60 + \
            int(duration[2])

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_MPCHC

    def volume_up(self):
        """Volume up the media player."""
        self._send_command("player_volume_up")

    def volume_down(self):
        """Volume down media player."""
        self._send_command("player_volume_down")

    def mute_volume(self, mute):
        """Mute the volume."""
        self._send_command("player_mute")

    def play_media(self, media_type, media_id, **kwargs):
        """Send play command."""
        if media_type == MEDIA_TYPE_PLAYLIST:
            if media_id in self._playlists:
                self._currentplaylist = media_id
                self._send_command("player_play")
            else:
                self._currentplaylist = None
                _LOGGER.warning(str.format("Unknown playlist name %s.", media_id))

    def media_pause(self):
        """Send pause command."""
        self._send_command("player_play_pause")
    def media_play(self):
        """Send pause command."""
        if self._player_variables['state']=='playing' or self._player_variables['state']=='paused': 
            self._send_command("player_play_pause")
        else:
            self.play_media(MEDIA_TYPE_PLAYLIST, self.source)    
    def media_stop(self):
        """Send stop command."""
        self._send_command("player_stop")

    def media_next_track(self):
        """Send next track command."""
        self._send_command("player_next_track")

    def media_previous_track(self):
        """Send previous track command."""
        self._send_command("player_previous_track")
        
    @property
    def source(self):
        """Name of the current input source."""
        return self._currentplaylist
    @property
    def source_list(self):
        """Return the list of available input sources."""
        return self._playlists

    def select_source(self, source):
        """Choose a different available playlist and play it."""
        self.play_media(MEDIA_TYPE_PLAYLIST, source)

    def turn_off(self):
        """Service to send the MPD the command to stop playing."""
        self._send_command("player_stop")
        self._player_variables['state']=None
        """self._currentplaylist = None"""
        

    def turn_on(self):
        """Service to send the MPD the command to start playing."""
        self._player_variables['state']='connect'        