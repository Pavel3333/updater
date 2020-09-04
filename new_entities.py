import codecs
import os
import sys

from zipfile   import ZipFile, ZIP_STORED, ZIP_DEFLATED
from xml.etree import ElementTree as ET
from hashlib import md5

from new_common import *

AnalyzeType = {
    'Init'     : 0,
    'Simple'   : 1,
    'Packages' : 2,
    'Mods'     : 3,
    'RawMods'  : 4,
    'WotMods'  : 5
}

class Entity(object):
    __logable = { 'path' }
    
    def __init__(self, ID, path=None, parent=None, *args, **kw):
        self._path = None
        
        self.ID     = ID
        self.parent = parent
        self.path   = path
        
        super(Entity, self).__init__()
    
    @property
    def path(self):
        return self._path
    
    @path.setter
    def path(self, path):
        if path:
            self._path = path
    
    @property
    def type(self):
        return self.__class__.__name__

    @property
    def fullpath(self):
        path = self._path
        
        if self.parent is not None:
            path = myjoin(self.parent.fullpath, path)
        
        return path
    
    @property
    def root(self):
        parent = self.parent
        
        while parent:
            parent_parent = parent.parent
            if parent_parent is None:
                return parent
            
            parent = parent_parent
        
        return None
    
    def __eq__(self, entity):
        return type(self) is type(entity)
    
    def create(self):
        pass
    
    def copy(self, new_tree, name=None, move=False):
        pass
    
    def move(self, new_tree, path=None):
        self.copy(new_tree, path, move=True)
    
    def remove(self):
        self.fini()
    
    def log(self, indent=0):
        print_indent(indent, self.type + ':')
        
        for attribute_name in self.logable():
            attribute = getattr(self, attribute_name, None)
            if attribute:
                print_indent(
                    indent+INDENT,
                    attribute_name + ':',
                    attribute
                )
    
    def logable(self):
        return self.__logable
    
    def fini(self):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.fini()
    
    def __del__(self):
        self.fini()

class File(Entity):
    __logable = { 'md5_hash' }
    
    def __init__(self, *args, **kw):
        super(File, self).__init__(*args, **kw)
        
        self.temp = False
        
        self.md5_hash = None
    
    @Entity.path.setter
    def path(self, path):
        Entity.path.fset(self, path)
        self.checkPath()
        
        self.md5_hash = md5(self.open().read()).hexdigest()
    
    def checkPath(self):
        if not exists(self.fullpath):
            self.log()
            
            raise StandardError('%s is not exists'%(fullpath))
    
    def __eq__(self, entity):
        return super(File, self).__eq__(entity) and self.md5_hash == entity.md5_hash
    
    def copy(self, new_tree, path=None, move=False):
        if path is None:
            path = self._path
        
        changed = True
        
        if path in new_tree:
            if self != new_tree[path]:
                del new_tree[path]
            else:
                changed = False
        
        if not changed:
            return
        
        dst_path = myjoin(new_tree.fullpath, path)
        
        if not move:
            shutil.copy2(self.fullpath, dst_path)
        else:
            os.rename(self.fullpath, dst_path)
        
        new_tree[path] = type(self)
        
        if move and self.parent is not None:
            del self.parent[self._path]
        
        return new_tree[path]
    
    def remove(self):
        fullpath = self.fullpath
        if os.path.exists(fullpath):
            os.remove(fullpath)
        
        super(File, self).remove()
    
    # Open file:
    # - For ZIP-archives supports only read mode
    # - For simple files all supported modes
    def open(self, mode='rb', encoding=None):
        root = self.root
        
        if not encoding:
            return open(self.fullpath, mode)
        else:
            return codecs.open(self.fullpath, mode, encoding)
    
    def logable(self):
        return super(File, self).logable() | self.__logable

