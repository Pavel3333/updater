import urllib
import os
import requests
import json
import zipfile

from hashlib import md5

from common import my_rmtree, zip_folder

DEBUG = False
INDENT = 4 if DEBUG else 0

config = {}

ID = 0

tree   = {}
paths  = {}
names  = {}
hashes = {}

dependencies = set()

exclude_paths = []

archives_wd        = 'archives/'
unpacked_wd        = 'unpacked/'
unpacked_deploy_wd = 'unpacked_deploy/'
deploy_wd          = 'deploy/'

def move(path, child, curr_dic):
    subpath = path + child
    
    if any(mask in path or mask in subpath for mask in exclude_paths):
        print 'path %s excluded'%(subpath)
        return

    global ID
    ID += 1
    
    if os.path.isfile(subpath):
        #print 'File:', child
        
        curr_dic[ID] = 0
        
        paths[ID]  = subpath
        names[ID]  = child
        hashes[ID] = md5(open(subpath, 'rb').read()).hexdigest()
    else:
        #print 'Folder:', child

        subpath += '/'
        subdic = curr_dic[ID] = {}
        names[ID] = child
        
        for subchild in os.listdir(subpath):
            move(subpath, subchild, subdic)

def get_dependency(main_mod_name, mod_name=None):
    if main_mod_name not in config:
        print main_mod_name, 'not in config'
        return set()
    
    if mod_name is None:
        mod_name = main_mod_name
    
    if mod_name not in config:
        print mod_name, 'not in config'
        return set()
    if 'dependencies' not in config[mod_name]:
        print 'dependencies not in', mod_name, 'config'
        return set()
    
    dependency_list = config[mod_name]['dependencies']
    for dependency in dependency_list:
        if dependency == main_mod_name: #recursion protection
            continue
        
        dependencies.add(int(mods_list_by_name[dependency]['ID']))
        if config[main_mod_name]['deploy']:
            get_dependency(main_mod_name, dependency)
    
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

if os.path.exists(unpacked_wd):
    my_rmtree(unpacked_wd)
os.mkdir(unpacked_wd)

if os.path.exists(unpacked_deploy_wd):
    my_rmtree(unpacked_deploy_wd)
os.mkdir(unpacked_deploy_wd)

if os.path.exists(deploy_wd):
    my_rmtree(deploy_wd)
os.mkdir(deploy_wd)

for archive_name in os.listdir(archives_wd):
    if '.zip' not in archive_name:
        continue

    exclude_paths = []

    ID = 0
    
    tree     = {}
    paths    = {}
    names    = {}
    hashes   = {}
    settings = {}
    
    mod_name = str(archive_name.replace('.zip', ''))
    print 'mod:', mod_name

    is_deploy = False
    if mod_name in config and config[mod_name].get('deploy', False):
        is_deploy = True
    
    dependencies = set()

    get_dependency(mod_name)
    '\tdependencies:', dependencies
    
    if mod_name not in mods_list_by_name:
        raise StandardError('Mod is not exists on the server!')

    with zipfile.ZipFile(archives_wd + archive_name) as archive:
        archive.extractall(unpacked_wd + mod_name)

    if not os.path.exists(unpacked_wd + mod_name):
        os.mkdir(unpacked_wd + mod_name)

    if is_deploy:
        for dependencyID in dependencies:
            dependency_name = mods_list_by_ID[str(dependencyID)]['name']
            
            with zipfile.ZipFile(archives_wd + '%s.zip'%(dependency_name)) as archive:
                archive.extractall(unpacked_deploy_wd + mod_name)
        
        with zipfile.ZipFile(archives_wd + archive_name) as archive:
            archive.extractall(unpacked_deploy_wd + mod_name)

        if not os.path.exists(unpacked_deploy_wd + mod_name):
            os.mkdir(unpacked_deploy_wd + mod_name)

        with zipfile.ZipFile(deploy_wd + archive_name, 'w', zipfile.ZIP_DEFLATED) as archive:
            os.chdir(unpacked_deploy_wd + mod_name + '/')
            zip_folder('./', archive)
            os.chdir('../../')
    
    mod = mods_list_by_name[mod_name]

    settings_path = mod['settings_path']
    if settings_path:
        exclude_paths.append(settings_path)

    if str(mod_name) in config and 'excludeChecksum' in config[mod_name]:
        exclude_paths.extend(config[mod_name]['excludeChecksum'])
    
    os.chdir(unpacked_wd + mod_name + '/')
    
    for child in os.listdir('./'):
        move('', child, tree)

    settings_path = mod['settings_path']
    if settings_path:
        with open(settings_path, 'r') as fil:
            settings = json.loads(fil.read().decode('utf-8-sig'))

    os.chdir('../../')
    
    files_dict = {
        'mod_autoupd' : open(archives_wd + '%s.zip'%(mod_name), 'rb')
    }

    if is_deploy:
        files_dict['mod_deploy'] = open(deploy_wd + '%s.zip'%(mod_name), 'rb')
    
    req = requests.post(
        'http://api.pavel3333.ru/update_mods.php',
        data = {
            'ID'           : mod['ID'],
            'tree'         : json.dumps(tree,               sort_keys=True),
            'paths'        : json.dumps(paths,              sort_keys=True),
            'names'        : json.dumps(names,              sort_keys=True),
            'hashes'       : json.dumps(hashes,             sort_keys=True),
            'settings'     : json.dumps(settings,           sort_keys=True),
            'dependencies' : json.dumps(list(dependencies), sort_keys=True)
        },
        files = files_dict
    )
    
    try:
        req_decoded = json.loads(req.text)
    except Exception:
        print 'invalid response:', req.text
        continue
    
    if req_decoded['status'] == 'ok':
        print '\tsuccessed'
        print '\tlog:',  req_decoded['log']
        print '\tdata:', req_decoded['data']
        
        name = req_decoded['data']
    
        with open('json/%s.json'%(name), 'w') as fil:
            fil.write(
                json.dumps(
                    {
                        'tree'     : tree,
                         'paths'    : paths,
                         'names'    : names,
                         'hashes'   : hashes,
                         'settings' : settings
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
