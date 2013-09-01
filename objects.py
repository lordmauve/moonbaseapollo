import math
import pyglet.sprite
from loader import load_centred


class Moonbase(object):
    RADIUS = 145.0

    @classmethod
    def load(cls):
        if not hasattr(cls, 'img'):
            cls.img = load_centred('moonbase')

    def __init__(self, world, x=0, y=0):
        self.world = world
        self.x = x
        self.y = y
        self.load()
        self.sprite = pyglet.sprite.Sprite(self.img)
        self.sprite.position = x, y
        self.rotation = 0  # rotation in radians
        self.angular_velocity = 0.05

    def draw(self):
        self.sprite.rotation = math.degrees(self.rotation)
        self.sprite.draw()

    def update(self, ts):
        self.rotation += self.angular_velocity * ts

