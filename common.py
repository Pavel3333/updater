import os
import re
import sys
import time
import json
import codecs
import shutil
import urllib
import requests

from os import chdir, listdir, rename, remove, rmdir, makedirs
from os.path import exists, isfile, isdir
from hashlib import md5

DEBUG    = False
PASSWORD = open('password.txt', 'rb').read()
INDENT   = 4

WOTMODS_WD      = 'wotmod/'
ARCHIVES_WD     = 'archives/'
RAW_ARCHIVES_WD = 'raw_' + ARCHIVES_WD
DEPLOY_WD       = 'deploy/'

XFW_PACKAGES_DIR    = 'res_mods/mods/xfw_packages/'
XFW_PACKAGES_WM_DIR = 'res/mods/xfw_packages/'

DAYS_SINCE = 30

def print_indent(indent, *args):
    print ' ' * indent + ' '.join(map(str, args)) 

def print_debug(*args):
    if DEBUG:
        print_indent(*args)

def get_reversed_path(path):
    return '../' * len(filter(lambda wd: wd, path.split('/')))

def myjoin(*args):
    return os.path.join(*args).replace('\\', '/')

class Shared():
    TEMP_DIR            = 'mytemp/'
    ARCHIVES_TEMP_DIR   = 'archives_temp/'
    ARCHIVES_DEPLOY_DIR = 'archives_deploy/'
    
    CONFIG_PATH              = 'config.json'
    RAW_ARCHIVES_CONFIG_PATH = 'raw_archives.json'
    
    def __init__(self):
        self.delete_after_fini = set()
        
        self.config              = self.getJSON(self.CONFIG_PATH,              {})
        self.raw_archives_config = self.getJSON(self.RAW_ARCHIVES_CONFIG_PATH, {})
    
    @staticmethod
    def getJSON(path, pattern):
        raw = {}
        
        if exists(path):
            with codecs.open(path, 'r', 'utf-8') as fil:
                raw = json.load(fil)
        else:
            raw = pattern
            
            with codecs.open(path, 'w', 'utf-8') as fil:
                json.dump(raw, fil, sort_keys=True, indent=4)
        
        return raw
    
    def indent(self, elem, level=0):
      i = "\n" + level*"  "
      if len(elem):
        if not elem.text or not elem.text.strip():
          elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
          elem.tail = i
        for elem in elem:
          self.indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
          elem.tail = i
      else:
        if level and (not elem.tail or not elem.tail.strip()):
          elem.tail = i

g_Shared = Shared()

def soft_rmtree(wd, remove_wd=True):
    for item in listdir(wd):
        path = myjoin(wd, item)
        if isdir(path):
            if not listdir(path):
                rmdir(path)
            else:
                soft_rmtree(path)
        else:
            print 'excess file found:', path
    if remove_wd and not listdir(wd):
        rmdir(wd)

def hard_rmtree(wd, remove_wd=True):
    for item in listdir(wd):
        path = myjoin(wd, item)
        if isfile(path):
            remove(path)
        else:
            hard_rmtree(path)
    if remove_wd:
        rmdir(wd)

def move_files(src_dir, dest_dir):
    if not exists(dest_dir):
        makedirs(dest_dir)
    
    for item in listdir(src_dir):
        path_from = myjoin(src_dir, item)
        path_to   = myjoin(dest_dir, item)
        if isfile(path_from):
            rename(path_from, path_to)
        else:
            move_files(path_from, path_to)
    rmdir(src_dir)

def zip_folder(path, archive):
    for root, dirs, files in os.walk(path):
        for fil in files:
            archive.write(myjoin(root, fil))

try:
    mods_data = json.loads(
        requests.post(
            'http://api.pavel3333.ru/get_builds_data.php',
            data={
                'password' : PASSWORD
            }
        ).text
    )
except IOError as exc:
    mods_data = {}
    print 'Unable to get mods data: ' + str(exc.message)

