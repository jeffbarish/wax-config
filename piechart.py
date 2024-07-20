"""Present data in a pie chart. The data are in the form of (fraction, color),
where fraction is the fraction of the pie and color is a tuple of (r, g, b)
for that slice of the pie."""

import cmath
import math

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject

from common.utilities import debug

TWO_PI = 2 * math.pi

class PieChart(Gtk.EventBox):
    @GObject.Signal
    def clicked(self, zone: int):
        pass

    def __init__(self, data):
        super().__init__()
        self.show()

        drawing_area = Gtk.DrawingArea.new()
        self.add(drawing_area)

        self.data = data
        self.angles = [d * TWO_PI for d, color in data]

    def do_draw(self, context):
        alloc = self.get_allocation()
        size = min(alloc.width, alloc.height)

        context.translate(size / 2.0, size / 2.0)
        context.scale(size * 0.9, size * 0.9)

        total_arc = 0.0
        for data, color in self.data:
            context.set_source_rgb(*color)
            context.move_to(0.0, 0.0)
            new_arc = -data * math.pi * 2.0 # counterclockwise from +x axis
            context.arc_negative(0.0, 0.0, 0.5, total_arc, total_arc + new_arc)
            context.move_to(0.0, 0.0)
            context.fill()
            total_arc += new_arc

        return False

    def do_button_press_event(self, event):
        if event.type == Gdk.EventType.BUTTON_PRESS \
                and event.state == 0 \
                and event.button == 1:
            alloc = self.get_allocation()
            size = min(alloc.width, alloc.height)

            c_origin = complex(size / 2.0, size / 2.0)
            c_button_press = complex(int(event.x), int(event.y))
            r, phi = cmath.polar(c_button_press - c_origin)

            # Return if button press outside the circle.
            if r > 0.5 * size * 0.9:
                return

            # Adjust phi to be 0 -> 2*pi counter-clockwise from x axis
            # (instead of 0 -> -pi for the top half and 0 -> pi for the
            # bottom).
            phi = -phi
            if phi < 0.0:
                phi = TWO_PI + phi

            total = 0.0
            for i, a in enumerate(self.angles):
                total += a
                if total > phi:
                    self.emit('clicked', i)
                    break

