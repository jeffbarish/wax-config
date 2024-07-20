"""Main program for waxconfig."""

import signal

import logging
#logging.basicConfig(level=logging.WARNING,
logging.basicConfig(level=logging.ERROR,
        format='%(levelname)s:%(module)s:%(message)s')

import gi
gi.require_version('Gio', '2.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, Gio

from common.constants import MAIN_WINDOW_SIZE
from common.utilities import debug
from common.types import RecordingTuple, WorkTuple, TrackTuple
from topbox import top_box

class WaxConfig(Gtk.Window):
    def __init__(self):
        super().__init__()
        self.set_title('Wax Config')
        self.set_default_size(*MAIN_WINDOW_SIZE)
        self.connect_after('destroy', self.on_destroy)

        signal.signal(signal.SIGINT, self.on_signal)

        screen = Gdk.Screen.get_default()
        gtk_provider = Gtk.CssProvider()
        gtk_context = Gtk.StyleContext()
        gtk_context.add_provider_for_screen(screen, gtk_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        css_file = Gio.File.new_for_path('wax.css')
        gtk_provider.load_from_file(css_file)

        self.add(top_box)

    def on_destroy(self, window):
        self.quit()

    def on_signal(self, signal, frame):
        self.quit()

    def quit(self):
        Gtk.main_quit()

wax_config = WaxConfig()
wax_config.show()
Gtk.main()

