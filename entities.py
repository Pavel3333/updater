import codecs
import sys

from zipfile   import ZipFile, ZIP_STORED, ZIP_DEFLATED
from xml.etree import ElementTree as ET
from hashlib import md5

from common import *

class AnalyzeType:
    Simple   = 0
    Packages = 1
    Mods     = 2
    WotMods  = 3

class EntityFactory():
    def __init__(self):
        self.maxID = 1
    
    def create(self, cls, *args, **kw):
        instance = cls(ID=self.maxID, *args, **kw)
        self.maxID += 1
        
        return instance

g_EntityFactory = EntityFactory()

class Entity(object):
    TYPE = 'Entity'
    
    __logable = { 'wd', 'path' }
    
    def __init__(self, ID, path=None, io=None, wd=None, zip_parent=None, *args, **kw):
        self.ID = ID
        
        self.io   = io
        self.wd   = '' if wd   is None else wd
        self.path = '' if path is None else path
        
        self.zip_parent = zip_parent
    
    def existsIO(self, path):
        #opened = self.io is not None
        #if not opened:
        #    if hasattr(self, 'openIO'):
        #        self.openIO('r')
        #    else:
        #        return False
        
        #result = path in self.io.namelist()
        
        #if not opened:
        #    self.closeIO()
        
        return self.io is not None and path in self.io.namelist()
    
    def closeIO(self):
        if self.io is not None:
            self.io.close()
            self.io = None
    
    def log(self, indent=0):
        print_indent(indent, self.TYPE + ':')
        
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
        self.closeIO()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.fini()
    
    def __del__(self):
        self.fini()

