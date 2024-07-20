import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango

from common.utilities import debug, tracer

@Gtk.Template.from_file('glade/undo.glade')
class UndoBox(Gtk.Box):
    __gtype_name__ = 'undo_box'

    undo_button = Gtk.Template.Child()
    undo_label = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self.set_name('undo-box')
        self.set_margin_bottom(3)
        self.set_margin_left(3)
        self.undo_label.set_ellipsize(Pango.EllipsizeMode.END)

    def show_error_message(self, error_message, value):
        undo_label = self.undo_label.get_label()
        def restore_undo():
            self.undo_label.set_markup(undo_label)
            self.undo_button.show()

        self.undo_button.hide()
        markup1 = f'<span foreground="red">{error_message}</span>'
        markup2= f'<span foreground="#009185">{value}</span>'
        self.undo_label.set_markup(f'{markup1} {markup2}')

        GLib.timeout_add_seconds(3, restore_undo)


undo_box = UndoBox()
