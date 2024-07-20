"""This module is for configuring Wax."""

import importlib

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

import common.checkpoint as checkpoint
from commandline import args
from common.utilities import debug, tracer
from common.utilities import config
from undobox import undo_box

@Gtk.Template.from_file('glade/notebook.glade')
class Notebook(Gtk.Notebook):
    __gtype_name__ = 'notebook'

    def __init__(self):
        super().__init__()
        self.set_name('notebook')

        # pages will map the name of the page to the page.
        self.pages = pages = {}.fromkeys(['genres', 'properties',
                'completers', 'parameters', 'info'])

        # Import the modules for pages of the notebook. They are located
        # in the 'pages' subdirectory.
        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.VERTICAL)
        for page_module_name in pages:
            module_name = f'{page_module_name}'
            page = importlib.import_module(module_name)
            page_widget = page.page_widget
            self.append_page(page_widget)
            self.set_tab_label_text(page_widget, page_widget.tab_text)
            label = self.get_tab_label(page_widget)
            label.set_angle(90)
            label.set_padding(0, 3)
            pages[page_module_name] = page
            size_group.add_widget(label)

        undo_box.undo_button.connect('clicked', self.on_undo_button_clicked)

        # Check for command line option to suppress deletion of checkpoints.
        if args.preserve:
            comment = checkpoint.update_comment()
            undo_box.undo_label.set_markup(comment)
            undo_box.undo_button.set_sensitive(bool(comment))
        else:
            checkpoint.remove_checkpoints()

    def do_switch_page(self, page, page_num):
        undo_box.props.visible = (page_num in [0, 1, 2, 3])
        if not undo_box.props.visible:
            print('Hiding undo_box in notebook.py on page', page_num)

        Gtk.Notebook.do_switch_page(self, page, page_num)

    def on_undo_button_clicked(self, button):
        comment = checkpoint.pop_checkpoint()
        undo_box.undo_label.set_markup(comment)
        undo_box.undo_button.set_sensitive(bool(comment))

        config.reread()

        for page in self.get_children():
            if hasattr(page, 'populate'):
                page.populate()


notebook = Notebook()
