import codecs
import os
import json
import requests

from urllib import urlretrieve
from zipfile import ZipFile, ZIP_DEFLATED
from os import chdir, rename, remove, listdir, mkdir, makedirs
from os.path import basename, exists, isfile, join
from shutil import rmtree
from xml.etree import ElementTree as ET

def zip_folder(path, archive):
    for root, dirs, files in os.walk(path):
        for fil in files:
            archive.write(join(root, fil))

filename = 'xvm.zip'
urlretrieve('https://nightly.modxvm.com/download/master/xvm_latest.zip', filename)
print filename, 'successfully downloaded'

if exists('temp'):
    rmtree('temp')
mkdir('temp')

with ZipFile(filename) as archive:
    archive.extractall(
        'temp/',
        filter(lambda path: 'res_mods/mods/xfw_packages/' in path, archive.namelist())
    )

packages_metadata = {}
packages_wd = 'temp/res_mods/mods/xfw_packages/'

if exists(packages_wd):
    for package_name in listdir(packages_wd):
        package_path = packages_wd + package_name + '/xfw_package.json'
        
        if not exists(package_path):
            print '%s: metainfo was not found'%(package_name)
            continue

        metadata = {}
        
        with open(package_path, 'r') as package:
            metadata = json.load(package)
            packages_metadata[metadata['id']] = metadata

        print '%s:\n\tID: %s\n\tName: %s\n\tDescription: %s\n\tVersion: %s\n\tWoT version: %s'%(
            package_name,
            metadata['id'],
            metadata['name'],
            metadata['description'],
            metadata['version'],
            metadata['wot_version_min']
        )
        if 'dependencies' in metadata:
            print '\tDependencies: %s'%(metadata['dependencies'])
        if 'wot_version_exactmatch' in metadata:
            print '\tExactly match: %s'%(metadata['wot_version_exactmatch'])
        
        zip_dir  = 'mods/%s/com.modxvm.xfw/'%(metadata['wot_version_min'])
        zip_path = 'archives/%s.zip'%(metadata['id'])
        if exists(zip_path):
            remove(zip_path)
        
        with ZipFile(zip_path, 'w', ZIP_DEFLATED) as out_zip:
            chdir('temp/')
            zip_folder('res_mods/mods/xfw_packages/%s/'%(package_name), out_zip)
            chdir('../')

#archive.extract(path, 'unpacked/%s/mods/%s/com.modxvm.xfw/')

rmtree('temp')
remove(filename)

config = {}
with codecs.open('config.json', 'r', 'utf-8') as cfg:
    config = json.load(cfg)

for mod_name in packages_metadata:
    if mod_name not in config:
        print mod_name, 'not found in config. Creating a new one...'
        config[mod_name] = {}
    
    if 'deploy' not in config[mod_name]:
        config[mod_name]['deploy'] = False

    metadata = packages_metadata[mod_name]
    
    dependencies = set()
    if 'dependencies' not in metadata:
        print 'Dependencies not found in %s. Please set it manually'%(metadata['name'])
        config[mod_name]['dependencies'] = []
    else:
        dependencies.update(set(metadata['dependencies']))
    
    if 'dependencies_optional' in metadata:
        dependencies.update(set(metadata['dependencies_optional']))

    print mod_name, 'deps:', dependencies
    
    config[mod_name]['dependencies'] = list(dependencies)

    if 'name' not in config[mod_name]:
        config[mod_name]['name'] = {
            'RU' : metadata['name'],
            'EN' : metadata['name'],
            'CN' : metadata['name']
        }

    if 'description' not in config[mod_name]:
        config[mod_name]['description'] = {
            'RU' : metadata['description'],
            'EN' : metadata['description'],
            'CN' : metadata['description']
        }
    
    req = requests.post(
        'http://api.pavel3333.ru/add_mod.php',
        data = {
            'ID'           : metadata['id'],
            'name_ru'      : config[mod_name]['name']['RU'],
            'name_en'      : config[mod_name]['name']['EN'],
            'name_cn'      : config[mod_name]['name']['CN'],
            'desc_ru'      : config[mod_name]['description']['RU'],
            'desc_en'      : config[mod_name]['description']['EN'],
            'desc_cn'      : config[mod_name]['description']['CN'],
            'version'      : metadata['version'],
            'deploy'       : config[mod_name]['deploy']
        }
    )
    print req.text
    
with codecs.open('config.json', 'w', 'utf-8') as cfg:
    json.dump(config, cfg, ensure_ascii=False, sort_keys=True, indent=4) #
