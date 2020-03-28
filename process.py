import urllib
import os
import requests
import json
import zipfile

from hashlib import md5

from common import *

DEBUG = False
INDENT = 4 if DEBUG else 0

config = {}

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
        
        if any(mask in path or mask in subpath for mask in self.exclude_paths):
            print 'path %s excluded'%(subpath)
            return
        
        self.ID += 1
        
        if os.path.isfile(subpath):
            #print 'file', subpath
            curr_dic[self.ID] = 0
            
            self.paths[self.ID]  = subpath
            self.names[self.ID]  = child
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
    
    if mod_name not in mods_list_by_name:
        raise StandardError('Mod is not exists on the server!')

    # cleaning
    my_rmtree(unpacked_wd, False)
    my_rmtree(unpacked_deploy_wd, False)
    
    dependencies = get_dependency(mod_name)
    #print '\tdependencies:', dependencies
    
    if isDependency:
        if main_mod_name is None:
            raise StandardError('This dependency have no main mod name')
        print 'mod: %s, dependency: %s'%(main_mod_name, mod_name)
    else:
        print 'mod:', mod_name

        for dependencyID in dependencies:
            dependency_name = mods_list_by_ID[str(dependencyID)]['name']
            send_mod(dependency_name, isPublic, mod_name)
    
    exclude_paths = []
    
    tree     = {}
    paths    = {}
    names    = {}
    hashes   = {}
    settings = {}
    
    with Archive('' if main_mod_name is None else main_mod_name, mod_name, False) as archive:  # Unpack the mod archive
        archive.extractall(unpacked_wd + mod_name)
    
    if not os.path.exists(unpacked_wd + mod_name): # Make unpacked mod dir if not exists
        os.mkdir(unpacked_wd + mod_name)
    
    if not isDependency:
        for dependencyID in dependencies:                     # Unpack all dependencies into deploy mod directory
            dependency_name = mods_list_by_ID[str(dependencyID)]['name']
            
            with Archive(mod_name, dependency_name, False) as archive:
                archive.extractall(unpacked_deploy_wd + mod_name)
        
        with Archive('', mod_name, False) as archive:         # Unpack mod into deploy mod directory
            archive.extractall(unpacked_deploy_wd + mod_name)

        if not os.path.exists(unpacked_deploy_wd + mod_name): # Make unpacked deploy mod dir if not exists
            os.mkdir(unpacked_deploy_wd + mod_name)
    
        with Archive('', mod_name, True) as archive:          # Make deploy archive
            os.chdir(unpacked_deploy_wd + mod_name + '/')
            zip_folder('./', archive)
            os.chdir('../../')
    
    mod = mods_list_by_name[mod_name]

    settings_path = mod['settings_path']                                  # Exclude settings path
    if settings_path:
        exclude_paths.append(settings_path)

    if str(mod_name) in config and 'excludeChecksum' in config[mod_name]: # Exclude checksum
        exclude_paths.extend(config[mod_name]['excludeChecksum'])
    
    os.chdir(unpacked_wd + mod_name + '/')

    structure = ModStructure(exclude_paths, './') # Get tree, paths, names and hashes
    structure.setSettings(mod['settings_path'])   # Set mod settings file
    
    os.chdir('../../')

    if not isPublic: return

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
            'ID'           : mod['ID'],
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
        return
    
    if req_decoded['status'] == 'ok':
        print '\tsuccessed'
        print '\tlog:',  req_decoded['log']
        print '\tdata:', req_decoded['data']
        
        name = req_decoded['data']
    
        with open('json/%s.json'%(name), 'w') as fil:
            fil.write(
                json.dumps(
                    {
                        'tree'     : structure.tree,
                        'paths'    : structure.paths,
                        'names'    : structure.names,
                        'hashes'   : structure.hashes,
                        'settings' : structure.settings
                    },
                    sort_keys=True,
                    indent=INDENT
                )
            )
        
    elif req_decoded['status'] == 'error':
        print '\tfailed'
        print '\terror code:',  req_decoded['code']
        print '\tdescription:', req_decoded['desc']
    else:
        print '\tinvalid response:', req_decoded
    
with open('config.json', 'r') as fil:
    config = json.load(fil)

mods_list_by_ID   = json.loads(urllib.urlopen('http://api.pavel3333.ru/get_mods.php').read())
mods_list_by_name = {}

for ID in mods_list_by_ID:
    mod = mods_list_by_ID[ID]
    mods_list_by_name[str(mod['name'])] = {
        'ID'            : ID,
        'ver'           : mod['ver'],
        'upd'           : mod['upd'],
        'build'         : mod['build'],
        'settings_path' : mod['settings_path']
    }

if not os.path.exists(unpacked_wd):
    os.mkdir(unpacked_wd)
my_rmtree(unpacked_wd, False)

if not os.path.exists(unpacked_deploy_wd):
    os.mkdir(unpacked_deploy_wd)
my_rmtree(unpacked_deploy_wd, False)

if not os.path.exists(deploy_wd):
    os.mkdir(deploy_wd)
my_rmtree(deploy_wd, False)

for archive_name in os.listdir(archives_wd):
    if '.zip' not in archive_name:
        continue
    
    mod_name = str(archive_name.replace('.zip', ''))
    if mod_name not in config:
        continue
    
    isDeploy = config[mod_name].get('deploy', False)
    isPublic = config[mod_name].get('public', False)

    if isDeploy:
        send_mod(mod_name, isPublic)