def add_mods(packages_metadata):
    config = {}
    with codecs.open('config.json', 'r', 'utf-8') as cfg:
        config = json.load(cfg)
    
    for mod_id in packages_metadata:
        print mod_id
        
        if mod_id not in config:
            print mod_id, 'not found in config. Creating a new one...'
            config[mod_id] = {}

        if 'deploy' not in config[mod_id]:
            config[mod_id]['deploy'] = False

        if config[mod_id]['deploy'] and 'public' not in config[mod_id]:
            config[mod_id]['public'] = False
        elif not config[mod_id]['deploy'] and 'public' in config[mod_id]:
            del config[mod_id]['public']
        
        metadata = packages_metadata[mod_id]
        
        dependencies = set(config[mod_id].get('dependencies', []))
        if 'dependencies' not in metadata:
            print 'Dependencies not found in %s. Please set it manually'%(metadata['name'])
        else:
            dependencies.update(set(metadata['dependencies']) | set(metadata.get('dependencies_optional', [])))
        
        config[mod_id]['dependencies'] = list(filter(lambda name: name != mod_id, dependencies))

        if 'excludeChecksum' in metadata:
            config[mod_id]['excludeChecksum'] = metadata['excludeChecksum']
            
        if 'name' not in config[mod_id]:
            config[mod_id]['name'] = {
                'RU' : metadata['name'],
                'EN' : metadata['name'],
                'CN' : metadata['name']
            }

        if 'description' not in config[mod_id]:
            config[mod_id]['description'] = {
                'RU' : metadata['description'],
                'EN' : metadata['description'],
                'CN' : metadata['description']
            }

        #if not config[mod_id].get('public', False):
        #    print '\tnot public mod'
        #    continue
        
        config[mod_id]['version'] = metadata['version']
        
        req = requests.post(
            'http://api.pavel3333.ru/add_mod.php',
            data = {
                'password' : PASSWORD,
                
                'name'     : mod_id,
                'name_ru'  : config[mod_id]['name']['RU'],
                'name_en'  : config[mod_id]['name']['EN'],
                'name_cn'  : config[mod_id]['name']['CN'],
                'desc_ru'  : config[mod_id]['description']['RU'],
                'desc_en'  : config[mod_id]['description']['EN'],
                'desc_cn'  : config[mod_id]['description']['CN'],
                'deploy'   : 1 if config[mod_id]['deploy'] else 0,
                'public'   : 1 if config[mod_id].get('public', False) else 0
            }
        )
        
        try:
            req_decoded = json.loads(req.text)
        except Exception:
            print '\tinvalid response:', req.text
            break
        
        if req_decoded['status'] == 'ok':
            print '\tsuccessed'
            print '\tlog:',  req_decoded['log']
            print '\tdata:', req_decoded['data']
        elif req_decoded['status'] == 'error':
            print '\tfailed'
            print '\terror code:',  req_decoded['code']
            print '\tdescription:', req_decoded['desc']
            break
        else:
            print '\tinvalid response:', req_decoded
            break

    with codecs.open('config.json', 'w', 'utf-8') as cfg:
        json.dump(config, cfg, ensure_ascii=False, sort_keys=True, indent=4)
    

def check_depends(wd, exclude_name=None):
    dependencies = set()
    
    for mod_name in mods_data:
        if exclude_name is not None and mod_name == exclude_name:
            print mod_name, 'ignored'
            continue
        for wot_version in reversed(mods_data[mod_name].keys()):
            for version in reversed(mods_data[mod_name][wot_version].keys()):
                for build in reversed(mods_data[mod_name][wot_version][version].keys()):
                    build_data = mods_data[mod_name][wot_version][version][str(build)]
                    
                    paths  = build_data['paths']
                    hashes = build_data['hashes']
                    
                    if not hashes or not all(
                        exists(wd + paths[itemID])                                                   \
                        and md5(open(wd + paths[itemID], 'rb').read()).hexdigest() == hashes[itemID] \
                        for itemID in hashes
                    ):
                        continue
                    
                    print '\tmod depends of %s (WoT %s, ver: %s #%s)'%(mod_name, wot_version, version, build)
                    
                    for path in paths.values():
                        if isfile(wd + path):
                            remove(wd + path)
                        else:
                            rmdir(wd + path)
                    
                    dependencies.add(mod_name)
    
    return dependencies

def check_patch(dirname):
    pattern = r'(\d+)'
    pattern_max_length = len(pattern)
    if pattern_max_length % 2:
        pattern_max_length += 1
    pattern_max_length = pattern_max_length // 2
    for i in xrange(pattern_max_length, 0, -1):
        if re.match(r'.'.join((pattern,) * i), dirname) is not None:
            return True
    return False

def check_wd(wd):
    if wd and not exists(wd):
        makedirs(wd)

def remove_unknown(path):
    if not exists(path):
        return
    
    if os.path.isfile(path):
        remove(path)
    elif os.path.isdir(path):
        hard_rmtree(path)

def get_archive(mod_name):
    fmt        = 'https://gitlab.com/api/v4/projects/xvm%%2Fxvm/repository/commits?since=%s'
    since_time = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() - DAYS_SINCE * 86400))

    data     = urllib.urlopen(fmt%(since_time)).read()
    xvm_data = {}
    
    try:
        xvm_data = json.loads(data)
    except:
        print 'failed to parse XVM data'
        print data
        sys.exit(1)
    
    for commit in xvm_data:
        dt = time.time() - time.mktime(time.strptime(commit['created_at'].split('T')[0], '%Y-%m-%d'))
        add = ' <================' if 'wot' in commit['title'].lower() else ''
        print commit['id']
        print '\t' + commit['title'], '(%s days ago)'%(int(dt//86400)) + add
        #print '\t' + 'author :', commit['author_name']

    print ''
    
    page = urllib.urlopen('https://nightly.modxvm.com/download/master/').read()

    commit  = raw_input('Please type the commit: ')
    matches = re.search(r'%s_([0-9._]+)_master_%s.zip'%(mod_name, commit), page)
    if not matches:
        raise ValueError('This commit was not found')
    
    archive_name = matches.group(0)
    
    filename = mod_name + '.zip'
    print 'downloading', archive_name
    urllib.urlretrieve('https://nightly.modxvm.com/download/master/%s'%(archive_name), filename)
    print filename, 'successfully downloaded'

    return filename
