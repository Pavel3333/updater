import codecs
import json

from urllib import urlretrieve
from zipfile import ZipFile, ZIP_DEFLATED
from os import chdir, rename, remove, listdir, mkdir, makedirs
from os.path import basename, exists, isfile
from xml.etree import ElementTree as ET

from common import *

wd = 'temp/'

if exists(wd):
    hard_rmtree(wd)
mkdir(wd)

packages_metadata = {}

mods_wd     = 'mods/'
wotmods_wd  = 'wotmod/'

mods = [
    {
        'id'     : 'com.pavel3333.Autoupdater',
        'dir'    : 'Autoupdater_Main',
        'public' : True,
        'deps'   : {}
    },
    {
        'id'     : 'com.pavel3333.Autoupdater.GUI',
        'dir'    : 'Autoupdater_GUI',
        'public' : True,
        'deps'   : {}
    },
    {
        'id'     : 'com.pavel3333.mods.PositionsMod',
        'dir'    : 'PositionsMod',
        'public' : True,
        'deps'   : {
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
        'id'     : 'com.pavel3333.mods.PositionsMod.TestersEdition',
        'dir'    : 'PositionsMod_TEST',
        'public' : False,
        'deps'   : {
            'com.pavel3333.mods.PositionsMod.models' : {
                'dir'        : 'com.pavel3333.mods/',
                'name_start' : 'com.pavel3333.mods.PositionsMod.models',
                'markVer'    : True
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
        'id'     : 'com.pavel3333.mods.Xcavator',
        'public' : True,
        'deps'   : {}
    },
    {
        'id'     : 'com.pavel3333.mods.Dora',
        'public' : True,
        'deps'   : {}
    },
    {
        'id'     : 'com.pavel3333.mods.Doshik_E-100',
        'public' : True,
        'deps'   : {}
    },
    {
        'id'     : 'com.pavel3333.mods.GRILLE_AUF_E-100',
        'public' : True,
        'deps'   : {}
    },
    {
        'id'     : 'com.pavel3333.mods.CollisionChecker',
        'dir'    : 'CollisionChecker',
        'public' : True,
        'deps'   : {}
    },
    {
        'id'     : 'com.pavel3333.mods.CollisionChecker.1.0.1.0',
        'public' : False,
        'deps'   : {}
    },
    {
        'id'     : 'com.pavel3333.mods.CollisionChecker.TesterEdition',
        'public' : False,
        'deps'   : {}
    }
]

for mod in mods:
    mod_name = mod['id']
    metadata = None
    
    with RawArchive('', mod_name, False) as archive:
        if 'dir' in mod:
            metadata = archive.getMeta(mod['dir'], mod_name)
            archive.extractall(wd)
        else:
            metadata = archive.getMeta(None, mod_name)
            archive.extractall(wd, filter(lambda name: name != 'meta.json', archive.namelist()))
    
    if metadata is None:
        print mod_name, 'metadata not found'
        continue

    packages_metadata[mod_name] = metadata
    
    if exists(wd + wotmods_wd):
        curr_mods_wd = wd + mods_wd + metadata['wot_version_min'] + '/'
        move_files(wd + wotmods_wd, curr_mods_wd)
    
    create_deploy(wd, '', mod_name, './', del_folder=False, isRaw=True)
    hard_rmtree(wd, False)

for mod in mods:
    mod_name = mod['id']
    if mod_name not in packages_metadata:
        print mod_name, 'not found'
        continue

    if not mod['public']:
        print mod_name, 'is not public'
        continue
    
    for dep_id in mod['deps']:
        dep_path = mod['deps'][dep_id]
        
        with RawArchive('', dep_id, False) as archive:
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
            packages_metadata[dep_id] = metadata = wotmod.getMeta(identifier=dep_id, ver=packages_metadata[mod_name]['wot_version_min'])
        
        if dep_id not in packages_metadata[mod_name]['dependencies']:
            packages_metadata[mod_name]['dependencies'].append(dep_id)
        
        if dep_path.get('markVer', False):
            rename(wd + dep_dir + wotmod_name, wd + dep_dir + wotmod_name.replace('.wotmod', '_%s_v%s.wotmod'%(metadata['wot_version_min'], metadata['version'])))
        
        curr_mods_wd = wd + mods_wd + metadata['wot_version_min'] + '/'
        move_files(wd + wotmods_wd, curr_mods_wd)
        
        create_deploy(wd, mod_name, dep_id, './', False, True)
        
        hard_rmtree(wd, False)

soft_rmtree(wd, False)
hard_rmtree(wd)

add_mods(packages_metadata)
