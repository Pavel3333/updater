import codecs
import json
import requests

from urllib import urlretrieve
from zipfile import ZipFile, ZIP_DEFLATED
from os import chdir, rename, remove, listdir, mkdir, makedirs
from os.path import basename, exists, isfile
from xml.etree import ElementTree as ET

from common import *

wd = 'temp/'

if exists(wd):
    my_rmtree(wd)
mkdir(wd)

packages_metadata = {}

mods_wd     = 'mods/'
wotmods_wd  = 'wotmod/'

mods = [
    {
        'id'   : 'com.pavel3333.mods.PositionsMod',
        'dir'  : 'PositionsMod',
        'deps' : {
            'com.pavel3333.mods.PositionsMod.models' : {
                'dir'        : 'com.pavel3333.mods/',
                'name_start' : 'com.pavel3333.mods.PositionsMod.models',
                'markVer'    : True
            },
            'com.PYmods.PYmodsCore' : {
                'dir'        : 'PYmods/',
                'name_start' : 'PYmodsCore'
            },
            'com.spoter.mods_gui' : {
                'dir'        : '',
                'name_start' : 'mod_mods_gui'
            },
            'com.gambiter.guiflash' : {
                'dir'        : '',
                'name_start' : 'gambiter.guiflash'
            }
        }
    },
    {
        'id'   : 'com.pavel3333.mods.CollisionChecker',
        'dir'  : 'CollisionChecker',
        'deps' : {}
    },
    {
        'id'   : 'com.pavel3333.mods.CollisionChecker.alpha',
        'dir'  : 'CollisionChecker',
        'deps' : {}
    }
]

for mod in mods:
    metadata = None
    
    with RawArchive(mod['id'], False) as archive:
        metadata = archive.getXFWPackageMeta(mod['dir'], mod['id'])
        archive.extractall(wd)
       
    if metadata is None:
        print mod['id'], 'metadata not found'
        continue

    packages_metadata[mod['id']] = metadata
    
    if exists(wd + wotmods_wd):
        curr_mods_wd = wd + mods_wd + metadata['wot_version_min'] + '/'
        move_files(wd + wotmods_wd, curr_mods_wd)
    
    create_deploy(wd, mod['id'], './', False, True)
    my_rmtree(wd, False)

for mod in mods:
    if mod['id'] not in packages_metadata:
        print mod['id'], 'not found'
        continue
    
    for dep_id in mod['deps']:
        dep_path = mod['deps'][dep_id]
        
        with RawArchive(dep_id, False) as archive:
            archive.extractall(wd)

        dep_dir = wotmods_wd + dep_path['dir']
        
        wotmod_list = filter(
            lambda name: name.startswith(dep_path['name_start']) and name.endswith('.wotmod'),
            listdir(wd + dep_dir)
        )
        if not wotmod_list:
            print dep_id, 'wotmod was not found'
            continue
        
        wotmod_name = max(wotmod_list)
        
        metadata = {}
        
        with Wotmod(wd + dep_dir + wotmod_name) as wotmod:
            packages_metadata[dep_id] = metadata = wotmod.getMeta(identifier=dep_id, ver=packages_metadata[mod['id']]['wot_version_min'])
        
        if dep_path.get('markVer', False):
            rename(wd + dep_dir + wotmod_name, wd + dep_dir + wotmod_name.replace('.wotmod', '_%s_v%s.wotmod'%(metadata['wot_version_min'], metadata['version'])))
        
        curr_mods_wd = wd + mods_wd + metadata['wot_version_min'] + '/'
        move_files(wd + wotmods_wd, curr_mods_wd)
        
        create_deploy(wd, dep_id, './', False, True)
        
        my_rmtree(wd, False)

my_rmtree(wd)

config = {}
with codecs.open('config.json', 'r', 'utf-8') as cfg:
    config = json.load(cfg)

for mod['id'] in packages_metadata:
    if mod['id'] not in config:
        print mod['id'], 'not found in config. Creating a new one...'
        config[mod['id']] = {}

    if 'deploy' not in config[mod['id']]:
        config[mod['id']]['deploy'] = False
    
    metadata = packages_metadata[mod['id']]
    
    if 'dependencies' not in config[mod['id']]:
        print 'Dependencies not found in %s. Please set it manually'%(mod['id'])
        dependencies = set(metadata['dependencies'])
    
        if 'dependencies_optional' in metadata:
            dependencies.update(set(metadata['dependencies_optional']))
    
        config[mod['id']]['dependencies'] = list(dependencies)

    if 'name' not in config[mod['id']]:
        config[mod['id']]['name'] = {
            'RU' : metadata['name'],
            'EN' : metadata['name'],
            'CN' : metadata['name']
        }

    if 'description' not in config[mod['id']]:
        config[mod['id']]['description'] = {
            'RU' : metadata['description'],
            'EN' : metadata['description'],
            'CN' : metadata['description']
        }
    
    req = requests.post(
        'http://api.pavel3333.ru/add_mod.php',
        data = {
            'ID'      : mod['id'],
            'name_ru' : config[mod['id']]['name']['RU'],
            'name_en' : config[mod['id']]['name']['EN'],
            'name_cn' : config[mod['id']]['name']['CN'],
            'desc_ru' : config[mod['id']]['description']['RU'],
            'desc_en' : config[mod['id']]['description']['EN'],
            'desc_cn' : config[mod['id']]['description']['CN'],
            'version' : metadata['version'],
            'deploy'  : config[mod['id']]['deploy']
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
