import codecs
import os
import json
import requests
import sys

from zipfile import ZipFile, ZIP_DEFLATED
from os import chdir, rename, remove, listdir, mkdir, makedirs, rmdir
from os.path import basename, exists, isfile, isdir, join
from xml.etree import ElementTree as ET

from common   import *
from entities import *

sys.path.insert(0, 'libs/')

import JSONxLoader

MOD_NAME = 'xvm'

filename = get_archive(MOD_NAME)

wd = 'temp/'

if exists(wd):
    hard_rmtree(wd)
mkdir(wd)

with ZipFile(filename) as archive:
    archive.extractall(wd)

packages_metadata = {}

if exists(wd + XFW_PACKAGES_DIR):
    for package_name in listdir(wd + XFW_PACKAGES_DIR):
        package = g_EntityFactory.create(
            Package,
            name=package_name,
            wd=wd
        )
        metadata = package.meta.copy()
        
        if not metadata:
            print package_name, 'Metainfo was not found'
            continue
        
        packages_metadata[metadata['id']] = metadata

        create_deploy(wd, '', metadata['id'], XFW_PACKAGES_DIR + package_name, isRaw=True)

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

                create_deploy(wd, '', configs[cfg_name]['id'], configs[cfg_name]['wd'], False, isRaw=True)

    for cfg_name in configs:
        if exists(wd + configs[cfg_name]['wd']):
            hard_rmtree(wd + configs[cfg_name]['wd'])
    
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
        
        create_deploy(wd, '', xvm_configs['id'], xvm_configs['wd'], isRaw=True)

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

#some packages need main XVM module version
xvm_metadata = packages_metadata.get('com.modxvm.xvm')
if xvm_metadata is not None:
    version = xvm_metadata['version']
    wot_version = xvm_metadata['wot_version_min']
    
    # Processing xfw
    xfw_wd = 'mods/%s/com.modxvm.xfw/' % wot_version
    xfw_wd_path = myjoin(wd, xfw_wd)
    print 'xfw_wd_path:', xfw_wd_path
    if exists(xfw_wd_path):
        for wotmod_name in listdir(xfw_wd_path):
            print 'wotmod_name', wotmod_name
            wotmod_path = myjoin(xfw_wd_path, wotmod_name)
            if not isfile(wotmod_path):
                print 'not isfile(wotmod_path=%s)' % wotmod_path
                continue

            name = None
                    
            for package_id, package_name in xfw_packages.iteritems():
                if wotmod_name.startswith(package_id):
                    name = package_name
                    break

            if name is None:
                print 'Cannot find wotmod', wotmod_name
                continue

            wotmod = g_EntityFactory.create(WotMod, wotmod_path)
            
            metadata = wotmod.entities['packages'][name].meta.copy()
            if not metadata:
                metadata = wotmod.meta

            metadata['wot_version_min'] = wot_version

            wotmod_id = metadata['id']

            packages_metadata[wotmod_id] = metadata

            out = g_EntityFactory.create(RawArchive, wotmod_id, True)
            out.io.write(
                wotmod_path,
                myjoin(xfw_wd, wotmod_name)
            )
            out.closeIO()

            wotmod.fini()
    
    #processing lobby
    xvm_lobby = {
        'id'      : 'com.modxvm.xvm.lobby',
        'wd'      : XFW_PACKAGES_DIR + 'xvm_lobby/',
    }
    if exists(wd + xvm_lobby['wd']) and xvm_lobby['id'] not in packages_metadata:
        packages_metadata[xvm_lobby['id']] = {
            'id'           : xvm_lobby['id'],
            'name'         : 'XVM Lobby',
            'description'  : 'XVM Lobby module',
            'version'      : version,
            'dependencies' : []
        }
        
        print 'Generated xvm_lobby metadata'

        create_deploy(wd, '', xvm_lobby['id'], xvm_lobby['wd'], isRaw=True)
    
    #processing resources
    resources_wd = 'res_mods/mods/shared_resources/'
    if exists(wd + resources_wd):
        metadata = {
            'id'           : 'com.modxvm.xvm.shared_resources',
            'name'         : 'XVM Shared Resources',
            'description'  : 'XVM Shared Resources Package',
            'version'      : version,
            'dependencies' : []
        }
        packages_metadata[metadata['id']] = metadata
        print 'Generated shared resources metadata'

        create_deploy(wd, '', metadata['id'], resources_wd, isRaw=True)
    
    #building final XVM package
    xvm_id = 'XVM'
    
    dependencies = set(packages_metadata.keys())
    print 'XVM packages:', dependencies
    new_deps = check_depends(wd, xvm_id)
    print 'found deps:', new_deps
    dependencies.update(new_deps)
    
    packages_metadata[xvm_id] = {
        'id'           : xvm_id,
        'name'         : 'XVM',
        'description'  : 'XVM - eXtended Visualization Mod',
        'version'      : version,
        'dependencies' : list(dependencies)
    }
    print 'Generated XVM metadata'
    
    soft_rmtree(wd, False)
    
    for item in listdir(wd):
        path = join(wd, item)
        if isdir(path):
            hard_rmtree(path)
    
    create_deploy(wd, '', xvm_id, './', False, isRaw=True)
else:
    print 'Main XVM module metadata was not found'
    print 'lobby and shared resources won\'t be processed'

soft_rmtree(wd, False)
hard_rmtree(wd)
remove(filename)

add_mods(packages_metadata)

raw_input('------ DONE ------')
