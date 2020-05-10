import codecs
import os
import re
import requests
import urllib
import time
import json
import sys

from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from os import chdir, listdir, rename, remove, rmdir, makedirs
from os.path import exists, isfile, isdir, join
from hashlib import md5
from xml.etree import ElementTree as ET

DEBUG = True

WOTMODS_WD      = 'wotmod/'
ARCHIVES_WD     = 'archives/'
RAW_ARCHIVES_WD = 'raw_' + ARCHIVES_WD
DEPLOY_WD       = 'deploy/'

XFW_PACKAGES_DIR    = 'res_mods/mods/xfw_packages/'
XFW_PACKAGES_WM_DIR = 'res/mods/xfw_packages/'

DAYS_SINCE = 30

def get_reversed_path(path):
    return '../' * len(filter(lambda wd: wd, path.split('/')))

def soft_rmtree(wd, remove_wd=True):
    for item in listdir(wd):
        path = join(wd, item)
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
        path = join(wd, item)
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
        path_from = join(src_dir, item)
        path_to   = join(dest_dir, item)
        if isfile(path_from):
            rename(path_from, path_to)
        else:
            move_files(path_from, path_to)
    rmdir(src_dir)

def zip_folder(path, archive):
    for root, dirs, files in os.walk(path):
        for fil in files:
            archive.write(join(root, fil))

def create_deploy(wd, src_dir, name, folder_path, del_folder=True, isRaw=False):
    out_zip = RawArchive(src_dir, name, True) if isRaw else Archive(src_dir, name, True)
    chdir(wd)
    zip_folder(folder_path, out_zip)
    if del_folder:
        hard_rmtree(folder_path)
    chdir(get_reversed_path(wd))
    out_zip.close()

def check_depends(wd, mod_id=None):
    dependencies = set()
    
    mods_data = {}
    with open('ModsData.json', 'rb') as fil:
        mods_data = json.load(fil)
    
    for 
    
    for ID in mods_list:
        if mod_id is not None and mods_list[ID]['name'] == mod_id:
            print mod_id, 'ignored'
            continue
        
        print '\t' + mods_list[ID]['name']
        paths  = json.loads(mods_list[ID]['paths'])
        hashes = json.loads(mods_list[ID]['hashes'])
        if not paths or not hashes: continue
        if not all(
            exists(wd + paths[itemID]) \
            and md5(open(wd + paths[itemID], 'rb').read()).hexdigest() == hashes[itemID] \
            for itemID in hashes
        ):
            #print '\t\tsome files not exists or non-equal hashes'
            #print '\t\tpaths:', paths
            continue
        
        for path in paths.values():
            if isfile(wd + path):
                remove(wd + path)
            else:
                rmdir(wd + path)
        
        print '\t\tmod depends of %s (ver: %s #%s)'%(mods_list[ID]['name'], mods_list[ID]['ver'], mods_list[ID]['build'])
        dependencies.add(mods_list[ID]['name'])

    return dependencies

class Archive(ZipFile):
    IN_DIR  = 'archives/'
    OUT_DIR = 'deploy/'
    
    def __init__(self, src_dir, name, isDeploy, *args, **kwargs):
        if not isDeploy:
            self.mode = 'r'
            self.WD   = self.IN_DIR
        else:
            self.mode = 'w'
            self.WD   = self.OUT_DIR
        
        self.path = None
        
        if not isDeploy:
            path = self.WD + '%s' + name + '.zip'
            if exists(path%(src_dir + '/')):
                self.path = path%(src_dir + '/')
            elif exists(path%('')):
                self.path = path%('')
        else:
            self.path = self.WD + src_dir + '/'
            if not exists(self.path):
                makedirs(self.path)
            self.path += name + '.zip'
            print 'creating deploy archive', self.path
        
        if self.path is None:
            raise StandardError(name, 'not found in', src_dir)
        
        if isDeploy and exists(self.path):
            remove(self.path)
        
        super(Archive, self).__init__(self.path, self.mode, ZIP_DEFLATED, *args, **kwargs)

