"""This module displays controls for dealing with genres."""

from pathlib import Path
from subprocess import Popen
from threading import Thread

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GLib

import common.checkpoint as checkpoint
from common.constants import COMPLETERS
from common.utilities import config
from common.utilities import debug
from common.utilities import make_unique
from undobox import undo_box

DEFAULT_COMPLETER = 'new_completer'

@Gtk.Template.from_file('glade/completers.glade')
class CompletersBox(Gtk.Box):
    __gtype_name__ = 'completers_box'

    completers_treeview = Gtk.Template.Child()
    completers_treeselection = Gtk.Template.Child()
    completers_liststore = Gtk.Template.Child()
    delete_completer_button = Gtk.Template.Child()
    edit_completer_button = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self.tab_text = 'Completers'
        self.set_name('completers-page')

        self.populate()

        self.connect('realize', self.on_realize)

    # The first row is selected initially.
    def on_realize(self, arg):
        GLib.idle_add(self.completers_treeselection.unselect_all)

    @Gtk.Template.Callback()
    def on_learn_cellrenderertoggle_toggled(self, cell, pathstr):
        key, enabled, learn, n_names = self.completers_liststore[pathstr]
        self.completers_liststore[pathstr] = (key, enabled, not learn, n_names)
        with config.modify('completers') as completers:
            completers[key] = (enabled, not learn)

    @Gtk.Template.Callback()
    def on_enabled_cellrenderertoggle_toggled(self, cell, pathstr):
        key, enabled, learn, n_names = self.completers_liststore[pathstr]
        self.completers_liststore[pathstr] = (key, not enabled, learn, n_names)
        with config.modify('completers') as completers:
            completers[key] = (not enabled, learn)

    @Gtk.Template.Callback()
    def on_add_completer_button_clicked(self, liststore):
        keys = next(zip(*liststore))
        new_completer = make_unique(DEFAULT_COMPLETER, keys)

        self._push_checkpoint('Added completer', new_completer)

        # Update liststore.
        row = (new_completer, True, True, 0)
        self.completers_liststore.append(row)

        # Create the completer file.
        with open(Path(COMPLETERS, new_completer), 'w') as completer_fo:
            pass

        # Update config.
        with config.modify('completers') as completers:
            completers[new_completer] = (True, True)

        # Re-populate to sort names.
        GLib.idle_add(self.populate)

    @Gtk.Template.Callback()
    def on_edit_completer_button_clicked(self, selection):
        model, treeiter = selection.get_selected()
        edit_completer = model[treeiter][0]

        def run_popen_in_thread(popen_args):
            process = Popen(popen_args)
            process.wait()

            # Update n_names.
            GLib.idle_add(self.populate)

        completer_fn = Path(COMPLETERS, edit_completer)
        thread = Thread(target=run_popen_in_thread,
                args=(['xdg-open', completer_fn],)) # or kwrite
        thread.daemon = True
        thread.start()

    @Gtk.Template.Callback()
    def on_delete_completer_button_clicked(self, selection):
        model, treeiter = selection.get_selected()
        del_completer = model[treeiter][0]
        self._push_checkpoint('Deleted completer', del_completer)

        self.completers_liststore.remove(treeiter)

        Path(COMPLETERS, del_completer).unlink()

        with config.modify('completers') as completers:
            del completers[del_completer]

    @Gtk.Template.Callback()
    def on_completers_treeselection_changed(self, selection):
        model, treeiter = selection.get_selected()
        sensitive = (treeiter is not None)
        self.delete_completer_button.props.sensitive = sensitive
        self.edit_completer_button.props.sensitive = sensitive

    @Gtk.Template.Callback()
    def on_key_cellrenderertext_edited(self, model, path, new_name):
        old_name = model[path][0]
        if new_name == old_name:
            return

        self._push_checkpoint('Renamed completers for', old_name,
                'to', new_name)

        with config.modify('completers') as completers:
            completers[new_name] = completers[old_name]
            del completers[old_name]

        Path(COMPLETERS, old_name).rename(Path(COMPLETERS, new_name))

        # Re-populate to sort names.
        GLib.idle_add(self.populate)

    def populate(self):
        self.completers_liststore.clear()

        # Check for inconsistency between config and the contents of the
        # completers directory.
        completer_files = sorted(p.name for p in Path(COMPLETERS).iterdir())
        config_keys = set(config['completers'].keys())
        del_keys = config_keys.difference(completer_files)
        if del_keys:
            del_mess = ', '.join(del_keys)
            with config.modify('completers') as completers:
                for key in del_keys:
                    del completers[key]
            message = f'completer file for {del_keys} not found. Deleted ' \
                    f'from config'
            s = 's' if len(del_keys) > 1 else ''
            message = f'delete key{s} {del_mess} from config — ' \
                    f'no completer file{s}'
            self.display_warning(message)
        for completer_file in completer_files:
            if completer_file not in config['completers']:
                # deal with multiple files here
                message = f'created entry in config corresponding to ' \
                        f'file {completer_file}'
                self.display_warning(message)
                with config.modify('completers') as completers:
                    completers[completer_file] = True

        for completer_file in sorted(Path(COMPLETERS).iterdir()):
            with open(completer_file, 'r') as completer_fo:
                lines = completer_fo.readlines()
            key = completer_file.name
            enabled, learn = config.completers[key]
            n_names = len(lines)
            row = (key, enabled, learn, n_names)
            self.completers_liststore.append(row)

    def display_warning(self, message):
        markup = f'<span foreground="#dc143c">{message}</span>'
        GLib.idle_add(undo_box.undo_label.set_markup, markup)
        GLib.timeout_add_seconds(5, undo_box.undo_label.set_text, '')

    def _push_checkpoint(self, *args):
        comment = checkpoint.make_comment(*args)
        checkpoint.push_checkpoint(comment)
        undo_box.undo_label.set_markup(comment)
        undo_box.undo_button.set_sensitive(True)


page_widget = CompletersBox()

