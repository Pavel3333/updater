import codecs
import json
import requests

from urllib import urlretrieve
from zipfile import ZipFile, ZIP_DEFLATED
from os import chdir, rename, remove, listdir, mkdir, makedirs
from os.path import basename, exists, isfile
from xml.etree import ElementTree as ET

from common import *

filename = 'xfw.zip'
urlretrieve('https://nightly.modxvm.com/download/master/xfw_latest.zip', filename)
print filename, 'successfully downloaded'

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

wd = 'temp/'

if exists(wd):
    my_rmtree(wd)
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
        wotmod_path = wd + wotmod_wd + wotmod_name

        name = None
                
        for package in xfw_packages:
            if wotmod_name.startswith(package):
                name = xfw_packages[package]
                break

        if name is None:
            print 'cannot find wotmod', wotmod_name
            continue
        
        if not isfile(wotmod_path): continue
        
        metadata = {}
        
        with Wotmod(wotmod_path) as wotmod:
            metadata = wotmod.getMeta(name)
            
            wotmods_metadata[metadata['id']] = metadata
        
        zip_dir  = 'mods/%s/com.modxvm.xfw/'%(metadata['wot_version_min'])
        
        with RawArchive(metadata['id'], True) as out:
            out.write(wotmod_path, zip_dir + wotmod_name)

my_rmtree(wd)
remove(filename)

config = {}
with codecs.open('config.json', 'r', 'utf-8') as cfg:
    config = json.load(cfg)

for mod_name in wotmods_metadata:
    if mod_name not in config:
        print mod_name, 'not found in config. Creating a new one...'
        config[mod_name] = {}
        continue

    if 'deploy' not in config[mod_name]:
        config[mod_name]['deploy'] = False
    
    metadata = wotmods_metadata[mod_name]
    
    dependencies = set()
    if 'dependencies' not in metadata:
        print 'Dependencies not found in %s. Please set it manually'%(metadata['name'])
        config[mod_name]['dependencies'] = []
    else:
        dependencies.update(set(metadata['dependencies']))
    
    if 'dependencies_optional' in metadata:
        dependencies.update(set(metadata['dependencies_optional']))
    
    config[mod_name]['dependencies'] = list(dependencies)

    if 'name' not in config[mod_name]:
        config[mod_name]['name'] = {
            'RU' : metadata['name'],
            'EN' : metadata['name'],
            'CN' : metadata['name']
        }

    if 'description' not in config[mod_name]:
        config[mod_name]['description'] = {
            'RU' : metadata['description'],
            'EN' : metadata['description'],
            'CN' : metadata['description']
        }
    
    req = requests.post(
        'http://api.pavel3333.ru/add_mod.php',
        data = {
            'ID'      : metadata['id'],
            'name_ru' : config[mod_name]['name']['RU'],
            'name_en' : config[mod_name]['name']['EN'],
            'name_cn' : config[mod_name]['name']['CN'],
            'desc_ru' : config[mod_name]['description']['RU'],
            'desc_en' : config[mod_name]['description']['EN'],
            'desc_cn' : config[mod_name]['description']['CN'],
            'version' : metadata['version'],
            'deploy'  : config[mod_name]['deploy']
        }
    )
    
    try:
        req_decoded = json.loads(req.text)
    except Exception:
        print 'invalid response:', req.text
        continue
    
    if req_decoded['status'] == 'ok':
        print 'successed'
        print 'log:',  req_decoded['log']
        print 'data:', req_decoded['data']
    elif req_decoded['status'] == 'error':
        print 'failed'
        print 'error code:',  req_decoded['code']
        print 'description:', req_decoded['desc']
    else:
        print 'invalid response:', req_decoded

with codecs.open('config.json', 'w', 'utf-8') as cfg:
    json.dump(config, cfg, ensure_ascii=False, sort_keys=True, indent=4)
