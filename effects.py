import pyglet.sprite
from loader import load_centred
from wasabi.geom import v


class Explosion(object):
    MAX_AGE = 0.6
    MIN_SCALE = 0.1
    EXPANSION = 5.0

    @classmethod
    def load(cls):
        if not hasattr(cls, 'img'):
            cls.img = load_centred('explosion')

    def __init__(self, world, position):
        self.world = world
        self.position = v(position)
        self.load()
        self.age = 0
        self.sprite = pyglet.sprite.Sprite(self.img)
        self.sprite.position = self.position
        self.sprite.scale = self.MIN_SCALE
        self.world.spawn(self)

    def draw(self):
        self.sprite.draw()

    def update(self, ts):
        self.age += ts
        if self.age > self.MAX_AGE:
            self.world.kill(self)
        self.sprite.scale = self.MIN_SCALE + self.age * self.EXPANSION
        self.sprite.opacity = int(255 * (1 - (self.age / self.MAX_AGE)))

