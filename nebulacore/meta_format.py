import time

from nxtools import *

from .common import *
from .constants import *

if PYTHON_VERSION < 3:
    str_type = unicode
else:
    str_type = str


def shorten(instr, nlen):
    line = instr.split("\n")[0]
    if len(line) < 100:
        return line
    return line[:nlen] + "..."


#
# CS Caching
#

FMH_DATA = {} # id_folder-->key
def folder_metaset_helper(id_folder, key):
    if id_folder not in FMH_DATA:
        d = {}
        for fkey, settings in config["folders"].get(id_folder, {}).get("meta_set", []):
            d[fkey] = settings
        FMH_DATA[id_folder] = d
    return FMH_DATA.get(id_folder, {}).get(key, {})


CSH_DATA = {} # key --> id_folder
def csdata_helper(meta_type, id_folder):
    key = meta_type.key
    if key not in CSH_DATA:
        CSH_DATA[key] = {
                0 : config["cs"].get(meta_type.settings["cs"], [])
            }
    if id_folder not in CSH_DATA[key]:
        folder_settings = folder_metaset_helper(id_folder, meta_type.key)
        folder_cs = folder_settings.get("cs", False)
        CSH_DATA[key][id_folder] = config["cs"].get(folder_cs, [])
    return CSH_DATA[key].get(id_folder, None) or CSH_DATA[key][0]


CSA_DATA = {}
def csa_helper(meta_type, id_folder, value, lang):
    key = meta_type.key
    if not key in CSA_DATA:
        CSA_DATA[key] = {}
    if not id_folder in CSA_DATA[key]:
        CSA_DATA[key][id_folder] = {}
    if not value in CSA_DATA[key][id_folder]:
        for csval, settings in csdata_helper(meta_type, id_folder):
            if csval == value:
                    CSA_DATA[key][id_folder][value] = settings.get("aliases", {})
                    break
        else:
            CSA_DATA[key][id_folder][value] = {}
    return CSA_DATA[key][id_folder][value].get(lang, value)


#
# Formating helpers
#

def format_text(meta_type, value, **kwargs):
    if "shorten" in kwargs:
        return shorten(value, kwargs["shorten"])
    return value


def format_integer(meta_type, value, **kwargs):
    value = int(value)
    if not value and meta_type.settings.get("hide_null", False):
        return ""

    #TODO: DEPRECATED??
    if kwargs.get("mode", False) == "hub":
        if meta_type.key == "id_folder":
            fconfig = config["folders"].get(value, {"color" : 0xaaaaaa, "title" : "-"})
            return "<span class='label' style='background-color : #{:06x}'>{}</span>".format(fconfig["color"], fconfig["title"])
        if meta_type.key == "qc/state":
            c, i = {
                    0 : ["#a0a0a0", "flag-outline"],
                    1 : ["#cc0000", "flag-outline"],
                    2 : ["#00cc00", "flag-outline"],
                    3 : ["#cc0000", "flag"],
                    4 : ["#00cc00", "flag"],
                }[value]
            return "<span class='label' style='background-color : {}'><i class='mdi mdi-{}'></i></span>".format(c,i)

    if meta_type.key == "file/size":
        return format_filesize(value)

    if meta_type.key == "status":
        return get_object_state_name(value).upper()

    if meta_type.key == "content_type":
        return get_content_type_name(value).upper()

    if meta_type.key == "media_type":
        return get_media_type_name(value).upper()

    return value


def format_numeric(meta_type, value, **kwargs):
    if type(value) not in [int, float]:
        try:
            value = float(value)
        except ValueError:
            value = 0
    return "{:.03f}".format(value)


def format_boolean(meta_type, value, **kwargs):
    value = int(value)
    #TODO: Deprecated?
    if kwargs.get("mode", False) == "hub":
        if meta_type.key == "promoted":
            return [
                    "<i class=\"mdi mdi-star-outline\"></i>",
                    "<i class=\"mdi mdi-star\"></i>"
                ][value]
        else:
            return [
                    "<i class=\"mdi mdi-checkbox-blank-outline\"></i>",
                    "<i class=\"mdi mdi-checkbox-marked-outline\"></i>"
                ][value]
    return ["no", "yes"][bool(value)]


def format_datetime(meta_type, value, **kwargs):
    time_format = meta_type.settings.get("format", False) or kwargs.get("format", "%Y-%m-%d %H:%M")
    return format_time(value, time_format)


def format_timecode(meta_type, value, **kwargs):
    return s2time(value)


def format_regions(meta_type, value, **kwargs):
    return "{} regions".format(len(value))


def format_fract(meta_type, value, **kwargs):
    return value # TODO


def format_select(meta_type, value, **kwargs):
    lang = kwargs.get("lang", "en")
    full = kwargs.get("full", False)
    id_folder = kwargs["parent"].meta.get("id_folder", 0)
    if full:
        result = []
        for csval, settings in csdata_helper(meta_type, id_folder):
            result.append({
                    "value" : csval,
                    "alias" : settings.get("aliases", {}).get(lang) or csval,
                    "selected" : value == csval
                })
        return sorted(result, key=lambda x: str(x["value"])) if full else "---"
    else:
        return csa_helper(meta_type, id_folder, value, lang)


def format_list(meta_type, value, **kwargs):
    return value # TODO

def format_color(meta_type, value, **kwargs):
    return "#{0:06X}".format(value)


humanizers = {
        -1       : None,
        STRING   : format_text,
        TEXT     : format_text,
        INTEGER  : format_integer,
        NUMERIC  : format_numeric,
        BOOLEAN  : format_boolean,
        DATETIME : format_datetime,
        TIMECODE : format_timecode,
        REGIONS  : format_regions,
        FRACTION : format_fract,
        SELECT   : format_select,
        LIST     : format_list,
        COLOR    : format_color
    }
