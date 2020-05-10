from os import mkdir, makedirs
from os.path import exists
from shutil import copy2

from common import *

packages_metadata = {}

mods = {
    'com.pavel3333.mods.Doshik_E-100' : {
        'dir'  : 'com.pavel3333.mods/',
        'type' : 'wotmod'
    }
}

game_version = raw_input('Please enter the game version: ')

wd = 'temp/'

if exists(wd):
    hard_rmtree(wd)
mkdir(wd)

for mod_id, mod in mods.iteritems():
    print mod_id

    if mod['type'] == 'archive':
        packages_metadata[mod_id] = {
            'id'              : mod_id,
            'name'            : mod['name'],
            'description'     : mod['desc'],
            'version'         : mod['ver'],
            'wot_version_min' : game_version
        }
    elif mod['type'] == 'wotmod':
        wotmod_path    = WOTMODS_WD + mod_id + '.wotmod'
        wotmod_dst_dir = wd + '/mods/%s/'%(game_version) + mod['dir']

        metadata = {}

        with Wotmod(wotmod_path) as wotmod:
            packages_metadata[mod_id] = metadata = wotmod.getMeta(identifier=mod_id, ver=game_version)

        makedirs(wotmod_dst_dir)

        copy2(wotmod_path, wotmod_dst_dir + mod_id + '.wotmod')

        create_deploy(wd, '', mod_id, './', False, True)
        hard_rmtree(wd, False)
    else:
        print '\tUnknown type: %s'%(mod['type'])

hard_rmtree(wd)

add_mods(packages_metadata)
