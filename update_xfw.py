import codecs
import json
import requests

from zipfile import ZipFile, ZIP_DEFLATED
from os import chdir, rename, remove, listdir, mkdir, makedirs
from os.path import basename, exists, isfile
from xml.etree import ElementTree as ET

from common   import *
from entities import *

MOD_NAME = 'xfw'

wotmod_prefix = 'wotmod/com.modxvm.xfw'

xfw_packages = {
    'com.modxvm.xfw.actionscript'   : 'xfw_actionscript',
    'com.modxvm.xfw.filewatcher'    : 'xfw_filewatcher',
    'com.modxvm.xfw.fonts'          : 'xfw_fonts',
    'com.modxvm.xfw.libraries'      : 'xfw_libraries',
    'com.modxvm.xfw.loader'         : 'xfw_loader',
    'com.modxvm.xfw.mutex'          : 'xfw_mutex',
    'com.modxvm.xfw.native'         : 'xfw_native',
    'com.modxvm.xfw.ping'           : 'xfw_ping',
    'com.modxvm.xfw.wotfix.crashes' : 'xfw_wotfix_crashes',
    'com.modxvm.xfw.wotfix.hidpi'   : 'xfw_wotfix_hidpi',
    'com.modxvm.xfw.wwise'          : 'xfw_wwise'
}

wot_version = None

filename = get_archive(MOD_NAME)

wd = 'temp/'

if exists(wd):
    hard_rmtree(wd)
mkdir(wd)

with ZipFile(filename) as archive:
    archive.extractall(
        wd,
        filter(lambda path: path.startswith(wotmod_prefix), archive.namelist())
    )

wotmods_metadata = {}

wotmod_wd = 'wotmod/'
if exists(wd + wotmod_wd):
    for wotmod_name in listdir(wd + wotmod_wd):
        wotmod_path = myjoin(wd, wotmod_wd, wotmod_name)

        name = None
                
        for package_id, package_name in xfw_packages.iteritems():
            if wotmod_name.startswith(package_id):
                name = package_name
                break

        if name is None:
            print 'Cannot find wotmod', wotmod_name
            continue
        
        if not isfile(wotmod_path): continue
        
        wotmod = g_EntityFactory.create(WotMod, wotmod_path)
        metadata = wotmod.entities['packages'][name].meta.copy()

        if not metadata:
            metadata = wotmod.meta

        if wot_version:
            metadata['wot_version_min'] = wot_version

        wotmods_metadata[metadata['id']] = metadata

        if wot_version is None and metadata['wot_version_min']:
            wot_version = metadata['wot_version_min']
        elif wot_version != metadata['wot_version_min']:
            raise ValueError, 'Invalid WoT version: %s, expected %s'%(metadata['wot_version_min'], wot_version)
        
        zip_dir  = 'mods/%s/com.modxvm.xfw/'%(metadata['wot_version_min'])
        
        out = g_EntityFactory.create(RawArchive, metadata['id'], True)
        out.io.write(
            wotmod_path,
            myjoin(zip_dir, wotmod_name)
        )
        out.closeIO()

        wotmod.fini()

soft_rmtree(wd, False)
hard_rmtree(wd)
remove(filename)

add_mods(wotmods_metadata)

raw_input('------ DONE ------')