class File(Entity):
    TYPE = 'File'
    
    CHECK_HASH = True
    
    __logable = { 'md5_hash' }
    
    def __init__(self, path=None, *args, **kw):
        super(File, self).__init__(path=path, *args, **kw)
        
        self.temp = False
        
        self.md5_hash = None
        
        if path:
            self.setPath(path)
    
    def checkPath(self, path=None):
        if path is None:
            path = self.path
        
        fullpath = myjoin(self.wd, path)
        
        if  self.existsIO(fullpath)                                    or \
            self.zip_parent is not None and self.zip_parent.existsIO(fullpath) or \
            exists(fullpath):
            return
            
        raise StandardError(
            '%s is not exists (wd: %s, path: %s)\nparent:%s'%(self.TYPE, self.wd, path, getattr(self.zip_parent, 'TYPE', None)))
    
    def setPath(self, path):
        self.checkPath(path)
        self.path = path
        
        if self.CHECK_HASH:
            self.md5_hash = md5(self.open().read()).hexdigest()
    
    # Open file:
    # - For ZIP-archives supports only read mode
    # - For simple files all supported modes
    def open(self, mode='rb', encoding=None):
        fullpath = myjoin(self.wd, self.path)
        
        if self.io is not None:
            return self.io.open(fullpath, mode[0])
        elif self.zip_parent is not None and self.zip_parent.io is not None:
            return self.zip_parent.io.open(fullpath, mode[0])
        else:
            if not encoding:
                return open(fullpath, mode)
            else:
                return codecs.open(fullpath, mode, encoding)
    
    def write(self, data):
        fullpath = myjoin(self.wd, self.path)
        
        if self.io is not None:
            self.io.writestr(fullpath, data)
        elif self.zip_parent is not None and self.zip_parent.io is not None:
            self.zip_parent.io.writestr(fullpath, data)
        else:
            with open(fullpath, 'wb') as file_object:
                file_object.write(data)
    
    def move(self, wd='', hard=True, temp=True, data=None, encoding=None):
        if temp:
            ID = self.zip_parent.ID if self.zip_parent is not None else self.ID
            wd = myjoin(g_Shared.TEMP_DIR, str(ID))
        
        src_path = myjoin(self.wd, self.path)
        
        if self.temp:
            self.wd = ''
        
        self.wd = myjoin(wd, self.wd)
        
        dst_path = myjoin(self.wd, self.path)
        dst_dir  = os.path.dirname(dst_path)
        
        check_wd(dst_dir)
        
        if exists(dst_path):
            remove(dst_path)
        
        if data is None:
            if self.zip_parent is not None and self.zip_parent.io is not None: # Inside the archive
                self.zip_parent.io.extract(src_path, wd)
            else:
                if hard:
                    self.closeIO()
                    
                    rename(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
        else:
            if not encoding:
                dst_file = open(dst_path, 'wb')
            else:
                dst_file = codecs.open(dst_path, 'w', encoding)
            
            dst_file.write(data)
            dst_file.close()
        
        self.zip_parent = None
        
        if temp:
            g_Shared.delete_after_fini.add(wd)
        else:
            self.clean(src_path)
        
        self.temp = temp
    
    def clean(self, path=None):
        if path is None:
            path = myjoin(self.wd, self.path)
        
        if self.temp and exists(path):
            pass
            #remove(path)
    
    def fini(self):
        super(File, self).fini()
        
        self.clean()
    
    def logable(self):
        return super(File, self).logable() | self.__logable

class Directory(Entity):
    TYPE = 'Directory'
    
    MODS_DIR         = 'mods/'
    RAW_MODS_DIR     = 'wotmod/'
    XFW_PACKAGES_DIR = 'res_mods/mods/xfw_packages/'
    
    CHECK_MODS         = True
    CHECK_RAW_MODS     = False
    CHECK_XFW_PACKAGES = True
    
    packable_entities = { 'files' }
    logable_entities  = { 'packages', 'wotmod_directories' }
    
    __logable = set()
    
    def __init__(self, *args, **kw):
        super(Directory, self).__init__(*args, **kw)
        
        self.entities = {
            'files'              : {},
            'directories'        : {},
            'packages'           : {},
            'wotmod_directories' : {}
        }
        
        self.tree = {}
    
    def getTreeFromPath(self, path):
        dirname, basename = os.path.split(path)
        
        directories = dirname.split('/')
        tree = self.tree
        for directory in directories:
            if not directory:
                continue
            
            if directory not in tree:
                tree[directory] = {}
            
            tree = tree[directory]
        
        if basename: # File
            tree[basename] = None
    
    def getTreeFromIO(self, io):
        for path in io.namelist():
            self.getTreeFromPath(path)
    
    def getTree(self):
        self.tree = {}
        
        if self.io is not None:
            self.getTreeFromIO(self.io)
        elif self.zip_parent is not None and self.zip_parent.io is not None:
            self.getTreeFromIO(self.zip_parent.io)
        else:
            wd = myjoin(self.wd, self.path)
            for root, dirs, files in os.walk(wd):
                for path in files:
                    relpath = os.path.relpath(myjoin(root, path), wd).replace('\\', '/')
                    self.getTreeFromPath(relpath)
    
    def analyze(self, tree, analyze_type, zip_parent=None, wd='', path='', indent=0):
        if zip_parent is None:
            zip_parent = self
        
        if tree is None: # File
            self.entities['files'][path] = g_EntityFactory.create(
                File,
                wd=wd, 
                path=path,
                zip_parent=zip_parent
            )
            return
        
        if path and not path.endswith('/'):
            path += '/'
        
        if analyze_type == AnalyzeType.Packages:
            self.analyzePackages(tree, zip_parent, wd, path, indent=indent)
        elif analyze_type == AnalyzeType.Mods:
            self.analyzeMods(tree, zip_parent, wd, path, indent=indent)
        elif analyze_type == AnalyzeType.WotMods:
            self.analyzeWotMods(tree, zip_parent, wd, path, indent=indent)
        elif analyze_type == AnalyzeType.Simple:
            if self.CHECK_MODS:
                if path == self.MODS_DIR:
                    self.analyze(
                        tree,
                        AnalyzeType.Mods,
                        zip_parent,
                        wd,
                        path,
                        indent=indent+INDENT
                    )
                    return
                elif self.CHECK_RAW_MODS and path == self.RAW_MODS_DIR:
                    self.entities['wotmod_directories'][path] = g_EntityFactory.create(
                        WotModDirectory,
                        wd=myjoin(wd, path),
                        tree=tree,
                        zip_parent=zip_parent
                    )
                    return
            
            if self.CHECK_XFW_PACKAGES and path == self.XFW_PACKAGES_DIR:
                self.analyze(
                    tree,
                    AnalyzeType.Packages,
                    zip_parent,
                    wd,
                    path,
                    indent=indent+INDENT
                )
                return
            
            # Directory
            if path:
                self.entities['directories'][path] = g_EntityFactory.create(
                    Directory,
                    wd=wd,
                    path=path,
                    zip_parent=zip_parent
                )
            
            for item, subtree in tree.iteritems():
                self.analyze(
                    subtree,
                    AnalyzeType.Simple,
                    zip_parent,
                    wd,
                    myjoin(path + item),
                    indent=indent
                )
    
    def analyzePackages(self, tree, zip_parent, wd, path, indent=0):
        print_debug(indent, 'Analyzing packages...')
        for package_name, package_tree in tree.iteritems():
            self.entities['packages'][package_name] = g_EntityFactory.create(
                Package,
                wd=wd,
                name=package_name,
                tree=package_tree,
                zip_parent=zip_parent
            )
    
    def analyzeMods(self, tree, zip_parent, wd, path, indent=0):
        print_debug(indent, 'Analyzing mods...')
        for patch_name, patch_tree in tree.iteritems():
            if check_patch(patch_name):
                print_indent(indent+INDENT, 'Patch', patch_name)
                
                self.entities['wotmod_directories'][patch_name] = g_EntityFactory.create(
                    WotModDirectory,
                    wd=myjoin(wd, path, patch_name),
                    tree=patch_tree,
                    zip_parent=zip_parent
                )
                continue
            
            self.analyze(
                patch_tree,
                AnalyzeType.Simple,
                zip_parent,
                wd,
                myjoin(path, patch_name),
                indent=indent
            )
    
    def analyzeWotMods(self, tree, zip_parent, wd, path, indent=0):
        print_debug(indent, 'Analyzing wotmods...')
        for wotmod_name, wotmod_tree in tree.iteritems():
            if wotmod_tree is None and wotmod_name.endswith('.wotmod'): # WotMod
                print_indent(indent+INDENT, 'WotMod', wotmod_name)
                self.entities['wotmods'][wotmod_name] = g_EntityFactory.create(
                    WotMod,
                    wd=wd,
                    path=myjoin(path, wotmod_name),
                    zip_parent=zip_parent
                )
                continue
            
            self.analyze(
                wotmod_tree,
                AnalyzeType.WotMods,
                zip_parent,
                wd,
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
            if entity.TYPE == 'File':
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
        for entities in self.entities.values():
            for entity in entities.values():
                entity.fini()
        
        super(Directory, self).fini()

class ZipArchive(Directory, File):
    TYPE = 'ZipArchive'
    
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
    TYPE = 'Archive'
    
    IN_DIR  = 'archives/'
    OUT_DIR = 'deploy/'
    
    CHECK_HASH = False
    
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
            self.checkPath(self.path)
        
        self.openIO('w' if self.is_deploy else 'r')
        
        self.getTree()
        self.analyze(self.tree, AnalyzeType.Simple)
    
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
    TYPE = 'RawArchive'
    
    IN_DIR  = 'raw_archives/'
    OUT_DIR = 'archives/'
    
    CHECK_RAW_MODS = True
    
    __logable = set()
    
    def build_archive(self, mod_name, indent=0):
        print_indent(indent, 'Building mod', mod_name)
        
        wd = myjoin(g_Shared.ARCHIVES_TEMP_DIR, mod_name)
        
        mod_data = g_Shared.raw_archives_config[mod_name]
        
        for _, entity in self.getAllPackableEntities():
            print_debug(indent+INDENT, 'Processing', entity.TYPE)
            
            name = None
            if entity.TYPE == 'Package':
                name = entity.name
            elif entity.TYPE == 'WotMod':
                name = entity.meta['name']
            
            if name:
                print_debug(indent+INDENT*2, 'Name:', name)
            
            if entity.TYPE == 'Package':
                new_meta = entity.meta.copy()
                new_meta.update({
                    'description'     : g_Shared.config[mod_name]['description']['EN'],
                    'wot_version_min' : mod_data['patch']
                })
                
                entity.move(wd, new_meta, temp=False)
            else:
                entity.move(wd, temp=False)
            
            if entity.TYPE == 'WotMod':
                entity.updateMeta(mod_name)
        
        self.pack(g_Shared.ARCHIVES_DEPLOY_DIR)
    
    def logable(self):
        return super(RawArchive, self).logable() | self.__logable

class Package(Directory):
    TYPE = 'Package'
    
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
            raise StandardError('You must specify wd or name of %s'%(self.TYPE))
        
        if not self.name:
            self.name = os.path.basename(self.wd)
            if not self.name:
                raise StandardError('Unable to init name of %s'%(self.TYPE))
        else:
            self.wd = myjoin(self.wd, self.XFW_PACKAGES_DIR, self.name)
        
        if self.tree is None:
            self.getTree()
        self.log()
        self.analyze(
            self.tree,
            AnalyzeType.Simple,
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
    TYPE = 'WotModDirectory'
    
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
            AnalyzeType.WotMods,
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
    TYPE = 'WotMod'
    
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
        self.analyze(self.tree, AnalyzeType.Simple)
        
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

def create_deploy(wd, src_dir, name, folder_path, del_folder=True, isRaw=False):
    cls     = RawArchive if isRaw else Archive
    out_zip = g_EntityFactory.create(cls, name, True, source_dir=src_dir)
    chdir(wd)
    zip_folder(folder_path, out_zip.io)
    if del_folder:
        hard_rmtree(folder_path)
    chdir(get_reversed_path(wd))
    out_zip.closeIO()