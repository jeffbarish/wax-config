import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk

import common.checkpoint as checkpoint
from common.utilities import config
from common.utilities import debug
from emissionstopper import stop_emission
from undobox import undo_box

@Gtk.Template.from_file('glade/parameters.glade')
class ParametersBox(Gtk.Box):
    __gtype_name__ = 'parameters_box'

    geometry_liststore = Gtk.Template.Child()
    geometry_treeselection = Gtk.Template.Child()
    trackmetadata_keys_delete_button = Gtk.Template.Child()
    trackmetadata_keys_treeselection = Gtk.Template.Child()
    trackmetadata_keys_liststore = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self.tab_text = 'Parameters'
        self.set_name('parameters-page')

        self.populate()

        # import pickle
        # from common.constants import CONFIG
        # with open(CONFIG, 'rb') as config_fo:
        #     config = pickle.load(config_fo)
        # config['geometry'] = config['parameters']
        # with open(CONFIG, 'wb') as config_fo:
        #     pickle.dump(config, config_fo)

    def populate(self):
        geometry_liststore = self.geometry_liststore
        geometry_treeselection = self.geometry_treeselection
        with stop_emission(geometry_treeselection, 'changed'):
            geometry_liststore.clear()
        for key in ['window_width',
                'window_height',
                'right_panel_width',
                'selector_paned_position',
                'import_paned_position']:
            geometry_liststore.append((key, config.geometry[key]))

        trackmetadata_keys_liststore = self.trackmetadata_keys_liststore
        trackmetadata_keys_liststore.clear()
        for key in config.trackmetadata_keys:
            trackmetadata_keys_liststore.append((key,))

    # -Geometry----------------------------------------------------------------
    @Gtk.Template.Callback()
    def on_geometry_key_cellrendererspin_edited(self, renderer, path, text):
        key, old_value = self.geometry_liststore[path]

        new_value = int(text)
        if new_value == old_value:
            return

        self._push_checkpoint('Changed dimension', key, 'to', new_value)

        self.geometry_liststore[path] = (key, new_value)

        with config.modify('geometry') as geometry:
            geometry[key] = new_value

    @Gtk.Template.Callback()
    def on_geometry_defaults_button_clicked(self, button):
        self._push_checkpoint('Restored default dimensions')

        config.geometry = {'window_width': 800,
                'window_height': 480,
                'right_panel_width': 341,
                'selector_paned_position': 254,
                'import_paned_position': 160}
        self.geometry_liststore.clear()
        self.populate()

    # -Trackmetadata keys------------------------------------------------------
    @Gtk.Template.Callback()
    def on_trackmetadata_keys_add_button_clicked(self, button):
        model = self.trackmetadata_keys_liststore
        keys = [row[0] for row in model]

        new_key, i = ('new_key', 1)
        while new_key in keys:
            new_key, i = (f'new_key_{i}', i + 1)
        model.append((new_key,))

        self._push_checkpoint('Added key', new_key, 'to trackmetadata keys')

        with config.modify('trackmetadata keys') as trackmetadata_keys:
            trackmetadata_keys.append(new_key)

    @Gtk.Template.Callback()
    def on_trackmetadata_keys_delete_button_clicked(self, button):
        selection = self.trackmetadata_keys_treeselection
        model, treeiter = selection.get_selected()

        key, = model[treeiter]

        self._push_checkpoint('Deleted key', key, 'from trackmetadata keys')

        del model[treeiter]

        with config.modify('trackmetadata keys') as trackmetadata_keys:
            trackmetadata_keys.remove(key)

    @Gtk.Template.Callback()
    def on_trackmetadata_keys_treeselection_changed(self, selection):
        model, treeiter = selection.get_selected()
        sensitive = treeiter is not None
        self.trackmetadata_keys_delete_button.set_sensitive(sensitive)

    @Gtk.Template.Callback()
    def on_trackmetadata_keys_renderertext_edited(self, cell, path, text):
        model = self.trackmetadata_keys_liststore
        old_key, = model[path]

        model[path] = (text,)

        self._push_checkpoint('Changed key', old_key, 'to', text,
                'in trackmetadata keys')

        with config.modify('trackmetadata keys') as trackmetadata_keys:
            trackmetadata_keys[int(path[0])] = text

    def _push_checkpoint(self, *args):
        comment = checkpoint.make_comment(*args)
        checkpoint.push_checkpoint(comment)
        undo_box.undo_label.set_markup(comment)
        undo_box.undo_button.set_sensitive(True)


page_widget = ParametersBox()

