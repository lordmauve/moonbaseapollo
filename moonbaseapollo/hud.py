# coding: utf8
import pyglet
from pyglet import gl
from pyglet.text import Label

from labels import FONT_NAME, GOLD, CYAN, RED


# Set the default message colour
DEFAULT_COLOUR = CYAN


# How long messages stay in the HUD
MESSAGE_TIME = 10  # seconds


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

        self.countdown = None

    def set_countdown(self, seconds):
        text = '%d:%02d' % (seconds // 60, seconds % 60)
        if self.countdown:
            self.countdown.text = text
        else:
            self.countdown = Label(
                text=text,
                x=self.width // 2,
                y=self.height - 30,
                font_name=FONT_NAME,
                font_size=20,
                anchor_x='center',
                anchor_y='baseline',
                color=RED + (255,),
                batch=self.batch
            )

    def clear_countdown(self):
        if self.countdown:
            self.countdown.delete()
            self.countdown = None

    def set_money(self, money):
        self.money.text = u'%d€' % money

    def append_message(self, message, colour=DEFAULT_COLOUR):
        pyglet.clock.schedule_once(self.pop_messages, MESSAGE_TIME, 1)
        self._add_message(message, colour=colour)
        self._layout_messages()

    def append_messages(self, messages, colour=DEFAULT_COLOUR):
        for m in messages:
            self._add_message(m, colour=colour)
        pyglet.clock.schedule_once(self.pop_messages, MESSAGE_TIME, len(messages))
        self._layout_messages()

    def pop_messages(self, dt, count):
        """Pop count messages."""
        ms = self.message_labels[:count]
        del self.message_labels[:count]
        for m in ms:
            m.delete()

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

    def clear_messages(self):
        for m in self.message_labels:
            m.delete()
        del self.message_labels[:]
        pyglet.clock.unschedule(self.pop_messages)

    def draw(self):
        gl.glLoadIdentity()
        self.batch.draw()
