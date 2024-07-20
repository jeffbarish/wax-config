import os
import pickle
import shelve
from collections import defaultdict
from datetime import datetime
from operator import itemgetter
from pathlib import Path

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk

from genrespec import genre_spec
from piechart import PieChart
from common.constants import SHORT, LONG
from common.utilities import config
from common.utilities import debug

N_ITEMS = 50

@Gtk.Template.from_file('glade/info.glade')
class InfoBox(Gtk.Box):
    __gtype_name__ = 'info_box'

    total_works_label = Gtk.Template.Child()
    total_recs_label = Gtk.Template.Child()
    number_of_works_liststore = Gtk.Template.Child()
    date_played_liststore = Gtk.Template.Child()
    date_created_liststore = Gtk.Template.Child()
    times_played_liststore = Gtk.Template.Child()
    number_of_works_hbox = Gtk.Template.Child()
    number_of_works_color_treeviewcolumn = Gtk.Template.Child()
    number_of_works_color_cellrenderertext = Gtk.Template.Child()
    number_of_works_treeselection = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        self.tab_text = 'Info'
        self.set_name('info-page')

        self.count_works()
        self.list_by_props()

        def func(column, cell, model, treeiter, *data):
            color = Gdk.RGBA(*model[treeiter][2])
            cell.props.cell_background_rgba = color
        col = self.number_of_works_color_treeviewcolumn
        cell = self.number_of_works_color_cellrenderertext
        col.set_cell_data_func(cell, func)

    def count_works(self):
        nworks_by_genre = defaultdict(int)
        for genre in genre_spec:
            short_file_path = Path(SHORT, genre)
            if not short_file_path.exists():
                continue
            with open(short_file_path, 'rb') as fo_short:
                while True:
                    try:
                        pickle.load(fo_short)
                    except EOFError:
                        break
                    nworks_by_genre[genre] += 1

        # Sort by count.
        nworks_by_genre = dict(sorted(nworks_by_genre.items(),
                key=itemgetter(1), reverse=True))

        total_works = sum(nworks_by_genre.values())
        self.total_works_label.set_text(f'Total works: {total_works}')

        # Start at Wax green (#009185) and get darker.
        color = (0.0, 0x91 / 256.0, 0x85 / 256.0)
        ratio = .95 # the rate at which the color gets darker

        self.number_of_works_liststore.clear()
        piechart_data = []
        for genre, count in nworks_by_genre.items():
            self.number_of_works_liststore.append((genre, count, color))

            fraction = float(count) / float(total_works)
            piechart_data.append((fraction, color))

            color = tuple(c * ratio for c in color)

        pie_chart = PieChart(piechart_data)
        pie_chart.connect('clicked', self.on_pie_chart_clicked)
        self.number_of_works_hbox.pack_end(pie_chart, True, True, 0)

    def on_pie_chart_clicked(self, piechart, zone):
        self.number_of_works_treeselection.select_path(zone)

    def list_by_props(self):
        n_recs = 0
        props_list = []
        if not os.path.getsize(LONG):
            self.total_recs_label.set_text(f'(from 0 recordings)')
            return
        with shelve.open(LONG, 'r') as recording_shelf:
            for recording in recording_shelf.values():
                n_recs += 1
                for work in recording.works.values():
                    props_d = dict(recording.props)
                    date_played = props_d['date played'][0]
                    date_created = props_d['date created'][0]
                    times_played = props_d['times played'][0]

                    metadata = work.metadata
                    keys = config.genre_spec[work.genre]['primary']
                    description = '\n'.join(', '.join(name_group)
                            for key, name_group in zip(keys, metadata))

                    row = (date_played, date_created, times_played, work.genre, description)
                    props_list.append(row)
        self.total_recs_label.set_text(f'(from {n_recs} recordings)')

        def sort_by_date_played(x):
            return datetime.strptime(x[0], "%Y %b %d") \
                    if x[0] else datetime.min
        props_list.sort(key=sort_by_date_played, reverse=True)
        date_played_getter = itemgetter(0, 3, 4)
        for item in props_list[:N_ITEMS]:
            self.date_played_liststore.append(date_played_getter(item))

        def sort_by_date_created(x):
            return datetime.strptime(x[1], "%Y %b %d") \
                    if x[1] else datetime.min
        props_list.sort(key=sort_by_date_created, reverse=True)
        date_played_getter = itemgetter(1, 3, 4)
        for item in props_list[:N_ITEMS]:
            self.date_created_liststore.append(date_played_getter(item))

        def sort_by_times_played(x):
            return int(x[2]) if x[2] else 0
        props_list.sort(key=sort_by_times_played, reverse=True)
        times_played_getter = itemgetter(2, 3, 4)
        for item in props_list[:N_ITEMS]:
            self.times_played_liststore.append(times_played_getter(item))


page_widget = InfoBox()

