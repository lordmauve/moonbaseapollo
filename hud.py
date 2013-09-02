# coding: utf8
import pyglet
from pyglet import gl
from pyglet.text import Label

from labels import FONT_NAME, GOLD, CYAN


# Set the default message colour
DEFAULT_COLOUR = CYAN


class HUD(object):
    def __init__(self, width, height):
        self.message_labels = []
        self.batch = pyglet.graphics.Batch()

        self.width = width
        self.height = height

        self.money = Label(
            text=u'0€',
            x=self.width - 10,
            y=self.height - 30,
            font_name=FONT_NAME,
            font_size=20,
            anchor_x='right',
            anchor_y='baseline',
            color=GOLD + (255,),
            batch=self.batch
        )

    def set_money(self, money):
        self.money.text = u'%d€' % money

    def set_message(self, message):
        self.set_messages([message])

    def append_message(self, message, colour=DEFAULT_COLOUR):
        self._add_message(message)
        self._layout_messages()

    def _add_message(self, message, colour=DEFAULT_COLOUR):
        self.message_labels.append(Label(
            text=message,
            x=10,
            y=0,
            font_name=FONT_NAME,
            font_size=10,
            anchor_x='left',
            anchor_y='baseline',
            color=colour + (255,),
            batch=self.batch
        ))

    def _layout_messages(self):
        n = len(self.message_labels)
        for i, l in enumerate(self.message_labels):
            l.y = (n - i) * 20 + 40

    def set_messages(self, messages):
        self.clear_messages()
        for m in messages:
            self._add_message(m)
        self._layout_messages()

    def clear_messages(self):
        for m in self.message_labels:
            m.delete()
        del self.message_labels[:]

    def draw(self):
        gl.glLoadIdentity()
        self.batch.draw()