class RawArchive(Archive):
    IN_DIR  = 'raw_archives/'
    OUT_DIR = 'archives/'
    
    def getMeta(self, xfw_name=None, identifier=None):
        path = 'meta.json'
        if xfw_name is not None:
            path = XFW_PACKAGES_DIR + xfw_name + '/xfw_package.json'
        
        if path not in self.namelist():
            return None
        
        metadata = json.loads(self.read(path))
        if identifier is not None:
            metadata['id'] = identifier
        
        if DEBUG:
            for key in metadata:
                if key == 'id':
                    print metadata['id']
                else:
                    print '\t%s: %s'%(key, metadata[key])
        
        return metadata

class Package(object):
    def __init__(self, wd, name):
        self.path = wd + XFW_PACKAGES_DIR + name + '/xfw_package.json'
        self.meta = {}
        
        if exists(self.path):
            with codecs.open(self.path, 'r', 'utf-8') as metafile:
                self.meta = json.load(metafile)
        
    def getXFWPackageMeta(self, identifier=None):
        if identifier is not None:
            self.meta['id'] = identifier
        
        if DEBUG:
            for key in self.meta:
                if key == 'id':
                    print self.meta['id']
                else:
                    print '\t%s: %s'%(key, self.meta[key])
        
        return self.meta

class Wotmod(ZipFile):
    def __init__(self, path):
        self.path = path
        
        if not exists(path):
            raise StandardError(path + ' not found')
        
        super(Wotmod, self).__init__(path, 'r', ZIP_STORED)
    
    def getWotmodMeta(self):
        with self.open('meta.xml') as meta_file:
            meta = ET.fromstring(meta_file.read())
            return {
                'id'              : meta[0].text,
                'name'            : meta[2].text,
                'description'     : meta[3].text,
                'version'         : meta[1].text
            }
    
    def getXFWPackageMeta(self, name):
        meta_path = XFW_PACKAGES_WM_DIR + name + '/xfw_package.json'
        if meta_path in self.namelist():
            return json.loads(self.read(meta_path))
        return {}

    def getMeta(self, name=None, identifier=None, ver=None):
        meta = {}
        
        if name is not None:
            meta = self.getXFWPackageMeta(name)

        if not meta:
            meta = self.getWotmodMeta()

        if identifier is not None:
            meta['id'] = identifier
        
        if ver is not None:
            meta['wot_version_min'] = ver

        if 'wot_version_min' not in meta:
            meta['wot_version_min'] = raw_input('WoT version is not defined. Please type it: ')
        
        if DEBUG:
            for key in meta:
                if key == 'id':
                    print meta['id']
                else:
                    print '\t%s: %s'%(key, meta[key])

        return meta
        
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
        
        req = requests.post(
            'http://api.pavel3333.ru/add_mod.php',
            data = {
                'ID'      : mod_id,
                'name_ru' : config[mod_id]['name']['RU'],
                'name_en' : config[mod_id]['name']['EN'],
                'name_cn' : config[mod_id]['name']['CN'],
                'desc_ru' : config[mod_id]['description']['RU'],
                'desc_en' : config[mod_id]['description']['EN'],
                'desc_cn' : config[mod_id]['description']['CN'],
                'version' : metadata['version'],
                'deploy'  : 1 if config[mod_id]['deploy'] else 0,
                'public'  : 1 if config[mod_id].get('public', False) else 0
            }
        )
        
        try:
            req_decoded = json.loads(req.text)
        except Exception:
            print '\tinvalid response:', req.text
            continue
        
        if req_decoded['status'] == 'ok':
            print '\tsuccessed'
            print '\tlog:',  req_decoded['log']
            print '\tdata:', req_decoded['data']
        elif req_decoded['status'] == 'error':
            print '\tfailed'
            print '\terror code:',  req_decoded['code']
            print '\tdescription:', req_decoded['desc']
        else:
            print '\tinvalid response:', req_decoded

    with codecs.open('config.json', 'w', 'utf-8') as cfg:
        json.dump(config, cfg, ensure_ascii=False, sort_keys=True, indent=4)

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
