import os
import urllib
import json

from zipfile import ZipFile, ZIP_DEFLATED
from os import chdir, listdir, rename, remove, rmdir, makedirs
from os.path import exists, isfile, join
from hashlib import md5

def get_reversed_path(path):
    return '../' * len(filter(lambda wd: wd, path.split('/')))

def my_rmtree(wd):
    for item in listdir(wd):
        path = join(wd, item)
        if isfile(path):
            remove(path)
        else:
            my_rmtree(path)
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

def create_archive(wd, zip_path, folder_path, del_folder=True):
    if exists(zip_path):
        remove(zip_path)
    
    with ZipFile(zip_path, 'w', ZIP_DEFLATED) as out_zip:
        chdir(wd)
        zip_folder(folder_path, out_zip)
        if del_folder:
            my_rmtree(folder_path)
        chdir(get_reversed_path(wd))

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
