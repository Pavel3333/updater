import codecs
import requests
import json

from time import time, sleep
from os import mkdir
from os.path import exists

from common import *

TAGS = {
    11: "Damage Panels",
    12: "Modpacks",
    13: "Hangars",
    14: "Icons",
    15: "Crosshairs",
    16: "Skins",
    17: "Sounds",
    18: "User Interface",
    19: "Minimaps",
    20: "Other",
    21: "Models",
    22: "Stats"
}
MAX_ID = 200

cfg = {
    'processedID'   : [],
    'lastCheckTime' : 0
}
cfg_path = 'wgmods_config.json'

if not exists(cfg_path):
    with open(cfg_path, 'w') as cfg_file:
        json.dump(cfg, cfg_file, sort_keys=True, indent=4)
else:
    with open(cfg_path, 'r') as cfg_file:
        cfg = json.load(cfg_file)

if time() > cfg['lastCheckTime'] + 86400:
    cfg['processedID'] = []

def get_mod_data(mod_id):
    url_page = 'https://wgmods.net/%s/'%(mod_id)
    url_api  = 'https://wgmods.net/api/mods/%s/'%(mod_id)
    
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ru,en;q=0.9',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Host':'wgmods.net',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 YaBrowser/19.12.3.320 Yowser/2.5 Safari/537.36',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1'
    }
    
    response = requests.get(url_page, headers=headers)
    
    headers.update({
        'Accept'           : 'application/json',
        'Cookie'           : '; '.join([x.name + '=' + x.value for x in response.cookies]),
        'Content-Type'     : 'application/json; charset=utf-8',
        'Referer'          : url_page,
        'Sec-Fetch-Mode'   : 'cors',
        'Sec-Fetch-Site'   : 'same-origin',
        #'X-CSRFToken'      : 'HZvIer0ri6dsbrlsoqpZo1KLrLNEcHiioUssssBFiV7jaWGe1S85PGwcOyBM9nij',
        'X-Requested-With' : 'XMLHttpRequest'
    })

    response = requests.get(url_api, headers=headers)

    getted_data = {}
    try:
        getted_data = json.loads(response.text.encode('utf-8'))
    except Exception:
        print mod_id, 'unable to decode json. response:', response.text
        return {}

    if len(getted_data) <= 8:
        print mod_id, 'not found'
        return {}

    name        = {}
    description = {}
    archives    = {}
    
    for mod in getted_data['versions']:
        game_ver = str(mod['game_version']['version'])
        mod_ver  = mod['version']
        archives['%s_%s'%(game_ver, mod_ver)] = {
            'game_version'      : game_ver,
            'mod_version'       : mod_ver,
            #comment
            'filename'          : str(mod['version_file']),
            'original_filename' : mod['version_file_original_name'],
            'url'               : str(mod['download_url'])
            #change_log
        }
    
    for desc in getted_data['localizations']:
        lang = str(desc['lang']['code'])
        if lang == 'ru':
            lang = 'RU'
        elif lang == 'en':
            lang = 'EN'
        else:
            print 'unexpected language:', lang
            continue
        name[lang]        = desc['title']
        description[lang] = desc['description'] + '\n' + desc['installation_guide']
    
    return {
        'author'      : getted_data['author_name'],
        'name'        : name,
        'description' : description,
        #change_log
        'img_cover'   : str(getted_data['cover']),
        'downloads'   : getted_data['downloads'],
        'mark'        : getted_data['mark'],
        'votes_count' : getted_data['mark_votes_count'],
        'owner'       : str(getted_data['owner']['spa_username']),
        'rating'      : getted_data['rating'],
        #screenshots
        'tags'        : getted_data['tags'],
        'archives'    : archives
    }

wd = 'wgmods_zip/'

if exists(wd):
    hard_rmtree(wd)
mkdir(wd)

setAfterCheck = False

to_process = cfg['processedID']
if not to_process:
    to_process = xrange(1, MAX_ID)
    setAfterCheck = True

for ID in to_process:
    data = get_mod_data(ID)
    if not data: continue
    
    if not all(archive['filename'].endswith('.zip') for archive in data['archives'].values()):
        print ID, 'is not zip archive'
        continue
    
    with codecs.open(wd + '%s_%s.json'%(int(data['rating']*data['downloads']), ID), 'w', 'utf-8') as data_file:
        json.dump(data, data_file, ensure_ascii=False, sort_keys=True, indent=4)
    print ID, 'getted successfully'
    if setAfterCheck:
        cfg['processedID'].append(ID)
    sleep(0.5)
        

if setAfterCheck:
    cfg['lastCheckTime'] = time()

with open(cfg_path, 'w') as cfg_file:
    json.dump(cfg, cfg_file, sort_keys=True, indent=4)
