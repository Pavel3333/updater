# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: ./JSONxLoader/__init__.py
# Compiled at: 2019-10-06 04:02:22
__author__ = 'Alex'
from loader import JSONxLoaderException

def load(file_path, log_func=None):
    import loader
    config_loader = loader.JSONxLoader(file_path, log_func)
    return config_loader.load()
