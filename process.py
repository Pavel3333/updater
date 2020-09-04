import urllib
import os
import sys
import requests
import json
import zipfile

from hashlib import md5

from common   import *
from entities import *

config    = {}

archives_wd        = 'archives/'
unpacked_wd        = 'unpacked/'
unpacked_deploy_wd = 'unpacked_deploy/'
deploy_wd          = 'deploy/'

class ModStructure:
    def __init__(self, exclude_paths, path):
        self.exclude_paths = exclude_paths
        self.ID     = 0
        self.paths  = {}
        self.names  = {}
        self.hashes = {}
        self.tree   = {}
        
        self.settings = {}

        for child in os.listdir(path):
            self.move(path, child, self.tree)

    def setSettings(self, path):
        if path:
            with open(path, 'r') as fil:
                self.settings = json.loads(fil.read().decode('utf-8-sig'))

    def move(self, path, child, curr_dic):
        subpath = path + child
        
        self.ID += 1
        
        if os.path.isfile(subpath):
            #print 'file', subpath
            curr_dic[self.ID] = 0
            
            self.paths[self.ID]  = subpath
            self.names[self.ID]  = child
            if any(mask in path or mask in subpath for mask in self.exclude_paths):
                print 'path %s excluded'%(subpath)
            else:
                self.hashes[self.ID] = md5(open(subpath, 'rb').read()).hexdigest()
        else:
            #print 'dir', subpath
            subpath += '/'
            subdic = curr_dic[self.ID] = {}
            self.names[self.ID] = child
            
            for subchild in os.listdir(subpath):
                self.move(subpath, subchild, subdic)

def get_dependency(main_mod_name, mod_name=None):
    if main_mod_name not in config:
        print main_mod_name, 'not in config'
        return
    
    if mod_name is None:
        mod_name = main_mod_name
    
    if mod_name not in config:
        print mod_name, 'not in config'
        return
    if 'dependencies' not in config[mod_name]:
        print 'dependencies not in', mod_name, 'config'
        return

    dependencies = set()
    
    dependency_list = config[mod_name]['dependencies']
    for dependency in dependency_list:
        if dependency == main_mod_name: #recursion protection
            continue
        
        dependencies.add(int(mods_list_by_name[dependency]['ID']))
        if config[main_mod_name]['deploy']:
            dependencies.update(get_dependency(main_mod_name, dependency))

    return dependencies

