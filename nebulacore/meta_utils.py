import re
from nxtools import *
from .common import *

def shorten(instr, nlen):
    line = instr.split("\n")[0]
    if len(line) < 100:
        return line
    return line[:nlen] + "..."


def filter_match(f, r):
    """OR"""
    if type(f) == list:
        res = False
        for fl in f:
            if re.match(fl, r):
                return True
        return False
    else:
        return re.match(f, r)

def tree_indent(data):
    has_children = False
    for i, row in enumerate(data):
        value = row["value"]
        depth = len(value.split("."))
        parentindex = None
        for j in range(i - 1, -1, -1):
            if value.startswith(data[j]["value"] + "."):
                parentindex = j
                data[j]["has_children"] = True
                break
        if parentindex is None:
            data[i]["indent"] = 0
            continue
        has_children = True
        data[i]["indent"] = data[parentindex]["indent"] + 1

    for i, row in enumerate(data):
        role = row.get("role", "option")
        if role in ["label", "hidden"]:
            continue
        elif has_children and row.get("has_children"):
            data[i]["role"] = "header"
        else:
            data[i]["role"] = "option"

#
# CS Caching
#

FMH_DATA = {} # id_folder-->key
def folder_metaset_helper(id_folder, key):
    if id_folder not in FMH_DATA:
        d = {}
        for fkey, settings in config["folders"].get(id_folder, {}).get("meta_set", []):
            d[fkey] = settings or {}
        FMH_DATA[id_folder] = d
    return FMH_DATA.get(id_folder, {}).get(key, {})


CSH_DATA = {} # key --> id_folder
def csdata_helper(meta_type, id_folder):
    key = meta_type.key
    if key not in CSH_DATA:
        CSH_DATA[key] = {
                0 : config["cs"].get(meta_type["cs"], [])
            }
    if id_folder not in CSH_DATA[key]:
        folder_settings = folder_metaset_helper(id_folder, meta_type.key)
        folder_cs = folder_settings.get("cs", meta_type.get("cs", "urn:special:nonexistent-cs"))
        folder_filter = folder_settings.get("filter")
        fdata = config["cs"].get(folder_cs, [])
        if folder_filter:
            CSH_DATA[key][id_folder] = [r for r in fdata if filter_match(folder_filter, r[0])]
        else:
            CSH_DATA[key][id_folder] = fdata
    return CSH_DATA[key].get(id_folder, False) or CSH_DATA[key][0]


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
                settings = settings or {}
                CSA_DATA[key][id_folder][value] = settings.get("aliases", {})
                break
        else:
            for csval, settings in csdata_helper(meta_type, 0):
                if csval == value:
                    settings = settings or {}
                    CSA_DATA[key][id_folder][value] = settings.get("aliases", {})
                    break
            else:
                CSA_DATA[key][id_folder][value] = {}
    return CSA_DATA[key][id_folder][value].get(lang) or CSA_DATA[key][id_folder][value].get("en", value)


CSD_DATA = {}
def csd_helper(meta_type, id_folder, value, lang):
    key = meta_type.key
    if not key in CSD_DATA:
        CSD_DATA[key] = {}
    if not id_folder in CSD_DATA[key]:
        CSD_DATA[key][id_folder] = {}
    if not value in CSD_DATA[key][id_folder]:
        for csval, settings in csdata_helper(meta_type, id_folder):
            if csval == value:
                CSD_DATA[key][id_folder][value] = settings.get("description", {})
                break
        else:
            for csval, settings in csdata_helper(meta_type, 0):
                if csval == value:
                    CSD_DATA[key][id_folder][value] = settings.get("description", {})
                    break
            else:
                CSD_DATA[key][id_folder][value] = {}
    return CSD_DATA[key][id_folder][value].get(lang) or CSD_DATA[key][id_folder][value].get("en", value)
