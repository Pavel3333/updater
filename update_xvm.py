import codecs
import os
import json
import requests
import sys

from urllib import urlretrieve
from zipfile import ZipFile, ZIP_DEFLATED
from os import chdir, rename, remove, listdir, mkdir, makedirs, rmdir
from os.path import basename, exists, isfile, join
from xml.etree import ElementTree as ET

from common import *

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

packages_metadata = {}
packages_wd = 'res_mods/mods/xfw_packages/'

if exists(wd + packages_wd):
    for package_name in listdir(wd + packages_wd):
        metadata = Package(wd, package_name).getXFWPackageMeta()
        
        if not metadata:
            print package_name, 'metainfo was not found'
            continue
        
        packages_metadata[metadata['id']] = metadata

        create_deploy(wd, metadata['id'], packages_wd + package_name)

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

                create_deploy(wd, configs[cfg_name]['id'], configs[cfg_name]['wd'], False)

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
        
        create_deploy(wd, xvm_configs['id'], xvm_configs['wd'])

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

        create_deploy(wd, xvm_lobby['id'], xvm_lobby['wd'])

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

        create_deploy(wd, metadata['id'], resources_wd)
    
    #building final XVM package
    xvm_id = 'XVM'
    
    dependencies = set(packages_metadata.keys())
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
    
    for item in listdir(wd):
        if not isfile(wd + item):
            my_rmtree(wd + item)
    
    create_deploy(wd, xvm_id, './', False)
else:
    print 'Main XVM module metadata was not found'
    print 'lobby and shared resources won\'t be processed'

my_rmtree(wd)
remove(filename)

add_mods(packages_metadata)
