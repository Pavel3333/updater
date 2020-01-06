import codecs
import json
import requests

from urllib import urlretrieve
from zipfile import ZipFile, ZIP_DEFLATED
from os import chdir, rename, remove, listdir, mkdir, makedirs
from os.path import basename, exists, isfile
from xml.etree import ElementTree as ET

from common import my_rmtree, move_files, create_archive

wd = 'temp/'

if exists(wd):
    my_rmtree(wd)
mkdir(wd)

packages_metadata = {}

zip_fmt = 'archives/%s.zip'
raw_zip_fmt = 'raw_' + zip_fmt

mods_wd     = 'mods/'
packages_wd = 'res_mods/mods/xfw_packages/'
wotmods_wd  = 'wotmod/'

mods = [
    {
        'id'   : 'com.pavel3333.mods.PositionsMod',
        'dir'  : 'PositionsMod/',
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
    }
]

for mod in mods:
    raw_mod_zip_path = raw_zip_fmt%(mod['id'])
    
    if not exists(raw_mod_zip_path):
        print raw_mod_zip_path, 'not exists'
        continue
    
    with ZipFile(raw_mod_zip_path) as archive:
        archive.extractall(wd)
    
    if not exists(wd + packages_wd + mod['dir']):
        print mod['dir'], 'not exists'
    
    metadata = {}
    
    metainfo_path = wd + packages_wd + mod['dir'] + 'xfw_package.json'
    with codecs.open(metainfo_path, 'r', 'utf-8') as meta:
        metadata = json.load(meta)
    
    packages_metadata[mod['id']] = {
        'id'           : mod['id'],
        'name'         : metadata['name'],
        'description'  : metadata['description'],
        
        'version'      : metadata['version'],
        'dependencies' : metadata['dependencies'],
        
        'wot_version_min'        : metadata['wot_version_min'],
        'wot_version_exactmatch' : metadata['wot_version_exactmatch']
    }
    
    print '%s:\n\tName: %s\n\tDescription: %s\n\tVersion: %s\n\tWoT version: %s'%(
        mod['id'],
        metadata['name'],
        metadata['description'],
        metadata['version'],
        metadata['wot_version_min']
    )
    if 'dependencies' in metadata:
        print '\tDependencies: %s'%(metadata['dependencies'])
    if 'wot_version_exactmatch' in metadata:
        print '\tExactly match: %s'%(metadata['wot_version_exactmatch'])
    
    if exists(wd + wotmods_wd):
        curr_mods_wd = wd + mods_wd + metadata['wot_version_min'] + '/'
        move_files(wd + wotmods_wd, curr_mods_wd)

    zip_path = zip_fmt%(mod['id'])
    create_archive(wd, zip_path, './', False)

    for item in listdir(wd):
        path = wd + item
        if isfile(path):
            remove(path)
        else:
            my_rmtree(path)

for mod in mods:
    if mod['id'] not in packages_metadata:
        print mod['id'], 'metadata not found'
        continue
    
    for dep_id in mod['deps']:
        dep_path = mod['deps'][dep_id]
        
        raw_dep_zip_path = raw_zip_fmt%(dep_id)
        if not exists(raw_dep_zip_path):
            print raw_dep_zip_path, 'not exists'
        
        with ZipFile(raw_dep_zip_path) as archive:
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
        print 'found wotmod', wotmod_name
        
        metadata = {}
        
        with ZipFile(wd + dep_dir + wotmod_name) as wotmod:
            with wotmod.open('meta.xml') as meta_file:
                meta = ET.fromstring(meta_file.read())
                metadata = packages_metadata[dep_id] = {
                    'id'              : dep_id,
                    'name'            : meta[2].text,
                    'description'     : meta[3].text,
                    'version'         : meta[1].text,
                    'dependencies'    : [],
                    'wot_version_min' : packages_metadata[mod['id']]['wot_version_min']
                }
        
        print '%s:\n\tName: %s\n\tDescription: %s\n\tVersion: %s\n\tWoT version: %s'%(
            mod['id'],
            metadata['name'],
            metadata['description'],
            metadata['version'],
            metadata['wot_version_min']
        )
        if 'dependencies' in metadata:
            print '\tDependencies: %s'%(metadata['dependencies'])
        if 'wot_version_exactmatch' in metadata:
            print '\tExactly match: %s'%(metadata['wot_version_exactmatch'])

        if dep_path.get('markVer', False):
            rename(wd + dep_dir + wotmod_name, wd + dep_dir + wotmod_name.replace('.wotmod', '_%s_v%s.wotmod'%(metadata['wot_version_min'], metadata['version'])))
        
        curr_mods_wd = wd + mods_wd + metadata['wot_version_min'] + '/'
        move_files(wd + wotmods_wd, curr_mods_wd)
                
        zip_path = zip_fmt%(dep_id)
        create_archive(wd, zip_path, './', False)
        
        for item in listdir(wd):
            path = wd + item
            if isfile(path):
                remove(path)
            else:
                my_rmtree(path)

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
