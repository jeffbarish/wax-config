import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from common.utilities import debug, tracer
from notebook import notebook
from undobox import undo_box

class TopBox(Gtk.Box):
    __gtype_name__ = 'topbox'

    def __init__(self):
        super().__init__()
        self.set_name('topbox')
        self.show()

        self.set_orientation(Gtk.Orientation.VERTICAL)

        self.pack_start(notebook, True, True, 0)
        self.pack_end(undo_box, False, False, 0)


top_box = TopBox()