class Directory(Entity, dict):
    ANALYZE_TYPE = AnalyzeType['Init']
    
    packable_entities = { 'files' }
    logable_entities  = { 'packages', 'wotmod_directories' }
    
    __logable = set()
    
    def __init__(self, *args, **kw):
        super(Directory, self).__init__(*args, **kw)
        
        self.analyze_handlers = {
            AnalyzeType['Init'] : {
                'enabled' : True,
                'handler' : self.__getTree
            },
            AnalyzeType['Packages'] : {
                'enabled' : True,
                'path'    : 'res_mods/mods/xfw_packages/',
                'handler' : self.analyzePackages
            },
            AnalyzeType['Mods'] : {
                'enabled' : True,
                'path'    : 'mods/',
                'handler' : self.analyzeMods,
            },
            AnalyzeType['RawMods'] : {
                'enabled' : False,
                'path'    : 'wotmod/',
                'handler' : self.analyzeMods,
            },
            AnalyzeType['WotMods'] : {
                'enabled' : True,
                'handler' : self.analyzeWotMods
            }
        }
    
    @Entity.path.setter
    def path(self, new_path):
        if not new_path:
            return
        
        if new_path.endswith('/'):
            new_path = new_path[:-1]
        
        old_path = self._path
        new_path = mynormpath(new_path)
        
        if new_path != old_path:
            Entity.path.fset(self, new_path)
            self.__getTree()
    
    def __getParentTree(self, path, onItemNotFound=None, strict=True):
        dirname, basename = mysplit(path)
        directories       = dirname.split('/')
        
        is_file = bool(basename)
        if not is_file:
            basename    = directories[-1]
            directories = directories[:-1]
        
        tree = self
        for directory in directories:
            if not directory or directory == '.':
                continue
            elif directory == '..':
                tree = tree.parent
                if tree is None:
                    return
                
                continue
            
            if directory not in tree:
                if onItemNotFound is not None:
                    onItemNotFound(tree, directory)
                
                if strict:
                    return
            
            tree = tree[directory]
        
        if strict and basename not in tree:
            return None
        
        return (tree, basename, is_file)
    
    def __createDirectory(self, tree, directory):
        tree[directory] = Directory
    
    def __getitem__(self, path):
        result = self.__getParentTree(path)
        if result is not None:
            tree, basename, is_file = result
            
            return super(Directory, tree).__getitem__(basename)
    
    def __setitem__(self, path, value):
        if value is None:
            return
        
        result = self.__getParentTree(path, onItemNotFound=self.__createDirectory, strict=False)
        if result is None:
            return
        
        tree, basename, is_file = result
        
        if type(value) is type:  # classobj
            value_type = value
        else:                    # Instance of some class
            value_type = type(value)
        
        if basename in tree:
            if tree[basename] == value:
                return
            else:
                del tree[basename]
        
        if type(value) is type:
            new_entity = g_EntityFactory.create(
                value_type,
                path=basename,
                parent=tree
            )
            if value_type is Directory:
                new_entity.create()
        else:
            new_entity = value.copy(tree, path=basename)
        
        super(Directory, tree).__setitem__(basename, new_entity)

    def __delitem__(self, path):
        result = self.__getParentTree(path)
        if result is None:
            return
        
        tree, basename, is_file = result
        
        tree[basename].remove()
        
        super(Directory, tree).__delitem__(basename)

    def create(self):
        fullpath = self.fullpath
        if not os.path.exists(fullpath):
            os.mkdir(fullpath)
    
    def copy(self, new_tree, path=None, move=False):
        if not path:
            path = self._path
        
        changed = True
        
        if path in new_tree:
            if self != new_tree[path]:
                del new_tree[path]
            else:
                changed = False
        
        if changed:
            new_tree[path] = type(self)
        
        result = new_tree[path]
        
        for item, subtree in self.iteritems():
            result[item] = subtree
        
        if move and changed and self.parent is not None:
            del self.parent[self._path]
        
        return result
    
    def remove(self):
        fullpath = self.fullpath
        if os.path.exists(fullpath):
            hard_rmtree(fullpath)
        
        super(Directory, self).remove()

    def __printTree(self, tree, indent=0):
        if not tree:
            print_indent(indent+INDENT, 'Empty')
            return
        
        for item, subtree in tree.iteritems():
            print_indent(indent+INDENT, subtree.type, item)
            
            if isinstance(subtree, Directory):
                self.__printTree(subtree, indent=indent+INDENT)
    
    def printTree(self, indent=0):
        print 'Tree', self._path
        
        self.__printTree(self, indent=indent)
    
    def __getTree(self):
        self.clear()
        
        wd = self.fullpath
        
        for item in os.listdir(wd):
            is_file    = os.path.isfile(myjoin(wd, item))
            self[item] = File if is_file else Directory
    
    def analyze(self, analyze_type, path='', indent=0):
        if isinstance(self, File): 
            return
        
        if path and not path.endswith('/'):
            path += '/'
        
        if analyze_type != AnalyzeType['Simple']:
            analyze_data = self.analyze_handlers.get(analyze_type)
            if analyze_data is not None:
                analyze_data['handler'](path, indent=indent)
            
            return
        
        if self.CHECK_MODS:
            if path == self.MODS_DIR:
                self.analyze(
                    AnalyzeType['Mods'],
                    path,
                    indent=indent+INDENT
                )
                return
            elif self.CHECK_RAW_MODS and path == self.RAW_MODS_DIR:
                self[path] = WotModDirectory
                return
        
        if self.CHECK_XFW_PACKAGES and path == self.XFW_PACKAGES_DIR:
            self.analyze(
                AnalyzeType['Packages'],
                path,
                indent=indent+INDENT
            )
            return
        
        # Directory
        if path:
            self[path] = Directory
        
        for item, subtree in self.iteritems():
            subtree.analyze(
                AnalyzeType['Simple'],
                myjoin(path + item),
                indent=indent
            )
    
    def analyzePackages(self, tree, path, indent=0):
        print_debug(indent, 'Analyzing packages...')
        for package_name, package_tree in tree.iteritems():
            self[package_name] = Package
    
    def analyzeMods(self, tree, path, indent=0):
        print_debug(indent, 'Analyzing mods...')
        for patch_name, patch_tree in tree.iteritems():
            if check_patch(patch_name):
                print_indent(indent+INDENT, 'Patch', patch_name)
                
                self[patch_name] = g_EntityFactory.create(
                    WotModDirectory,
                    tree=patch_tree
                )
                continue
            
            self.analyze(
                patch_tree,
                AnalyzeType['Simple'],
                myjoin(path, patch_name),
                indent=indent
            )
    
    def analyzeWotMods(self, tree, path, indent=0):
        print_debug(indent, 'Analyzing wotmods...')
        for wotmod_name, wotmod_tree in tree.iteritems():
            if wotmod_tree is None and wotmod_name.endswith('.wotmod'): # WotMod
                print_indent(indent+INDENT, 'WotMod', wotmod_name)
                self[wotmod_name] = g_EntityFactory.create(
                    WotMod,
                    path=myjoin(path, wotmod_name)
                )
                continue
            
            self.analyze(
                wotmod_tree,
                AnalyzeType['WotMods'],
                myjoin(path, wotmod_name),
                indent=indent+INDENT
            )
    
    def getPackableEntities(self):
        for entity_type in self.packable_entities:
            for entity in self.entities.get(entity_type, {}).values():
                yield entity
    
    def getAllPackableEntities(self):
        for entity in self.getPackableEntities():
            wd = entity.wd
            if entity.type == 'File':
                wd = ''
            yield (wd, entity)
        
        for entity_type in ('packages', 'wotmod_directories'):
            for zip_parent in self.entities.get(entity_type, {}).values():
                for _, entity in zip_parent.getAllPackableEntities():
                    yield (zip_parent.wd, entity)
    
    def log(self, indent=0):
        super(Directory, self).log(indent)
        
        for entities_type in self.logable_entities:
            for entity in self.entities[entities_type].values():
                entity.log(indent+INDENT)
    
    def logable(self):
        return super(Directory, self).logable() | self.__logable
    
    def fini(self):
        for entity in self.values():
            entity.fini()
        
        super(Directory, self).fini()

