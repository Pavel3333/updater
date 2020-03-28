import codecs
import json

from urllib import urlretrieve
from zipfile import ZipFile, ZIP_DEFLATED
from os import chdir, rename, remove, listdir, mkdir, makedirs
from os.path import basename, exists, isfile
from xml.etree import ElementTree as ET

from common import *

packages_metadata = {}

mods = {
    'com.pavel3333.Autoupdater' : {
        'name' : 'Autoupdater',
        'desc' : 'Autoupdater main module',
        'ver'  : 1.0
    },
    'com.pavel3333.Autoupdater.GUI' : {
        'name' : 'Autoupdater GUI module',
        'desc' : 'Shows Autoupdater GUI in the hangar',
        'ver'  : 1.0
    }
}

game_version = raw_input('Please enter the game version: ')

for mod_id in mods:
    mod = mods[mod_id]
    packages_metadata[mod_id] = {
        'id'              : mod_id,
        'name'            : mod['name'],
        'description'     : mod['desc'],
        'version'         : mod['ver'],
        'wot_version_min' : game_version
    }

add_mods(packages_metadata)
