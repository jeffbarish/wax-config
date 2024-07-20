import os
import pickle
import shelve
import shutil
from pathlib import Path

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib

import common.checkpoint as checkpoint
from emissionstopper import add_emission_stopper, stop_emission
from genrespec import genre_spec
from operations import operations
from common.constants import METADATA, LONG, SHORT, NOEXPAND
from common.constants import SOUND, IMAGES, DOCUMENTS
from common.utilities import debug
from common.utilities import config
from common.utilities import make_unique
from undobox import undo_box

DEFAULT_GENRE = 'New_genre'
DEFAULT_KEY = 'new_key'
CONFIG_SECTIONS = ('column widths', 'filter config', 'random config',
                'sort indicators')

@Gtk.Template.from_file('glade/genres.glade')
class GenresBox(Gtk.Box):
    __gtype_name__ = 'genres_box'

    genre_treeview = Gtk.Template.Child()
    genre_liststore = Gtk.Template.Child()
    genre_treeselection = Gtk.Template.Child()
    delete_genre_button = Gtk.Template.Child()
    genre_scrolledwindow = Gtk.Template.Child()

    keys_box = Gtk.Template.Child()

    keys_primary_treeview = Gtk.Template.Child()
    keys_primary_liststore = Gtk.Template.Child()
    keys_primary_treeselection = Gtk.Template.Child()
    delete_key_primary_button = Gtk.Template.Child()

    keys_secondary_treeview = Gtk.Template.Child()
    keys_secondary_liststore = Gtk.Template.Child()
    keys_secondary_treeselection = Gtk.Template.Child()
    delete_key_secondary_button = Gtk.Template.Child()

    buttons_sizegroup = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self.tab_text = 'Genres'
        self.set_name('genres-page')
        self.previous_height = 0
        self.genre = None

        primary_liststore = self.keys_primary_liststore
        secondary_liststore = self.keys_secondary_liststore
        primary_liststore.metadata_class = 'primary'
        secondary_liststore.metadata_class = 'secondary'

        self.models = {'primary': primary_liststore,
                'secondary': secondary_liststore}

        self.delete_genre_button.set_sensitive(False)

        flags = Gtk.TargetFlags.SAME_APP
        # Drag primary -> secondary
        self.keys_primary_treeview.enable_model_drag_source(
                Gdk.ModifierType.BUTTON1_MASK,
                [Gtk.TargetEntry.new('key', flags, 0)],
                Gdk.DragAction.MOVE)
        self.keys_secondary_treeview.enable_model_drag_dest(
                [Gtk.TargetEntry.new('key', flags, 0)],
                Gdk.DragAction.MOVE)
        # Drag secondary -> primary
        self.keys_secondary_treeview.enable_model_drag_source(
                Gdk.ModifierType.BUTTON1_MASK,
                [Gtk.TargetEntry.new('key', flags, 0)],
                Gdk.DragAction.MOVE)
        self.keys_primary_treeview.enable_model_drag_dest(
                [Gtk.TargetEntry.new('key', flags, 0)],
                Gdk.DragAction.MOVE)

        # Populate genre liststore.
        self.populate()

    def populate(self):
        genre_liststore = self.genre_liststore
        genre_treeselection = self.genre_treeselection
        with (stop_emission(genre_treeselection, 'changed'),
                stop_emission(genre_liststore, 'row-deleted')):
            genre_liststore.clear()
        for genre in genre_spec:
            genre_liststore.append((genre,))

        # Re-select the current genre, if it still exists.
        if self.genre is not None:
            for row in genre_liststore:
                if row[0] == self.genre:
                    genre_treeselection.select_iter(row.iter)
                    break
            else:
                # self.genre is no longer in genre_liststore.
                self.delete_genre_button.set_sensitive(False)
                self.keys_box.hide()
                self.genre = None

    @Gtk.Template.Callback()
    @add_emission_stopper('changed')
    def on_genre_treeselection_changed(self, selection):
        model, treeiter = selection.get_selected()

        # Hiding keys_box and showing it later gets it to
        # resize so that its contents are visible.
        self.keys_box.hide()

        if treeiter is not None:
            self.genre = genre = model.get_value(treeiter, 0)

            for liststore in self.models.values():
                liststore.clear()

            if genre in genre_spec: # could be a new genre
                liststore = self.models['primary']
                keys = config.genre_spec[genre]['primary']
                column_widths = config.column_widths[genre]
                filter_buttons = [False] * len(keys)
                for fb in config.filter_config[genre]:
                    filter_buttons[fb] = True
                if genre not in config.sort_indicators:
                    sort_indicators = [False] * len(keys)
                else:
                    sort_indicators = config.sort_indicators[genre]

                for k, cw, fb, cs in \
                        zip(keys, column_widths, filter_buttons, sort_indicators):
                    with stop_emission(liststore, 'row-changed'):
                        liststore.append([k, cw, fb, True, cs])

                liststore = self.models['secondary']
                for key in config.genre_spec[genre]['secondary']:
                    liststore.append((key,))

            self.delete_genre_button.set_sensitive(True)
            self.delete_key_primary_button.hide()
            self.delete_key_secondary_button.hide()
            GLib.idle_add(self.keys_box.show)
        else:
            self.delete_genre_button.set_sensitive(False)
            self.keys_box.hide()
            self.genre = None

    # When the scrolledwindow resizes, keep the selected row visible. I get
    # size-allocate whenever the scrolledwindow scrolls, in which case the
    # allocation does not actually change. Do scroll_to_cell only when the
    # allocation actually changes.
    @Gtk.Template.Callback()
    def on_genre_scrolledwindow_size_allocate(self,
                scrolledwindow, allocation):
        if allocation.height != self.previous_height:
            selection = self.genre_treeselection
            model, treeiter = selection.get_selected()
            if treeiter is not None:
                treepath = model.get_path(treeiter)
                treeview = self.genre_treeview
                GLib.idle_add(treeview.scroll_to_cell,
                        treepath, None, True, 0.5, 0.0)
                self.previous_height = allocation.height

    # -Genre operations--------------------------------------------------------
    @Gtk.Template.Callback()
    def on_add_genre_button_clicked(self, liststore):
        genres = next(zip(*liststore))
        new_genre = make_unique(DEFAULT_GENRE, genres)

        self._push_checkpoint('Added genre', new_genre)

        new_row_iter = liststore.append((new_genre,))

        selection = self.genre_treeselection
        GLib.idle_add(selection.select_iter, new_row_iter)

        genre_spec.add_genre(new_genre, DEFAULT_KEY)

        # If the files do not exist, create them.
        with (open(LONG, 'ab') as fo_long,
                open(Path(SHORT, new_genre), 'ab') as fo_short):
            pass

        for section, val in (('column widths', [80]),
                ('filter config', []), ('random config', [0, False]),
                ('sort indicators', [True])):
            with config.modify(section) as spec:
                spec[new_genre] = val

    @Gtk.Template.Callback()
    def on_delete_genre_button_clicked(self, selection):
        model, treeiter = selection.get_selected()
        del_genre = model.get_value(treeiter, 0)

        # Warn if short exists and has nonzero size.
        try:
            warning = bool(os.path.getsize(Path(SHORT, del_genre)))
        except OSError:
            warning = False

        if warning:
            dialog = DeleteDialog(del_genre)
            dialog.set_transient_for(self.get_toplevel())
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.NO:
                return

        self._push_checkpoint('Deleted genre', del_genre)

        with (stop_emission(selection, 'changed'),
                stop_emission(model, 'row-deleted')):
            model.remove(treeiter)
        genre_spec.delete_genre(del_genre)

        Path(SHORT, del_genre).unlink(missing_ok=True)

        for section in CONFIG_SECTIONS:
            with config.modify(section) as spec:
                del spec[del_genre]

        self.delete_genre_in_long(del_genre)

        selection.unselect_all()
        self.keys_box.hide()

        # Create a new genre. Save a recording in the new genre. Go back to
        # WaxConfig and Undo create a new genre. The new genre short file
        # disappears because it did not exist prior to the checkpoint.
        # Likewise, long gets restored. However, the new directories in
        # sound, documents, and images persist. Moral: do not do this.

    @Gtk.Template.Callback()
    def on_name_cellrenderertext_edited(self, cellrenderertext, path, text):
        new_genre = text.strip()
        model = self.genre_liststore

        # If new_genre is already in model, abort.
        if new_genre in (name for name, in model):
            return

        old_genre, = model[path]

        model[path] = (new_genre,)

        self._push_checkpoint('Renamed genre', old_genre, 'to', new_genre)

        genre_spec.rename_genre(old_genre, new_genre)
        self.genre = new_genre

        # Rename short and long metadata files.
        orig_file = Path(METADATA, 'short', old_genre)
        orig_file.rename(Path(METADATA, 'short', new_genre))

        # Rename entries in config.
        for section in CONFIG_SECTIONS:
            with config.modify(section) as spec:
                spec[new_genre] = spec.pop(old_genre)

        self.rename_genre_in_long(old_genre, new_genre)

    @Gtk.Template.Callback()
    def on_genre_liststore_row_inserted(self, model, treepath, treeiter):
        self.insertion_at_path = treepath

    @Gtk.Template.Callback()
    @add_emission_stopper('row-deleted')
    def on_genre_liststore_row_deleted(self, model, treepath):
        # The user reordered rows in the treeview.
        new_index = self.insertion_at_path[0]
        if treepath[0] < self.insertion_at_path[0]:
            new_index -= 1
        genre, = model[new_index]

        self._push_checkpoint('Moved genre', genre, 'to position', new_index+1)

        genre_spec.reorder_genres(g for g, in model)

    @Gtk.Template.Callback()
    @add_emission_stopper('row-inserted')
    def on_keys_primary_liststore_row_inserted(self, model, treepath, treeiter):
        if len(model) == 1:
            model[0][2] = False
            model[0][3] = False
            model[0][4] = True
        elif len(model) > 1:
            for row in model:
                row[3] = True

    @Gtk.Template.Callback()
    def on_keys_primary_liststore_row_deleted(self, model, treepath):
        if len(model) == 1:
            model[0][2] = False
            model[0][3] = False
            model[0][4] = True

    def rename_genre_in_long(self, old_genre, new_genre):
        if not os.path.getsize(LONG):
            return
        TMP = str(LONG) + '.tmp'
        with shelve.open(LONG, 'r') as recording_shelf, \
                shelve.open(TMP, 'n') as tmp_shelf:
            for uuid, recording in recording_shelf.items():
                new_works = {}
                for i, work in recording.works.items():
                    if work.genre == old_genre:
                        work = work._replace(genre=new_genre)
                    new_works[i] = work
                tmp_shelf[uuid] = recording._replace(works=new_works)
        Path(TMP).rename(LONG)

    def delete_genre_in_long(self, genre):
        if not os.path.getsize(LONG):
            return
        TMP = str(LONG) + '.tmp'
        with shelve.open(LONG, 'r') as recording_shelf, \
                shelve.open(TMP, 'n') as tmp_shelf:
            for uuid, recording in recording_shelf.items():
                new_i, new_works = (0, {})
                for i, work in recording.works.items():
                    if work.genre != genre:
                        new_works[new_i] = work
                        new_i += 1
                if len(new_works):
                    tmp_shelf[uuid] = recording._replace(works=new_works)
                else:
                    for path in (SOUND, IMAGES, DOCUMENTS):
                        shutil.rmtree(Path(path, uuid), ignore_errors=True)
        Path(TMP).rename(LONG)


    # -Key operations----------------------------------------------------------
    # There are two treeviews, one for primary and one for secondary. However,
    # the handlers are generic.
    @Gtk.Template.Callback()
    def on_keys_treeselection_changed(self, selection):
        delete_button = {
                self.keys_primary_treeselection:
                    self.delete_key_primary_button,
                self.keys_secondary_treeselection:
                    self.delete_key_secondary_button}[selection]
        is_secondary = selection is self.keys_secondary_treeselection
        model, treeiter = selection.get_selected()
        delete_button.props.visible = treeiter is not None \
                and (len(model) > 1 or is_secondary)

    # I specified user data to get the corresponding treeview instead of the
    # button.
    @Gtk.Template.Callback()
    def on_add_key_button_clicked(self, treeview):
        model = treeview.get_model()
        selection = treeview.get_selection()

        is_primary = (model.metadata_class == 'primary')

        # new_key must be unique in both primary and secondary.
        all_keys = genre_spec.all_keys(self.genre)
        new_key = make_unique(DEFAULT_KEY, all_keys)

        self._push_checkpoint('Added key', new_key,
                'to', model.metadata_class, 'in genre', self.genre)

        if is_primary:
            new_column_width, widths = self.steal_widths(self.genre)

            new_row = (new_key, new_column_width, False, True, False)

            for row, width in zip(model, widths):
                model[row.iter][1] = width
        else:
            new_row = (new_key,)
        new_row_iter = model.append(new_row)
        GLib.idle_add(selection.select_iter, new_row_iter)

        self.update_config_from_models(self.genre)
        self.adjust_metadata_files(operations['add_key'], locals())

    @Gtk.Template.Callback()
    def on_delete_key_button_clicked(self, treeview):
        selection = treeview.get_selection()
        model, treeiter = selection.get_selected()

        # These two variables are used in operation delete_key.
        all_keys = genre_spec.all_keys(self.genre)
        is_primary = (model.metadata_class == 'primary')

        del_key = model[treeiter][0]
        model.remove(treeiter)

        self._push_checkpoint('Deleted key', del_key,
                'from', model.metadata_class, 'in genre', self.genre)

        self.update_config_from_models(self.genre)
        self.adjust_metadata_files(operations['delete_key'], locals())

    # I specified user data to get the corresponding model instead of the
    # cellrenderertext.
    @Gtk.Template.Callback()
    def on_keys_cellrenderertext_edited(self, model, path, text):
        new_key = text.strip()
        if not new_key.isidentifier():
            undo_box.show_error_message('Invalid key', new_key)
            return

        # If new_key is already in the genre, abort.
        all_keys = genre_spec.all_keys(self.genre)
        if new_key in all_keys:
            return

        old_key = model[path][0]

        self._push_checkpoint('Renamed key', old_key, 'to', new_key,
                'in genre', self.genre)

        # Replace old_key with new_key.
        model[path][0] = new_key

        self.update_config_from_models(self.genre)
        self.adjust_metadata_files(operations['rename_key'], locals())

    @Gtk.Template.Callback()
    def on_keys_treeview_drag_data_get(self,
            treeview, context, data, info, time):
        selection = treeview.get_selection()
        model, treeiter = selection.get_selected()
        row = model[treeiter]
        cargo = pickle.dumps(tuple(row))
        data.set(data.get_selection(), 8, cargo)

        GLib.idle_add(selection.unselect_all)

    @Gtk.Template.Callback()
    def on_keys_primary_treeview_drag_data_received(self,
            treeview, context, x, y, data, info, time):
        key, *params = source_row = pickle.loads(data.get_data())
        if not params:
            params = [0, False, True, False]
        drop_row = [key] + params
        drop_iter = self._place_drop(treeview, x, y, drop_row)

        # Delete the original row in the source treeview.
        context.finish(True, True, time)

        model = treeview.get_model()
        path = model.get_path(drop_iter)

        if key in config.genre_spec[self.genre]['primary']:
            self.rearrange_primary(self.genre, model, key, path[0])
        else:
            self.promote_secondary(self.genre, key, path[0])

        # Select the new row in the dest treeview.
        selection = treeview.get_selection()
        selection.select_iter(drop_iter)

    def promote_secondary(self, genre, key, insert_index):
        all_keys = genre_spec.all_keys(genre)
        from_index = all_keys.index(key)

        self._push_checkpoint('Promoted key', key,
                'to primary in position', insert_index+1, 'in', genre)

        new_column_width, widths = self.steal_widths(genre)
        self.keys_primary_liststore[insert_index][1] = new_column_width

        # Update all width values.
        for row, width in zip(self.keys_primary_liststore, widths):
            row[1] = width

        self.update_config_from_models(genre)
        self.adjust_metadata_files(operations['promote_secondary'], locals())

    def rearrange_primary(self, genre, model, key, insert_index):
        primary_keys = config.genre_spec[genre]['primary']
        from_index = primary_keys.index(key)

        if from_index == insert_index:
            return

        self._push_checkpoint('Moved primary key', key,
                'to position', insert_index+1, 'in', genre)

        self.update_config_from_models(genre)
        self.adjust_metadata_files(operations['rearrange_primary'], locals())

    @Gtk.Template.Callback()
    def on_keys_secondary_treeview_drag_data_received(self,
            treeview, context, x, y, data, info, time):
        key, *params = source_row = pickle.loads(data.get_data())
        drop_row = [key]
        drop_iter = self._place_drop(treeview, x, y, drop_row)

        # Delete the original row in the source treeview.
        context.finish(True, True, time)

        # Select the new row in the dest treeview.
        selection = treeview.get_selection()
        selection.select_iter(drop_iter)

        path = treeview.props.model.get_path(drop_iter)

        secondary_keys = config.genre_spec[self.genre]['secondary']
        if key in secondary_keys:
            model = treeview.get_model()
            self.rearrange_secondary(self.genre, model, key, path[0])
        else:
            self.demote_primary(self.genre, key, path[0])

    def demote_primary(self, genre, key, insert_index):
        # The first elements of long_metadata correspond to primary
        # keys, so the index of key in primary_keys is the index of
        # the desired value in long_metadata.
        primary_keys = config.genre_spec[genre]['primary']
        from_index = primary_keys.index(key)

        self._push_checkpoint('Demoted key', key,
                'to secondary in position', insert_index+1, 'in', genre)

        self.update_config_from_models(genre)
        self.adjust_metadata_files(operations['demote_primary'], locals())

    def rearrange_secondary(self, genre, model, key, insert_index):
        primary_keys = config.genre_spec[genre]['primary']
        secondary_keys = config.genre_spec[genre]['secondary']
        from_index = secondary_keys.index(key)

        if from_index == insert_index:
            return

        self._push_checkpoint('Moved secondary key', key,
                'to position', insert_index+1, 'in', genre)

        self.update_config_from_models(genre)
        self.adjust_metadata_files(operations['rearrange_secondary'], locals())

    @Gtk.Template.Callback()
    def on_sort_indicator_cellrenderertoggle_toggled(self, cell, pathstr):
        model = self.keys_primary_liststore

        self._push_checkpoint('Changed sort column for key',
                model[pathstr][0], 'in', self.genre)

        new_sort = not model[pathstr][4]
        for row in self.keys_primary_liststore:
            self.keys_primary_liststore[row.iter][4] = False
        if new_sort:
            self.keys_primary_liststore[pathstr][4] = True

        # If no row has sort_indicator set, set it on row 0.
        if not any(self.keys_primary_liststore[row.iter][4]
                for row in self.keys_primary_liststore):
            self.keys_primary_liststore[0][4] = True

        self.update_config_from_models(self.genre)

    @Gtk.Template.Callback()
    def on_filter_button_cellrenderertoggle_toggled(self, cell, pathstr):
        model = self.keys_primary_liststore

        self._push_checkpoint('Changed filter button state for key',
                model[pathstr][0], 'in', self.genre)

        new_button = not model[pathstr][2]
        self.keys_primary_liststore[pathstr][2] = new_button

        # If the number of unchecked toggles is 1, desensitize that one
        # as it is forbidden to convert every column to a filter button.
        n_not_filter_buttons = sum(1 for row in model if not row[2])
        for row in model:
            if n_not_filter_buttons == 1 and not row[2]:
                row[3] = False
            else:
                row[3] = True

        self.update_config_from_models(self.genre)

    @Gtk.Template.Callback()
    def on_column_width_cellrenderertext_edited(self, cell, pathstr, text):
        model = self.keys_primary_liststore

        new_width = int(text)

        self._push_checkpoint('Changed column width for key',
                model[pathstr][0], 'in', self.genre)

        self.keys_primary_liststore[pathstr][1] = new_width

        self.update_config_from_models(self.genre)

    def update_config_from_models(self, genre):
        keys_p, widths, filters, _, sorts = zip(*self.keys_primary_liststore)
        try:
            keys_s, = zip(*self.keys_secondary_liststore)
        except ValueError:
            keys_s = ()
        filter_config = filter(lambda f: filters[f], range(len(filters)))

        new_specs = {
            'genre spec': {'primary': list(keys_p), 'secondary': list(keys_s)},
            'column widths': list(widths),
            'filter config': list(filter_config),
            'sort indicators': list(sorts)}
        for category, val in new_specs.items():
            with config.modify(category) as spec:
                spec.update({genre: val})

    def _place_drop(self, treeview, x, y, source_row):
        model = treeview.get_model()
        drop_info = treeview.get_dest_row_at_pos(x, y)
        if drop_info:
            path, position = drop_info
            dest_iter = model.get_iter(path)
            if position == Gtk.TreeViewDropPosition.BEFORE:
                drop_iter = model.insert_before(dest_iter, source_row)
            else:
                drop_iter = model.insert_after(dest_iter, source_row)
        else:
            drop_iter = model.append(source_row)
        return drop_iter

    def _push_checkpoint(self, *args):
        comment = checkpoint.make_comment(*args)
        checkpoint.push_checkpoint(comment)
        undo_box.undo_label.set_markup(comment)
        undo_box.undo_button.set_sensitive(True)

    def adjust_metadata_files(self, func, local_vars):
        if not os.path.getsize(str(LONG)):
            return

        if not os.path.getsize(LONG):
            return
        short_file_path = Path(SHORT, self.genre)
        tmp_file_path = short_file_path.with_suffix('.tmp')
        with (shelve.open(LONG, 'c') as recording_shelf,
                open(short_file_path, 'rb') as fo_short,
                open(tmp_file_path, 'wb') as fo_tmp):
            while True:
                try:
                    short_metadata, uuid, work_num = pickle.load(fo_short)
                except EOFError:
                    break

                func(list(short_metadata), recording_shelf, uuid, work_num,
                        fo_tmp, local_vars)

        # If func put something in tmp_file_path, presumably it was destined
        # to be renamed short_file_path.
        if os.path.getsize(tmp_file_path):
            tmp_file_path.rename(short_file_path)
        else:
            tmp_file_path.unlink()

    def steal_widths(self, genre):
        new_column_width = 50
        min_column_width = 30
        widths = config.column_widths[genre]
        total = 0
        while total < new_column_width:
            if all(w == min_column_width for w in widths):
                new_column_width = min_column_width
                break
            for i, width in enumerate(widths):
                if width > min_column_width:
                    widths[i] -= 1
                    total += 1
        return new_column_width, widths

    def recover_width(self, genre, from_index):
        widths = config.column_widths[genre]
        recovered_width = widths.pop(from_index)
        while recovered_width > 0:
            for i, width in enumerate(widths):
                widths[i] += 1
                if not (recovered_width := recovered_width - 1):
                    break
        return widths

class DeleteDialog(Gtk.Dialog):
    def __init__(self, del_genre):
        super().__init__()
        self.vbox.set_spacing(12)
        self.vbox.set_margin_start(6)
        self.vbox.set_margin_end(6)

        label1 = Gtk.Label.new(None)
        label1.set_markup(
            '<span size="larger">Genre '
            f'<span foreground="#009185" font="monospace">{del_genre}</span> '
            'has at least one work.</span>')
        label1.set_line_wrap(True)
        label1.set_justify(Gtk.Justification.CENTER)
        label1.set_margin_top(6)
        label1.show()

        label2 = Gtk.Label.new(None)
        label2.set_label(
            'You will lose those works if you proceed. If one of those\n'
            'works is the last in the recording, you will also lose the\n'
            'sound files, images, and documents.')
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


page_widget = GenresBox()

