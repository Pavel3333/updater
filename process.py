import urllib
import os
import requests
import json
import zipfile
import shutil

from hashlib import md5

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

def get_dependency(mod_name, is_deploy):
    if mod_name not in config:
        print mod_name, 'not in config'
        return set()
    if 'dependencies' not in config[mod_name]:
        print 'dependencies not in config[mod_name]'
        return set()
    
    dependency_list = config[mod_name]['dependencies']
    for dependency in dependency_list:
        dependencies.add(int(mods_list_by_name[dependency]['ID']))
        if is_deploy:
            get_dependency(dependency, is_deploy)

def zip_folder(path, archive):
    for root, dirs, files in os.walk(path):
        for fil in files:
            archive.write(os.path.join(root, fil))
    
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

if os.path.exists('unpacked'):
    shutil.rmtree('unpacked')
os.mkdir('unpacked')

if os.path.exists('unpacked_deploy'):
    shutil.rmtree('unpacked_deploy')
os.mkdir('unpacked_deploy')

if os.path.exists('deploy'):
    shutil.rmtree('deploy')
os.mkdir('deploy')

for archive_name in os.listdir('archives'):
    if '.zip' not in archive_name:
        raise StandardError('Archive %s is not ZIP-archive'%(archive_name))

    exclude_paths = []

    ID = 0
    
    tree     = {}
    paths    = {}
    names    = {}
    hashes   = {}
    settings = {}
    
    mod_name = str(archive_name.replace('.zip', ''))

    is_deploy = False
    if mod_name in config and config[mod_name].get('deploy', False):
        is_deploy = True
    
    dependencies = set()

    get_dependency(mod_name, is_deploy)
    print mod_name, 'mod dependencies:', dependencies
    
    if mod_name not in mods_list_by_name:
        raise StandardError('Mod %s is not exists on the server!'%(mod_name))

    with zipfile.ZipFile('archives/' + archive_name) as archive:
        archive.extractall('unpacked/' + mod_name)

    if is_deploy:
        for dependencyID in dependencies:
            dependency_name = mods_list_by_ID[str(dependencyID)]['name']
            
            with zipfile.ZipFile('archives/%s.zip'%(dependency_name)) as archive:
                archive.extractall('unpacked_deploy/' + mod_name)
        
        with zipfile.ZipFile('archives/' + archive_name) as archive:
            archive.extractall('unpacked_deploy/' + mod_name)

        with zipfile.ZipFile('deploy/' + archive_name, 'w', zipfile.ZIP_DEFLATED) as archive:
            os.chdir('unpacked_deploy/%s/'%(mod_name))
            zip_folder('./', archive)
            os.chdir('../../')
    
    mod = mods_list_by_name[mod_name]

    settings_path = mod['settings_path']
    if settings_path:
        exclude_paths.append(settings_path)

    if str(mod_name) in config and 'excludeChecksum' in config[mod_name]:
        exclude_paths.extend(config[mod_name]['excludeChecksum'])
    
    os.chdir('unpacked/%s/'%(mod_name))
    for child in os.listdir('./'):
        move('', child, tree)

    settings_path = mod['settings_path']
    if settings_path:
        print 'settings_path', settings_path
        with open(settings_path, 'r') as fil:
            settings = json.loads(fil.read().decode('utf-8-sig'))

    os.chdir('../../json/')
    
    prefix = '%s_%s_#%d_%s'%(mod_name, mod['ver'], int(mod['build']) + 1, mod['upd'])
    
    with open(prefix + '.json', 'w') as fil:
        fil.write(
            json.dumps(
                {'tree'     : tree,
                 'paths'    : paths,
                 'names'    : names,
                 'hashes'   : hashes,
                 'settings' : settings
                },
                sort_keys=True,
                indent=INDENT
            )
        )

    os.chdir('../')
    
    files_dict = {
        'mod_autoupd' : open('archives/%s.zip'%(mod_name), 'rb')
    }

    if is_deploy:
        files_dict['mod_deploy'] = open('deploy/%s.zip'%(mod_name), 'rb')
    
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

    print req.text