class ZipArchive(Directory, File):
    COMPRESSION_MODE = ZIP_DEFLATED
    
    __logable = set()
    
    def openIO(self, mode):
        self.closeIO()
        
        self.io = ZipFile(
            myjoin(self.wd, self.path),
            mode,
            self.COMPRESSION_MODE
        )
    
    def extract(self, wd='', *args, **kw):
        self.openIO('r')
        
        for _, entity in self.getAllPackableEntities():
            entity.move(wd, *args, **kw)
        
        self.closeIO()
    
    def pack(self, wd=None):
        if wd is not None:
            self.wd = wd
        
        zip_dir = os.path.dirname(myjoin(self.wd, self.path))
        
        check_wd(zip_dir)
        
        self.openIO('w')
        
        for parent_wd, entity in self.getAllPackableEntities():
            self.io.write(
                myjoin(entity.wd, entity.path),
                myjoin(parent_wd, entity.path)
            )
        
        self.closeIO()
    
    def logable(self):
        return super(ZipArchive, self).logable() | self.__logable

class Archive(ZipArchive):
    IN_DIR  = 'archives/'
    OUT_DIR = 'deploy/'
    
    __logable = { 'name', 'source_dir', 'is_deploy' }
    
    def __init__(self, name, is_deploy, source_dir=None, *args, **kw):
        super(Archive, self).__init__(
            wd=self.OUT_DIR if is_deploy else self.IN_DIR,
            *args,
            **kw
        )
        
        self.name       = name
        self.source_dir = None
        self.is_deploy  = is_deploy
        
        if source_dir:
            self.source_dir = source_dir
        
        self.path = self.getArchivePath()
        if self.path is None:
            self.log()
            raise StandardError('Archive was not found')
        
        if self.is_deploy:
            print 'Creating deploy archive', self.path
        else:
            self.checkPath()
        
        self.openIO('w' if self.is_deploy else 'r')
        
        self.getTree()
        self.analyze(self.tree, AnalyzeType['Simple'])
    
    def getArchivePath(self):
        if not self.is_deploy:
            suffixes = ['']
            if self.source_dir is not None:
                suffixes.append(self.source_dir + '/')
            
            for suffix in suffixes:
                path = suffix + self.name + '.zip'
                if exists(self.wd + path):
                    return path
        else:
            path = ''
            
            if self.source_dir is not None:
                path = myjoin(path, self.source_dir)
            
            check_wd(myjoin(self.wd, path))
            
            path = myjoin(path, self.name + '.zip')
            
            fullpath = myjoin(self.wd, path)
            if exists(fullpath):
                remove(fullpath)
            
            return path
        
        return None
    
    def logable(self):
        return super(ZipArchive, self).logable() | self.__logable

