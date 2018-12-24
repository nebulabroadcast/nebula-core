import pprint
import copy

from .common import *
from .constants import *
from .metadata import meta_types

__all__ = ["BaseObject", "AssetMixIn", "ItemMixIn", "BinMixIn", "EventMixIn", "UserMixIn"]

class BaseObject(object):
    required = []
    defaults = {}

    def __init__(self, id=False, **kwargs):
        self.text_changed = self.meta_changed = False
        self.is_new = True
        self.meta = {}
        meta = kwargs.get("meta", {})
        if id:
            assert type(id) == int, "{} ID must be integer".format(self.object_type)
        assert meta is not None, "Unable to load {}.  Meta must not be 'None'.".format(self.object_type)
        assert hasattr(meta, "keys"), "Incorrect meta!"
        for key in meta:
            self.meta[key] = meta[key]
        if "id" in self.meta:
            self.is_new = False
        elif not self.meta:
            if id:
                self.load(id)
                self.is_new = False
            else:
                self.new()
                self.is_new = True
                self["ctime"] = self["mtime"] = time.time()
        for key in self.defaults:
            if not key in self.meta:
                self.meta[key] = self.defaults[key]

    @property
    def id(self):
        return self.meta.get("id", False)

    @property
    def object_type(self):
        return self.__class__.__name__.lower()

    def keys(self):
        return self.meta.keys()

    def get(self, key, default=False):
        if key in self.meta:
            return self[key]
        return default

    def __getitem__(self, key):
        key = key.lower().strip()
        if key == "_duration":
            return self.duration
        return self.meta.get(key, meta_types[key].default)

    def __setitem__(self, key, value):
        key = key.lower().strip()
        meta_type = meta_types[key]
        value = meta_type.validate(value)
        if value == self[key]:
            return True # No change
        self.meta_changed = True
        if meta_type["fulltext"] or key == "subclips":
            self.text_changed = True
        if not value and key in self.meta:
            del self.meta[key]
        else:
            self.meta[key] = value
        return True

    def update(self, data):
        for key in data.keys():
            self[key] = data[key]

    def new(self):
        pass

    def load(self, id):
        pass

    def save(self, **kwargs):
        if not kwargs.get("silent", False):
            logging.debug("Saving {}".format(self))
        self["ctime"] = self["ctime"] or time.time()
        if kwargs.get("set_mtime", True):
            self["mtime"] = time.time()
        for key in self.required:
            assert key in self.meta, "Unable to save {}. {} is required".format(self, key)

    def delete(self, **kwargs):
        assert self.id > 0, "Unable to delete unsaved object"

    def __delitem__(self, key):
        key = key.lower().strip()
        if not key in self.meta:
            return
        del self.meta[key]

    def __repr__(self):
        if self.id:
            result = "{} ID:{}".format(self.object_type, self.id)
        else:
            result = "new {}".format(self.object_type)
        if self.object_type == "item" and not hasattr(self, "_asset"):
            title = ""
        else:
            if PYTHON_VERSION >= 3:
                title = self["title"]
            else:
                title = self.meta.get("title", "").encode("utf8", "replace")
        if title:
            result += " ({})".format(title)
        return result

    def __len__(self):
        return not self.is_new

    def show(self, key, **kwargs):
        kwargs["parent"] = self
        return meta_types[key.lstrip("_")].show(self[key], **kwargs)

    def show_meta(self):
        return pprint.pformat(self.meta)






class AssetMixIn(object):
    object_type_id = 0
    required = ["media_type", "content_type", "id_folder"]
    defaults = {"media_type" : VIRTUAL, "content_type" : TEXT}

    def mark_in(self, new_val=False):
        if new_val:
            self["mark_in"] = new_val
        return self["mark_in"]

    def mark_out(self, new_val=False):
        if new_val:
            self["mark_out"] = new_val
        return self["mark_out"]

    @property
    def file_path(self):
        if self["media_type"] != FILE:
            return ""
        try:
            return os.path.join(storages[int(self["id_storage"])].local_path, self["path"])
        except (KeyError, IndexError, ValueError):
            # Yes. empty string. keep it this way!!! (because of os.path.exists and so on)
            # Also: it evals as false
            return ""

    @property
    def duration(self):
        dur = float(self.meta.get("duration",0))
        mki = float(self.meta.get("mark_in" ,0))
        mko = float(self.meta.get("mark_out",0))
        if not dur:
            return 0
        if mko > 0:
            dur -= dur - mko
        if mki > 0:
            dur -= mki
        return dur

    @property
    def fps(self):
        n, d = [int(k) for k in self.meta.get("fps", "25/1").split("/")]
        return n/d

    @property
    def proxy_url(self):
        if not self.id:
            return ""
        tpl = config.get("proxy_url", "/proxy/{id1000:04d}/{id}.mp4")
        id1000 = int(self.id/1000)
        return tpl.format(id1000=id1000, **self.meta)


class ItemMixIn(object):
    object_type_id = 1
    required = ["id_bin", "id_asset", "position"]

    def __getitem__(self, key):
        key = key.lower().strip()
        if not key in self.meta:
            if key not in ["id_asset"] and self.asset:
                return self.asset[key]
            else:
                return meta_types[key].default
        return self.meta[key]

    def mark_in(self, new_val=False):
        if new_val:
            self["mark_in"] = new_val
        return float(self["mark_in"])

    def mark_out(self, new_val=False):
        if new_val:
            self["mark_out"] = new_val
        return float(self["mark_out"])

    @property
    def asset(self):
        pass

    @property
    def bin(self):
        pass

    @property
    def event(self):
        pass

    @property
    def duration(self):
        """Final duration of the item"""
        if self["id_asset"]:
            dur = self.asset["duration"] or 0
        elif self["duration"]:
            dur = self["duration"] or 0
        else:
            return self.mark_out() - self.mark_in()
        if not dur:
            return 0
        mark_in  = self.mark_in()
        mark_out = self.mark_out()
        if mark_out > 0: dur -= dur - mark_out
        if mark_in  > 0: dur -= mark_in
        return dur

    @property
    def fps(self):
        return self.asset.fps

    @property
    def file_path(self):
        if not self["id_asset"]:
            return ""
        return self.asset.file_path


class BinMixIn(object):
    object_type_id = 2
    required = ["bin_type"]
    defaults = {"bin_type" : 0}

    @property
    def duration(self):
        if "duration" not in self.meta:
            duration = 0
            for item in self.items:
                duration += item.duration
            self["duration"] = duration
        return self["duration"]



class EventMixIn(object):
    object_type_id = 3
    required = ["start", "id_channel"]


class UserMixIn(object):
    object_type_id = 4
    required = ["login", "password"]

    def __getitem__(self, key):
        if key == "title":
            return self.meta["login"]
        return super(UserMixIn, self).__getitem__(key)

    def set_password(self, password):
        self["password"] = get_hash(password)

    def has_right(self, key, val=True, anyval=False):
        if self["is_admin"]:
            return True
        key = "can/{}".format(key)
        if not self[key]:
            return False
        if anyval:
            return True
        return self[key] == True or (type(self[key]) == list and val in self[key])