def send_mod(mod_name, isPublic, main_mod_name=None):
    isDependency = main_mod_name is not None
    
    if isPublic and mod_name not in mods_list_by_name:
        raise StandardError('Mod %s is not exists on the server!'%(mod_name))

    # cleaning
    hard_rmtree(unpacked_wd, False)
    hard_rmtree(unpacked_deploy_wd, False)
    
    dependencies = get_dependency(mod_name)
    #print '\tdependencies:', dependencies
    
    if isDependency:
        if main_mod_name is None:
            raise StandardError('This dependency have no main mod name')
        print 'mod: %s, dependency: %s'%(main_mod_name, mod_name)
    else:
        print 'mod:', mod_name

        for dependencyID in dependencies:
            dependency_name = mods_list_by_ID[str(dependencyID)]['Name']
            if not send_mod(dependency_name, isPublic, mod_name):
                return False
    
    exclude_paths = []
    
    tree     = {}
    paths    = {}
    names    = {}
    hashes   = {}
    settings = {}
    
    extract_wd = myjoin(unpacked_wd, mod_name)
    
    # Unpack the mod archive
    archive = g_EntityFactory.create(Archive, mod_name, False, source_dir=main_mod_name)
    archive.io.extractall(extract_wd)
    archive.fini()
    
    # Make unpacked mod dir if not exists
    if not os.path.exists(extract_wd):
        os.mkdir(extract_wd)
    
    if not isDependency:
        extract_wd = myjoin(unpacked_deploy_wd, mod_name)
        
        # Unpack all dependencies into deploy mod directory
        for dependencyID in dependencies:
            archive = g_EntityFactory.create(
                Archive,
                mods_list_by_ID[str(dependencyID)]['Name'],
                False,
                source_dir=mod_name
            )
            archive.io.extractall(extract_wd)
            archive.fini()
        
        # Unpack mod into deploy mod directory
        archive = g_EntityFactory.create(Archive, mod_name, False)
        archive.io.extractall(extract_wd)
        archive.fini()
        
        # Make unpacked deploy mod dir if not exists
        if not os.path.exists(extract_wd):
            os.mkdir(extract_wd)
        
        # Make deploy archive
        archive = g_EntityFactory.create(Archive, mod_name, True)
        os.chdir(extract_wd + '/')
        zip_folder('./', archive.io)
        os.chdir('../../')
        archive.fini()
    
    settings_path = mods_list_by_name.get(mod_name, {}).get('SettingsPath', '') # Exclude settings path
    if settings_path:
        exclude_paths.append(settings_path)

    if str(mod_name) in config and 'excludeChecksum' in config[mod_name]: # Exclude checksum
        exclude_paths.extend(config[mod_name]['excludeChecksum'])
    
    os.chdir(unpacked_wd + mod_name + '/')

    structure = ModStructure(exclude_paths, './') # Get tree, paths, names and hashes
    structure.setSettings(settings_path)   # Set mod settings file
    
    os.chdir('../../')

    if not isPublic: return True

    path_autoupd = archives_wd + '%s.zip'%(mod_name)
    if not os.path.exists(path_autoupd):
        if not main_mod_name:
            raise StandardError('Unable to find mod archive %s'%(mod_name))
        path_autoupd = archives_wd + '%s/%s.zip'%(main_mod_name, mod_name)
        if not os.path.exists(path_autoupd):
            raise StandardError('Unable to find dependency archive %s of mod %s'%(mod_name, main_mod_name))

    files_dict = {
        'mod_autoupd' : open(path_autoupd, 'rb')
    }

    if not isDependency:
        files_dict['mod_deploy'] = open(deploy_wd + '%s.zip'%(mod_name), 'rb')
    
    req = requests.post(
        'http://api.pavel3333.ru/update_mods.php',
        data = {
            'password'     : PASSWORD,
            
            'ID'           : mods_list_by_name[mod_name]['ID'],
            'version'      : config[mod_name]['version'],
            'tree'         : json.dumps(structure.tree,     sort_keys=True),
            'paths'        : json.dumps(structure.paths,    sort_keys=True),
            'names'        : json.dumps(structure.names,    sort_keys=True),
            'hashes'       : json.dumps(structure.hashes,   sort_keys=True),
            'settings'     : json.dumps(structure.settings, sort_keys=True),
            'dependencies' : json.dumps(list(dependencies), sort_keys=True)
        },
        files = files_dict
    )
    
    try:
        req_decoded = json.loads(req.text)
    except Exception:
        print '\tinvalid response:', req.text
        return False
    
    if req_decoded['status'] == 'ok':
        print '\tsuccessed'
        print '\tlog:',  req_decoded['log']
        
        if not req_decoded['data']:
          print 'Build data was not changed'
        else:
            for key, value in req_decoded['data'].iteritems():
                print '%s: %s'%(key, value)
        
        return True
    elif req_decoded['status'] == 'error':
        print '\tfailed'
        print '\terror code:',  req_decoded['code']
        print '\tdescription:', req_decoded['desc']
        return False
    else:
        print '\tinvalid response:', req_decoded
        return False
    
with open('config.json', 'r') as fil:
    config = json.load(fil)

mods_list_by_ID = json.loads(
    requests.post(
        'http://api.pavel3333.ru/get_mods.php',
        data={
            'password' : PASSWORD
        }
    ).text
)
mods_list_by_name = {}

for ID in mods_list_by_ID:
    mod = mods_list_by_ID[ID].copy()
    mod_name = str(mod.pop('Name'))
    mods_list_by_name[mod_name] = mod
    mods_list_by_name[mod_name]['ID'] = ID

if not os.path.exists(unpacked_wd):
    os.mkdir(unpacked_wd)
hard_rmtree(unpacked_wd, False)

if not os.path.exists(unpacked_deploy_wd):
    os.mkdir(unpacked_deploy_wd)
hard_rmtree(unpacked_deploy_wd, False)

if not os.path.exists(deploy_wd):
    os.mkdir(deploy_wd)
hard_rmtree(deploy_wd, False)

for archive_name in os.listdir(archives_wd):
    if '.zip' not in archive_name:
        continue
    
    mod_name = str(archive_name.replace('.zip', ''))
    if mod_name not in config:
        continue
    
    isDeploy = config[mod_name].get('deploy', False)
    isPublic = config[mod_name].get('public', False)

    if isDeploy:
        if not send_mod(mod_name, isPublic):
            break

raw_input('------ DONE ------')
