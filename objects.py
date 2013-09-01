import pyglet.sprite
from loader import load_centred
from wasabi.geom import v


class MoonBase(object):
    RADIUS = 33.0
    OFFSET = v(0, 130.0)

    def __init__(self, moon):
        self.moon = moon

    @property
    def position(self):
        return self.moon.position + self.OFFSET.rotated(-self.moon.rotation)


class Moon(object):
    RADIUS = 145.0
    ANGULAR_VELOCITY = 5.0  # degrees/second

    @classmethod
    def load(cls):
        if not hasattr(cls, 'img'):
            cls.img = load_centred('moonbase')

    def __init__(self, world, x=0, y=0):
        self.world = world
        self.position = v(x, y)
        self.load()
        self.sprite = pyglet.sprite.Sprite(self.img)
        self.sprite.position = self.position
        self.rotation = 0  # rotation in degrees
        self.moonbase = MoonBase(self)

        self.world.spawn(self)

    def draw(self):
        self.sprite.rotation = self.rotation
        self.sprite.draw()

    def update(self, ts):
        self.rotation += self.ANGULAR_VELOCITY * ts

