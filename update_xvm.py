import codecs
import os
import json
import requests
import sys

from urllib import urlretrieve
from zipfile import ZipFile, ZIP_DEFLATED
from os import chdir, rename, remove, listdir, mkdir, makedirs
from os.path import basename, exists, isfile, join
from xml.etree import ElementTree as ET

from common import my_rmtree, check_depends, zip_folder, create_archive

sys.path.insert(0, 'libs/')

import JSONxLoader

filename = 'xvm.zip'
urlretrieve('https://nightly.modxvm.com/download/master/xvm_latest.zip', filename)
print filename, 'successfully downloaded'

wd = 'temp/'

if exists(wd):
    my_rmtree(wd)
mkdir(wd)

with ZipFile(filename) as archive:
    archive.extractall(wd)

zip_path_fmt = 'archives/%s.zip'

packages_metadata = {}
packages_wd = 'res_mods/mods/xfw_packages/'

if exists(wd + packages_wd):
    for package_name in listdir(wd + packages_wd):
        metadata = {}
        
        package_path = wd + packages_wd + package_name + '/xfw_package.json'
        if not exists(package_path):
            print '%s: metainfo was not found'%(package_name)
            continue
        
        with codecs.open(package_path, 'r', 'utf-8') as package:
            metadata = json.load(package)
            packages_metadata[metadata['id']] = metadata

        print '%s:\n\tID: %s\n\tName: %s\n\tDescription: %s\n\tVersion: %s\n\tWoT version: %s'%(
            package_name,
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

        create_archive(wd, zip_path_fmt%(metadata['id']), packages_wd + package_name)

#processing configs
xvm_configs = {
    'id'      : 'com.modxvm.xvm.configs',
    'wd'      : 'res_mods/configs/xvm/',
}
if exists(wd + xvm_configs['wd']):
    configs = {
        'default' : {
            'id'          : xvm_configs['id'] + '.default',
            'name'        : 'XVM Default Config',
            'description' : 'XVM Default Config',
            'wd'          : xvm_configs['wd'] + 'default/',
            'main_cfg'    : '@xvm.xc',
            'data'        : {}
        },
        'sirmax' : {
            'id'       : xvm_configs['id'] + '.sirmax',
            'wd'       : xvm_configs['wd'] + 'sirmax/',
            'name'        : 'XVM Sirmax Config',
            'description' : 'XVM Sirmax Config',
            'main_cfg' : 'sirmax.xc',
            'data'     : {}
        }
    }
    
    for cfg_name in configs:
        cfg_path = wd + configs[cfg_name]['wd'] + configs[cfg_name]['main_cfg']
        if exists(cfg_path):
            data = configs[cfg_name]['data'] = JSONxLoader.load(cfg_path)
            if data is None:
                print cfg_name, 'config loading error'
    
            else:
                excludeChecksum = []
                for cfg_file in listdir(wd + configs[cfg_name]['wd']):
                    if isfile(wd + configs[cfg_name]['wd'] + cfg_file):
                        excludeChecksum.append(configs[cfg_name]['wd'] + cfg_file)
                              
                packages_metadata[configs[cfg_name]['id']] = {
                    'id'              : configs[cfg_name]['id'],
                    'name'            : configs[cfg_name]['name'],
                    'description'     : configs[cfg_name]['description'],
                    'version'         : data['configVersion'],
                    'dependencies'    : [],
                    'excludeChecksum' : excludeChecksum
                }
                print 'Generated %s config metadata'%(cfg_name)

                create_archive(wd, zip_path_fmt%(configs[cfg_name]['id']), configs[cfg_name]['wd'], False)

    for cfg_name in configs:
        if exists(wd + configs[cfg_name]['wd']):
            my_rmtree(wd + configs[cfg_name]['wd'])
    
    if configs['default']['data'].get('configVersion') is None:
        print 'Config version was not found'
    else:
        packages_metadata[xvm_configs['id']] = {
            'id'           : xvm_configs['id'],
            'name'         : 'XVM Configs',
            'description'  : 'XVM Configs Package',
            'version'      : configs['default']['data']['configVersion'],
            'dependencies' : [
                configs['default']['id'],
                configs['sirmax']['id']
            ]
        }
        print 'Generated configs metadata'
        
        create_archive(wd, zip_path_fmt%(xvm_configs['id']), xvm_configs['wd'])

config = {}
with codecs.open('config.json', 'r', 'utf-8') as cfg:
    config = json.load(cfg)

#some packages need main XVM module version
if 'com.modxvm.xvm' in packages_metadata:
    #processing lobby
    xvm_lobby = {
        'id'      : 'com.modxvm.xvm.lobby',
        'wd'      : packages_wd + 'xvm_lobby/',
    }
    if exists(wd + xvm_lobby['wd']) and xvm_lobby['id'] not in packages_metadata:
        packages_metadata[xvm_lobby['id']] = {
            'id'           : xvm_lobby['id'],
            'name'         : 'XVM Lobby',
            'description'  : 'XVM Lobby module',
            'version'      : packages_metadata['com.modxvm.xvm']['version'],
            'dependencies' : []
        }
        print 'Generated xvm_lobby metadata'

        create_archive(wd, zip_path_fmt%(xvm_lobby['id']), xvm_lobby['wd'])

    #processing resources
    resources_wd = 'res_mods/mods/shared_resources/'
    if exists(wd + resources_wd):
        metadata = {
            'id'           : 'com.modxvm.xvm.shared_resources',
            'name'         : 'XVM Shared Resources',
            'description'  : 'XVM Shared Resources Package',
            'version'      : packages_metadata['com.modxvm.xvm']['version'],
            'dependencies' : []
        }
        packages_metadata[metadata['id']] = metadata
        print 'Generated shared resources metadata'

        create_archive(wd, zip_path_fmt%(metadata['id']), resources_wd)
    
    #building final XVM package
    xvm_id = 'XVM'
    
    xfw_packages = set(filter(lambda name: 'com.modxvm.xfw' in name, config.keys()))
    
    dependencies = set(packages_metadata.keys())
    dependencies.update(xfw_packages)
    dependencies.update(check_depends(wd))

    version = packages_metadata['com.modxvm.xvm']['version']
    
    packages_metadata[xvm_id] = {
        'id'           : xvm_id,
        'name'         : 'XVM',
        'description'  : 'XVM - eXtended Visualization Mod',
        'version'      : version,
        'dependencies' : list(dependencies)
    }
    print 'Generated XVM metadata'

    zip_path = zip_path_fmt%(xvm_id)
    if exists(zip_path):
        remove(zip_path)
    
    with ZipFile(zip_path, 'w', ZIP_DEFLATED) as out_zip:
        chdir(wd)
        for item in listdir('./'):
            if isfile(item):
                out_zip.write(item)
        chdir('../')
else:
    print 'Main XVM module metadata was not found'
    print 'lobby and shared resources won\'t be processed'

my_rmtree(wd)
remove(filename)

for mod_name in packages_metadata:
    if mod_name not in config:
        print mod_name, 'not found in config. Creating a new one...'
        config[mod_name] = {}
    
    if 'deploy' not in config[mod_name]:
        config[mod_name]['deploy'] = False

    metadata = packages_metadata[mod_name]
    
    dependencies = set()
    if 'dependencies' not in metadata:
        print 'Dependencies not found in %s. Please set it manually'%(metadata['name'])
        config[mod_name]['dependencies'] = []
    else:
        dependencies.update(set(metadata['dependencies']))
    
    if 'dependencies_optional' in metadata:
        dependencies.update(set(metadata['dependencies_optional']))
    
    config[mod_name]['dependencies'] = list(dependencies)

    if 'excludeChecksum' in metadata:
        config[mod_name]['excludeChecksum'] = metadata['excludeChecksum']

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
            'ID'           : metadata['id'],
            'name_ru'      : config[mod_name]['name']['RU'],
            'name_en'      : config[mod_name]['name']['EN'],
            'name_cn'      : config[mod_name]['name']['CN'],
            'desc_ru'      : config[mod_name]['description']['RU'],
            'desc_en'      : config[mod_name]['description']['EN'],
            'desc_cn'      : config[mod_name]['description']['CN'],
            'version'      : metadata['version'],
            'deploy'       : 1 if config[mod_name]['deploy'] else 0
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
