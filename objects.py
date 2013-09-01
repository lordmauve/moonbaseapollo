import random
import pyglet.sprite
from loader import load_centred
from wasabi.geom import v


class Collidable(object):
    """Objects that can be collided with.

    All collidable objects are assumed to be circles, with a fixed radius
    RADIUS in pixels, and a centre given by inst.position, which must be a
    wasabi.geom.vector.Vector.

    """
    def colliding(self, other):
        r = self.RADIUS + other.RADIUS
        return (self.position - other.position).length2 < r * r

    def on_collide(self, player):
        player.kill()


class MoonBase(Collidable):
    alive = True
    RADIUS = 33.0
    OFFSET = v(0, 130.0)

    def __init__(self, moon):
        self.moon = moon

    @property
    def position(self):
        return self.moon.position + self.OFFSET.rotated(-self.moon.rotation)


class Moon(Collidable):
    RADIUS = 135.0
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


class Collectable(Collidable):
    RADIUS = 9.0
    SPRITE_NAME = None  # Subclasses should set this
    MASS = 0.5

    @classmethod
    def load(cls):
        if not hasattr(cls, 'img'):
            cls.img = load_centred(cls.SPRITE_NAME)

    def __init__(self, world, position, velocity=v(0, 0)):
        self.world = world
        self.position = position
        self.sprite = pyglet.sprite.Sprite(self.img)
        self.velocity = velocity
        self.sprite.rotation = random.random() * 360
        self.angular_velocity = (random.random() - 0.5) * 60
        self.world.spawn(self)

    def draw(self):
        self.sprite.position = self.position
        self.sprite.draw()

    def update(self, ts):
        self.sprite.rotation += self.angular_velocity * ts
        self.position += self.velocity * ts

    def kill(self):
        self.world.kill(self)

    def on_collide(self, player):
        if player.tethered:
            return
        self.world.kill(self)
        player.tethered = self


class Cheese(Collectable):
    SPRITE_NAME = 'cheese-fragment'


class Ice(Collectable):
    SPRITE_NAME = 'ice-fragment'


class Metal(Collectable):
    SPRITE_NAME = 'metal-fragment'


def spawn_random_collectable(world):
    cls = random.choice([
        Cheese, Ice, Metal
    ])

    while True:
        x = (random.random() - 0.5) * 2000
        y = (random.random() - 0.5) * 2000
        if x * x + y * y > 4e5:
            break
    return cls(world, v(x, y))


def load_all():
    Metal.load()
    Ice.load()
    Cheese.load()
    Moon.load()
