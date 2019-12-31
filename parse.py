import json
from hashlib import md5

need_to_upd = []

tree   = {}
names  = {}
hashes = {}

with open('tree.json', 'r') as fil:
    tree = json.loads(fil.read())

with open('names.json', 'r') as fil:
    names = json.loads(fil.read())

with open('hashes.json', 'r') as fil:
    hashes = json.loads(fil.read())

def walk(path, curr_dic):
    for ID in curr_dic:
        subpath = path + names[ID]
        if curr_dic[ID] == 0:
            print 'File  :', subpath
            #print 'Hash:', hashes[ID]
            hash_ = md5(open(subpath, 'rb').read()).hexdigest()

            if hash_ != hashes[ID]:
                need_to_upd.append(int(ID))
        else:
            print 'Folder:', subpath
            walk(path + names[ID] + '/', curr_dic[ID])

walk('', tree)
print need_to_upd
