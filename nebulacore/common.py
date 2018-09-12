import os
import sys
import json
import time

import hashlib
import socket

from xml.etree import ElementTree as ET

from nxtools import *

from .constants import *

logging.show_time = True


if PLATFORM == "windows":
    python_cmd = "c:\\python27\python.exe"
    def ismount(path):
        return True
else:
    python_cmd = "python"
    from posixpath import ismount

#
# Config
#

class Config(dict):
    def __init__(self):
        super(Config, self).__init__()
        self["site_name"] = "Unnamed"
        self["user"] = "Nebula"              # Service identifier. Should be overwritten by service/script.
        self["host"] = socket.gethostname()  # Machine hostname
        self["storages"] = {}
        self["rights"] = {}
        self["folders"] = {}
        self["playout_channels"] = {}
        self["ingest_channels"] = {}
        self["cs"] = {}
        self["views"] = {}
        self["meta_types"] = {}
        self["actions"] = {}

        if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
            local_settings_path = sys.argv[1]
        else:
            local_settings_path = "settings.json"

        settings_files = [
                    "/etc/nebula.json",
                    local_settings_path
                ]
        settings = {}
        for settings_file in settings_files:
            if os.path.exists(settings_file):
                try:
                    settings.update(json.load(open(settings_file)))
                except Exception:
                    log_traceback(handlers=False)

        if not settings:
            critical_error("Unable to open site settings")
        self.update(settings)

config = Config()

#
# Utilities
#

def get_hash(string):
    string = string + config.get("hash_salt", "")
    string = encode_if_py3(string)
    return hashlib.sha256(string).hexdigest()

#
# Nebula response object
#

class NebulaResponse(object):
    def __init__(self, response=200, message=None, **kwargs):
        self.dict = {
                "response" : response,
                "message" : message
            }
        self.dict.update(kwargs)

    @property
    def json(self):
        return json.dumps(self.dict)

    @property
    def response(self):
        return self["response"]

    @property
    def message(self):
        return self["message"] or "(no message)"

    @property
    def data(self):
        return self.get("data", {})

    @property
    def is_success(self):
        return self.response < 400

    @property
    def is_error(self):
        return self.response >= 400

    def get(self, key, default=False):
        return self.dict.get(key, default)

    def __getitem__(self, key):
        return self.dict[key]

    def __len__(self):
        return self.is_success

#
# Messaging
#

class Messaging():
    def __init__(self):
        self.configured = False

    def configure(self):
        self.addr = config.get("seismic_addr", "224.168.2.8")
        self.port = int(config.get("seismic_port", 42112))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
        self.configured = True

    def send(self, method, **data):
        if not self.configured:
            return
        try:
            self.sock.sendto(
                encode_if_py3(
                    json.dumps([
                        time.time(),
                        config["site_name"],
                        config["host"],
                        method,
                        data
                        ])
                    ),
                (self.addr, self.port)
                )
        except Exception:
            log_traceback(handlers=False)

messaging = Messaging()

#
# Logging
#

def seismic_log(**kwargs):
    messaging.send("log", **kwargs)

logging.user = config["user"]
logging.add_handler(seismic_log)

#
# Filesystem
#

class Storage(object):
    def __init__(self, id,  **kwargs):
        self.id = int(id)
        self.settings = kwargs
        self.is_dead = False
        self.last_check = 0
        self.check_interval = 2

    def __getitem__(self, key):
        return self.settings[key]

    def __repr__(self):
        return "storage ID:{} ({})".format(self.id, self["title"])

    @property
    def title(self):
        if "title" in self.settings:
            return self.settings["title"]
        return "Storage {}".format(self.id)

    @property
    def local_path(self):
        if str(self.id) in config.get("alt_storages", []):
            alt_storage_config = config["alt_storages"][str(self.id)]
            if config.get("id_service", -1) in alt_storage_config.get("services", []):
                return alt_storage_config["path"]

        if self["protocol"] == "local":
            return self["path"]
        elif PLATFORM == "unix":
            return os.path.join("/mnt/{}_{:02d}".format(config["site_name"], self.id))
        #elif PLATFORM == "windows":
            #TODO
            #logging.warning("Unsuported {} protocol '{}' on this platform.".format(self, self["protocol"]))
        return ""

    def __len__(self):
        if self["protocol"] == "local" and os.path.isdir(self["path"]):
            return True
        return ismount(self.local_path) and len(os.listdir(self.local_path)) != 0


class Storages(object):
    def __getitem__(self, key):
        #TODO error_handling
        return Storage(key, **config["storages"][key])

    def __iter__(self):
        return config["storages"].__iter__()

storages = Storages()
