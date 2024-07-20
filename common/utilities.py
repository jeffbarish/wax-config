import contextlib
import logging
import os
import pickle
import sys
from collections import namedtuple
from functools import wraps
from inspect import currentframe, getframeinfo
from pathlib import Path
from pprint import pformat

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from common.constants import CONFIG

class Config:
    def __init__(self):
        with open(CONFIG, 'rb') as config_fo:
            # Like self.config = pickle.load(config_fo).
            self.__dict__['config'] = pickle.load(config_fo)

    # After undo, Config needs to reread the pickle.
    def reread(self):
        self.__init__()

    # Support access either as attribute (config.attr_name)
    # or item (config['attr name']).
    def __getattr__(self, attr):
        key = attr.replace('_', ' ')
        val = self.__dict__['config'].get(key, {})
        return val

    def __setattr__(self, attr, val):
        key = attr.replace('_', ' ')
        self.__dict__['config'][key] = val
        with open(CONFIG, 'wb') as config_fo:
            pickle.dump(self.__dict__['config'], config_fo)

    def __getitem__(self, key):
        val = self.__dict__['config'].get(key, {})
        return val

    def __setitem__(self, key, val):
        self.__dict__['config'][key] = val
        with open(CONFIG, 'wb') as config_fo:
            pickle.dump(self.__dict__['config'], config_fo)

    def __str__(self):
        return pformat(self.__dict__['config'])

    # Yield the mutable specification for key. After the main program modifies
    # the specification, write it back to config to trigger a write to disk.
    @staticmethod
    @contextlib.contextmanager
    def modify(key):
        spec = config[key]
        yield spec
        config[key] = spec

config = Config()

def debug(arg, comment=''):
    if comment:
        comment += ': '
    frame = sys._getframe(1)
    value = eval(arg, frame.f_globals, frame.f_locals)
    print(f'{comment}{arg} = {repr(value)} ({type(value)})')

# Decorator to trace execution of methods -- handlers, typically. Note that
# tracer should come after add_emission_stopper because the latter might
# prevent the function from running.
def tracer(f):
    @wraps(f)
    def new_f(*args, **kwargs):
        frameinfo = getframeinfo(currentframe().f_back)
        filename = Path(frameinfo.filename).name
        lineno = frameinfo.lineno
        print(f'TRACER: Executing function {f.__name__} '
                f'at {filename}:{lineno}')
        #logging.info(f'Executing function {f.__name__}')
        try:
            return f(*args, **kwargs)
        finally:
            print(f'TRACER: Done executing function {f.__name__}')
        #return f(*args, **kwargs)
    return new_f

NULLVALUE = ('',)
class Value(namedtuple('Value', ['long', 'short'])):
    __slots__ = ()

    def __add__(self, other):
        if other.long == NULLVALUE:
            return self
        elif self.long == NULLVALUE:
            return other
        else:
            return Value(self.long + other.long, self.short + other.short)

# If text is already in model, append a number to make the resulting
# string unique.
def make_unique(text, existing_text):
    unique_text = text
    if unique_text in existing_text:
        i = 1
        while (unique_text := f'{text}_{i}') in existing_text:
            i += 1
    return unique_text