class RawArchive(Archive):
    IN_DIR  = 'raw_archives/'
    OUT_DIR = 'archives/'
    
    CHECK_RAW_MODS = True
    
    __logable = set()
    
    def build_archive(self, mod_name, indent=0):
        print_indent(indent, 'Building mod', mod_name)
        
        wd = myjoin(g_Shared.ARCHIVES_TEMP_DIR, mod_name)
        
        mod_data = g_Shared.raw_archives_config[mod_name]
        
        for _, entity in self.getAllPackableEntities():
            print_debug(indent+INDENT, 'Processing', entity.type)
            
            name = None
            if isinstance(entity, Package):
                name = entity.name
            elif isinstance(entity, WotMod):
                name = entity.meta['name']
            
            if name:
                print_debug(indent+INDENT*2, 'Name:', name)
            
            if isinstance(entity, Package):
                new_meta = entity.meta.copy()
                new_meta.update({
                    'description'     : g_Shared.config[mod_name]['description']['EN'],
                    'wot_version_min' : mod_data['patch']
                })
                
                entity.move(wd, new_meta, temp=False)
            else:
                entity.move(wd, temp=False)
            
            if isinstance(entity, WotMod):
                entity.updateMeta(mod_name)
        
        self.pack(g_Shared.ARCHIVES_DEPLOY_DIR)
    
    def logable(self):
        return super(RawArchive, self).logable() | self.__logable

class Package(Directory):
    CHECK_MODS         = False
    CHECK_RAW_MODS     = False
    CHECK_XFW_PACKAGES = False
    
    logable_entities  = set()
    
    __logable = { 'name', 'meta' }
    
    def __init__(self, name=None, tree=None, *args, **kw):
        super(Package, self).__init__(*args, **kw)
        
        if self.zip_parent:
            self.XFW_PACKAGES_DIR = self.zip_parent.XFW_PACKAGES_DIR
        
        self.entities = {
            'files'       : {},
            'directories' : {}
        }
        
        self.name = name
        self.tree = tree
        self.meta = {}
        
        if not self.wd and not self.name:
            raise StandardError('You must specify wd or name of %s'%(self.type))
        
        if not self.name:
            self.name = os.path.basename(self.wd)
            if not self.name:
                raise StandardError('Unable to init name of %s'%(self.type))
        else:
            self.wd = myjoin(self.wd, self.XFW_PACKAGES_DIR, self.name)
        
        if self.tree is None:
            self.getTree()
        self.log()
        self.analyze(
            self.tree,
            AnalyzeType['Simple'],
            zip_parent=self.zip_parent,
            wd=self.wd
        )
        self.getMeta()
    
    def getMeta(self, indent=0):
        files = self.entities['files']
        if 'xfw_package.json' not in files:
            print_indent(indent, 'Unable to get meta from package:')
            self.log(indent)
            return
        
        with files['xfw_package.json'].open('r', 'utf-8') as meta_file:
            self.meta = json.load(meta_file)
    
    def move(self, wd, new_meta=None, *args, **kw):
        for entity in self.entities['files'].values():
            if new_meta is not None and entity.path == 'xfw_package.json':
                entity.move(
                    wd,
                    data=json.dumps(new_meta, sort_keys=True, indent=4),
                    encoding='utf-8',
                    *args,
                    **kw
                )
                continue
            
            entity.move(wd, *args, **kw)
    
    def logable(self):
        return super(Package, self).logable() | self.__logable

