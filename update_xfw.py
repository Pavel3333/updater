import json

from urllib import urlretrieve
from zipfile import ZipFile, ZIP_DEFLATED
from os import chdir, rename, remove, listdir, mkdir, makedirs
from os.path import basename, exists, isfile
from shutil import rmtree
from xml.etree import ElementTree as ET

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

if not exists('temp'):
    mkdir('temp')

with ZipFile(filename) as archive:
    archive.extractall(
        'temp/',
        filter(lambda path: path.startswith(wotmod_prefix), archive.namelist())
    )

wotmods_metadata = {}

wotmod_wd = 'temp/wotmod/'
if exists(wotmod_wd):
    for wotmod_name in listdir(wotmod_wd):
        wotmod_path = wotmod_wd + wotmod_name

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
        
        with ZipFile(wotmod_path) as wotmod:
            try:
                with wotmod.open('res/mods/xfw_packages/%s/xfw_package.json'%(name)) as meta:
                    metadata = json.load(meta)
                    
                    wotmods_metadata[metadata['id']] = {
                        'name'         : metadata['name'],
                        'description'  : metadata['description'],
                        
                        'version'      : metadata['version'],
                        'dependencies' : metadata['dependencies'],
                        
                        'wot_version_min'        : metadata['wot_version_min'],
                        'wot_version_exactmatch' : metadata['wot_version_exactmatch']
                    }
            except KeyError:
                with wotmod.open('meta.xml') as meta_file:
                    meta = ET.fromstring(meta_file.read())
                    metadata = wotmods_metadata[meta[0].text] = {
                        'id'          : meta[0].text,
                        'name'        : meta[2].text,
                        'description' : meta[3].text,
                        'version'     : meta[1].text             
                    }
                    metadata['wot_version_min'] = raw_input('WoT version for %s is not defined. Please type it: '%(name))

        print '%s:\n\tID: %s\n\tName: %s\n\tDescription: %s\n\tVersion: %s\n\tWoT version: %s'%(
            name,
            metadata['id'],
            metadata['name'],
            metadata['description'],
            metadata['version'],
            metadata['wot_version_min']
        )
        if 'dependencies' in metadata:
            print '\tDependencies: %s'%(metadata['dependencies'])
        if 'wot_version_exactmatch' in metadata:
            print '\tExactly match: %s'%(metadata['wot_version_exactmatch'])
        
        zip_dir  = 'mods/%s/com.modxvm.xfw/'%(metadata['wot_version_min'])
        zip_path = 'archives/%s.zip'%(metadata['id'])
        if exists(zip_path):
            remove(zip_path)
        
        with ZipFile(zip_path, 'w', ZIP_DEFLATED) as out_zip:
            out_zip.write(wotmod_path, zip_dir + wotmod_name)

#archive.extract(path, 'unpacked/%s/mods/%s/com.modxvm.xfw/')

rmtree('temp')
remove(filename)

config = {}
with open('config.json', 'r') as cfg:
    config = json.load(cfg)

for mod_name in wotmods_metadata:
    if mod_name not in config: continue
    
    metadata = wotmods_metadata[mod_name]
    if 'dependencies' not in metadata:
        print 'Dependencies not found in %s. Please set it manually'%(metadata['name'])
        config[mod_name]['dependencies'] = []
    else:
        config[mod_name]['dependencies'] = list(metadata['dependencies'])

with open('config.json', 'w') as cfg:
    json.dump(config, cfg, sort_keys=True, indent=4)
    
