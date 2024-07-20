import gi
from gi.repository import GObject

import contextlib
import functools

def add_emission_stopper(signal_name):
    def wrapper(f):
        @functools.wraps(f)
        def new_f(self, obj, *args, **kwargs):
            try:
                if obj._stop_emission == signal_name:
                    GObject.signal_stop_emission_by_name(obj, signal_name)
            except AttributeError:
                return f(self, obj, *args, **kwargs)
        return new_f
    return wrapper

@contextlib.contextmanager
def stop_emission(obj, signal):
    obj._stop_emission = signal
    yield
    del obj._stop_emission

