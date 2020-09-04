import os
import json

from os.path import exists, join

from new_common   import *
from new_entities import *

RESOURCES_WD = 'resources/'

g_Tree = g_EntityFactory.create(
    Directory,
    path=RESOURCES_WD
)

g_Tree.printTree()

"""
class Parser(object):
    def __init__(self):
        self.raw_archives = {}

        self.fail_raw_archives = set()
        
        if exists(g_Shared.TEMP_DIR):
            hard_rmtree(g_Shared.TEMP_DIR)

        self.analyze()
        self.build_archives()
        
    def analyze(self, indent=0):
        print_indent(indent, 'Analyzing raw archives...')
        for mod_name, mod_data in g_Shared.raw_archives_config.iteritems():
            print_indent(indent+INDENT, 'Raw archive', mod_name)
            archive = self.raw_archives[mod_name] = g_EntityFactory.create(RawArchive, mod_name, False)
            archive.log()
            
            if 'packages' in mod_data:
                config_packages = set(mod_data['packages'])
                real_packages   = set(archive.entities['packages'].keys())
                
                not_found_packages = config_packages - real_packages
                new_packages       = real_packages   - config_packages

                if not_found_packages:
                    print_indent(indent, 'Packages not found:')
                    for package_name in not_found_packages:
                        print_indent(indent+INDENT+INDENT, package_name)
                    
                    self.fail_raw_archives.add(mod_name)

                if new_packages:
                    print_indent(indent, 'New packages:')
                    for package_name in new_packages:
                        print_indent(indent+INDENT+INDENT, package_name)

    def build_archives(self, indent=0):
        if exists(g_Shared.ARCHIVES_TEMP_DIR):
            hard_rmtree(g_Shared.ARCHIVES_TEMP_DIR)

        if exists(g_Shared.ARCHIVES_DEPLOY_DIR):
            hard_rmtree(g_Shared.ARCHIVES_DEPLOY_DIR)
        
        print_indent(indent, 'Building raw archives...')
        for mod_name, mod_data in g_Shared.raw_archives_config.iteritems():
            if mod_name in self.fail_raw_archives:
                print_indent(indent+INDENT, 'Item analysis failed')
                continue

            archive = self.raw_archives[mod_name]
            archive.build_archive(mod_name)

    def fini(self):
        for raw_archive in self.raw_archives.values():
            raw_archive.fini()

        if exists(g_Shared.TEMP_DIR):
            hard_rmtree(g_Shared.TEMP_DIR)

    def __del__(self):
        self.fini()

g_Parser = Parser()

print '------ DONE ------'

del g_Parser
"""
