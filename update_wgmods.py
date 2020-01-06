import codecs
import json

from os import listdir
from os.path import exists

IDs = [95]
wd = 'wgmods_zip/'



if exists(wd):
    for ID in IDs:
        for filename in filter(lambda name: name.endswith('_%s.json'%(ID)), listdir(wd)):
            with codecs.open(wd + filename, 'r', 'ascii') as fil:
                with codecs.open(wd + filename.replace('.json', '_encoded.json'), 'w', 'utf-8') as fil_new:
                    fil_new.write(fil.read().decode('utf-8'))
                