class WotModDirectory(Directory):
    CHECK_MODS         = False
    CHECK_RAW_MODS     = True
    CHECK_XFW_PACKAGES = False
    
    packable_entities = { 'files', 'wotmods' }
    logable_entities  = { 'files', 'wotmods' }
    
    __logable = set()
    
    def __init__(self, wd, tree=None, *args, **kw):
        super(WotModDirectory, self).__init__(wd=wd, *args, **kw)
        
        self.entities = {
            'files'              : {},
            'directories'        : {},
            'wotmod_directories' : {},
            'wotmods'            : {}
        }
        
        if tree is None:
            self.getTree()
        else:
            self.tree = tree
        
        self.analyze(
            self.tree,
            AnalyzeType['WotMods'],
            zip_parent=self.zip_parent,
            wd=self.wd
        )
    
    def move(self, *args, **kw):
        for entity_type in ('files', 'wotmod_directories', 'wotmods'):
            for entity in self.entities[entity_type].values():
                entity.move(*args, **kw)
    
    def logable(self):
        return super(WotModDirectory, self).logable() | self.__logable

class WotMod(ZipArchive):
    XFW_PACKAGES_DIR = 'res/mods/xfw_packages/'
    
    COMPRESSION_MODE = ZIP_STORED
    
    CHECK_MODS = False
    
    __logable = { 'name' }
    
    def __init__(self, path, *args, **kw):
        super(WotMod, self).__init__(path=path, *args, **kw)
        
        if self.zip_parent is not None and self.zip_parent.io is not None:
            self.move()
        
        self.openIO('r')
        
        self.getTree()
        self.analyze(self.tree, AnalyzeType['Simple'])
        
        self.meta = self.getWotmodMeta()
        
        #self.closeIO()
    
    def getWotmodMeta(self):
        files = self.entities['files']
        
        if 'meta.xml' not in files:
            raise StandardError('meta.xml was not found')
        
        with files['meta.xml'].open() as meta_file:
            meta = ET.fromstring(meta_file.read())
            return {
                'id'              : meta[0].text,
                'name'            : meta[2].text,
                'description'     : meta[3].text,
                'version'         : meta[1].text
            }
    
    def updateMeta(self, mod_name, indent=0):
        print_indent(indent, 'Updating meta.xml for wotmod', self.path)
        
        mod_data   = g_Shared.raw_archives_config[mod_name]
        mod_config = g_Shared.config[mod_name]
        
        files = self.entities['files']
        
        if 'meta.xml' not in files:
            raise StandardError('meta.xml was not found')
        
        root = ET.Element('root')
        
        new_id      = ET.SubElement(root, 'id')
        new_name    = ET.SubElement(root, 'name')
        new_desc    = ET.SubElement(root, 'description')
        new_version = ET.SubElement(root, 'version')
        
        new_id.text      = mod_name
        new_name.text    = mod_config['name']['EN']
        new_desc.text    = mod_config['description']['EN']
        new_version.text = self.meta['version']
        
        g_Shared.indent(root)
        tree = ET.ElementTree(root)
        
        self.extract()
        
        with files['meta.xml'].open('wb') as meta_file:
            tree.write(meta_file)
        
        self.pack()
    
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
    
    def logable(self):
        return super(WotMod, self).logable() | self.__logable


class EntityFactory():
    SourceInstanceData = {
        Entity: ('io', 'parent', 'path'),
        
    }
    
    def __init__(self):
        self.maxID = 1
    
    def create(self, cls, source_instance=None, **kw):
        if source_instance is not None:
            for field in self.SourceInstanceFields:
                kw[field] = getattr(source_instance, field)
        
        instance = cls(ID=self.maxID, **kw)
        
        self.maxID += 1
        
        return instance

g_EntityFactory = EntityFactory()

def create_deploy(wd, src_dir, name, folder_path, del_folder=True, isRaw=False):
    cls     = RawArchive if isRaw else Archive
    out_zip = g_EntityFactory.create(cls, name, True, source_dir=src_dir)
    chdir(wd)
    zip_folder(folder_path, out_zip.io)
    if del_folder:
        hard_rmtree(folder_path)
    chdir(get_reversed_path(wd))
    out_zip.closeIO()