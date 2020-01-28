import codecs
import os
import urllib
import json

from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from os import chdir, listdir, rename, remove, rmdir, makedirs
from os.path import exists, isfile, join
from hashlib import md5
from xml.etree import ElementTree as ET

DEBUG = True

def get_reversed_path(path):
    return '../' * len(filter(lambda wd: wd, path.split('/')))

def my_rmtree(wd, remove_wd=True):
    for item in listdir(wd):
        path = join(wd, item)
        if isfile(path):
            remove(path)
        else:
            my_rmtree(path)
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

def create_deploy(wd, name, folder_path, del_folder=True, isRaw=False):
    out_zip = RawArchive(name, True) if isRaw else Archive(name, True)
    chdir(wd)
    zip_folder(folder_path, out_zip)
    if del_folder:
        my_rmtree(folder_path)
    chdir(get_reversed_path(wd))
    out_zip.close()

def check_depends(wd):
    dependencies = set()
    
    mods_list = json.loads(urllib.urlopen('http://api.pavel3333.ru/get_mods.php').read())

    for ID in mods_list:
        paths  = json.loads(mods_list[ID]['paths'])
        hashes = json.loads(mods_list[ID]['hashes'])
        if not paths or not hashes: continue
        if not all(
            exists(wd + paths[itemID]) \
            and md5(open(wd + paths[itemID], 'rb').read()).hexdigest() == hashes[itemID] \
            for itemID in hashes
        ):  continue
        
        for path in paths.values():
            if isfile(wd + path):
                remove(wd + path)
            else:
                rmdir(wd + path)
        
        print 'mod depends of %s (ver: %s #%s)'%(mods_list[ID]['name'], mods_list[ID]['ver'], mods_list[ID]['build'])
        dependencies.add(mods_list[ID]['name'])

    return dependencies

class Archive(ZipFile):
    IN_DIR  = 'archives/'
    OUT_DIR = 'deploy/'
    
    def __init__(self, name, isDeploy, *args, **kwargs):
        if not isDeploy:
            self.mode = 'r'
            self.WD   = self.IN_DIR
        else:
            self.mode = 'w'
            self.WD   = self.OUT_DIR
        
        self.path = self.WD + name + '.zip'
        
        if isDeploy and exists(self.path):
            remove(self.path)
        elif not isDeploy and not exists(self.path):
            raise StandardError(self.path, 'not found')
        
        super(Archive, self).__init__(self.path, self.mode, ZIP_DEFLATED, *args, **kwargs)

class RawArchive(Archive):
    IN_DIR  = 'raw_archives/'
    OUT_DIR = 'archives/'
    
    XFW_PACKAGES_DIR = 'res_mods/mods/xfw_packages/'
    
    def getXFWPackageMeta(self, name, identifier=None):
        path = self.XFW_PACKAGES_DIR + name + '/xfw_package.json'
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
    XFW_PACKAGES_DIR = 'res_mods/mods/xfw_packages/'
    
    def __init__(self, wd, name):
        self.path = wd + self.XFW_PACKAGES_DIR + name + '/xfw_package.json'
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
    XFW_PACKAGES_DIR = 'res/mods/xfw_packages/'
    
    def __init__(self, path):
        self.path = path
        
        if not exists(path):
            raise StandardError(path, 'not found')
        
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
        meta = {}
        meta_path = self.XFW_PACKAGES_DIR + name + '/xfw_package.json'
        if meta_path in self.namelist():
            meta = json.loads(self.read(meta_path))
        
        return meta

    def getMeta(self, name=None, identifier=None):
        if name is not None:
            meta = self.getXFWPackageMeta(name)

        if not meta:
            meta = self.getWotmodMeta()

        if identifier is not None:
            meta['id'] = identifier

        if 'wot_version_min' not in meta:
            meta['wot_version_min'] = raw_input('WoT version is not defined. Please type it: ')
        
        if DEBUG:
            for key in meta:
                if key == 'id':
                    print meta['id']
                else:
                    print '\t%s: %s'%(key, meta[key])

        return meta
        
