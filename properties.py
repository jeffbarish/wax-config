"""This module displays controls for dealing with genres."""

import shelve
import shutil
from pathlib import Path

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GLib

import common.checkpoint as checkpoint
from common.constants import SHORT, LONG, NOEXPAND
from common.utilities import debug
from common.utilities import make_unique
from common.utilities import config
from emissionstopper import stop_emission
from undobox import undo_box

DEFAULT_PROPERTY = 'new_property'

@Gtk.Template.from_file('glade/properties.glade')
class PropertiesBox(Gtk.Box):
    __gtype_name__ = 'properties_box'

    properties_liststore = Gtk.Template.Child()
    properties_treeselection = Gtk.Template.Child()
    delete_property_button = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self.tab_text = 'Properties'
        self.set_name('properties-page')

        self.connect('realize', self.on_realize)

        # Populate prop liststore.
        self.populate()

    def populate(self):
        properties_liststore = self.properties_liststore
        properties_treeselection = self.properties_treeselection
        with (stop_emission(properties_treeselection, 'changed'),
                stop_emission(properties_liststore, 'row-deleted')):
            properties_liststore.clear()
        for prop in config.user_props:
            properties_liststore.append((prop,))

    @Gtk.Template.Callback()
    def on_add_property_button_clicked(self, liststore):
        try:
            properties = next(zip(*liststore))
        except StopIteration:
            properties = ()
            config.user_props = []
        add_prop = make_unique(DEFAULT_PROPERTY, properties)

        self._push_checkpoint('Added property', add_prop)

        liststore.append((add_prop,))

        last_row = liststore[-1]
        selection = self.properties_treeselection
        GLib.idle_add(selection.select_iter, last_row.iter)

        with config.modify('user props') as user_props:
            user_props.append(add_prop)

        self.add_property_in_long(add_prop)

    @Gtk.Template.Callback()
    def on_delete_property_button_clicked(self, selection):
        model, treeiter = selection.get_selected()
        del_prop = model.get_value(treeiter, 0)

        # Check to see whether del_prop has a value assigned in any recording.
        # If so, warn with a dialog before proceeding with deletion.
        found_value = False
        with shelve.open(LONG, 'r') as recording_shelf:
            for uuid, recording in recording_shelf.items():
                props_dict = dict(recording.props)
                if any(props_dict.get(del_prop, ('',))):
                    found_value = True
                    break

        if found_value:
            dialog = PropDialog(del_prop)
            dialog.set_transient_for(self.get_toplevel())
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.NO:
                return

        self._push_checkpoint('Deleted property', del_prop)

        with (stop_emission(selection, 'changed'),
                stop_emission(model, 'row-deleted')):
            model.remove(treeiter)

        with config.modify('user props') as user_props:
            user_props.remove(del_prop)

        self.delete_property_in_long(del_prop)

    @Gtk.Template.Callback()
    def on_name_cellrenderertext_edited(self, model, path, text):
        new_prop = text.strip()

        # If new_prop is already in model, abort.
        if new_prop in (name for name, in model):
            return

        old_prop, = model[path]

        model[path] = (new_prop,)

        self._push_checkpoint('Renamed property', old_prop, 'to', new_prop)

        config.user_props = [prop if prop != old_prop else new_prop
                for prop in config.user_props]

        self.rename_property_in_long(old_prop, new_prop)

    @Gtk.Template.Callback()
    def on_properties_treeselection_changed(self, selection):
        model, treeiter = selection.get_selected()
        self.delete_property_button.props.sensitive = (treeiter is not None)

    # The first row is selected initially.
    def on_realize(self, arg):
        GLib.idle_add(self.properties_treeselection.unselect_all)

    def add_property_in_long(self, add_prop):
        TMP = str(LONG) + '.tmp'
        with shelve.open(LONG, 'r') as recording_shelf, \
                shelve.open(TMP, 'n') as tmp_shelf:
            for uuid, recording in recording_shelf.items():
                props_dict = dict(recording.props)
                if add_prop in props_dict: # should not happen
                    tmp_shelf[uuid] = recording
                    continue
                props_dict[add_prop] = ('',)
                new_props = list(props_dict.items())
                tmp_shelf[uuid] = recording._replace(props=new_props)
        Path(TMP).rename(LONG)

    def delete_property_in_long(self, del_prop):
        TMP = str(LONG) + '.tmp'
        with shelve.open(LONG, 'c') as recording_shelf, \
                shelve.open(TMP, 'n') as tmp_shelf:
            for uuid, recording in recording_shelf.items():
                props_dict = dict(recording.props)
                try:
                    del props_dict[del_prop]
                except KeyError:
                    continue
                new_props = list(props_dict.items())
                tmp_shelf[uuid] = recording._replace(props=new_props)
        Path(TMP).rename(LONG)

    def rename_property_in_long(self, old_prop, new_prop):
        TMP = str(LONG) + '.tmp'
        with shelve.open(LONG, 'r') as recording_shelf, \
                shelve.open(TMP, 'n') as tmp_shelf:
            for uuid, recording in recording_shelf.items():
                props_dict = dict(recording.props)
                props_dict[new_prop] = props_dict[old_prop]
                del props_dict[old_prop]
                new_props = list(props_dict.items())
                tmp_shelf[uuid] = recording._replace(props=new_props)
        Path(TMP).rename(LONG)

    def _push_checkpoint(self, *args):
        comment = checkpoint.make_comment(*args)
        checkpoint.push_checkpoint(comment)
        undo_box.undo_label.set_markup(comment)
        undo_box.undo_button.set_sensitive(True)

class PropDialog(Gtk.Dialog):
    def __init__(self, del_prop):
        super().__init__()
        self.vbox.set_spacing(12)

        label1 = Gtk.Label.new(None)
        label1.set_markup(
            '<span size="larger">User property '
            f'<span foreground="#009185" font="monospace">{del_prop}</span> '
            'has a value\nassigned in at least one recording.</span>')
        label1.set_line_wrap(True)
        label1.set_justify(Gtk.Justification.CENTER)
        label1.set_margin_start(3)
        label1.set_margin_end(3)
        label1.set_margin_top(6)
        label1.show()

        label2 = Gtk.Label.new(None)
        label2.set_label(
            'You will lose all values if you delete the property.')
        label2.set_justify(Gtk.Justification.CENTER)
        label2.show()

        label3 = Gtk.Label.new(None)
        label3.set_label('Proceed anyway?')
        label3.show()

        self.vbox.pack_start(label1, *NOEXPAND)
        self.vbox.pack_start(label2, *NOEXPAND)
        self.vbox.pack_start(label3, *NOEXPAND)

        button = self.add_button('Yes', Gtk.ResponseType.YES)
        button.set_can_focus(False)
        button = self.add_button('No', Gtk.ResponseType.NO)
        button.set_can_focus(False)


page_widget = PropertiesBox()

