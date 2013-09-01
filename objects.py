# coding: utf8
import random
import math
import pyglet.sprite
from loader import load_centred
from wasabi.geom import v

from effects import Explosion
from labels import FloatyLabel


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
        player.explode()


class MoonBase(Collidable):
    alive = True
    RADIUS = 50.0
    OFFSET = v(0, 130.0)

    def __init__(self, moon):
        self.moon = moon

    @property
    def position(self):
        return self.moon.position + self.OFFSET.rotated(-self.moon.rotation)

    def do_collisions(self, world):
        for o in world.collidable_objects:
            if o.colliding(self):
                if isinstance(o, Collectable):
                    o.kill()
                    FloatyLabel(
                        world, u'+10€',
                        position=o.position,
                        colour=(212, 170, 0)
                    )


class Moon(Collidable):
    RADIUS = 140.0
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
        self.moonbase.do_collisions(self.world)


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
        self.tethered_to = None
        self.world.spawn(self)

    def draw(self):
        self.sprite.position = self.position
        self.sprite.draw()

    def update(self, ts):
        self.sprite.rotation += self.angular_velocity * ts
        self.position += self.velocity * ts
        self.do_collisions()

    def do_collisions(self):
        for o in self.world.collidable_objects:
            if o is not self and o.colliding(self):
                if isinstance(o, Collectable):
                    o.explode()
                self.explode()
                return

    def explode(self):
        """Explode the object."""
        Explosion(self.world, self.position)
        self.kill()

    def kill(self):
        """Remove the object from the world."""
        if self.tethered_to:
            self.tethered_to.release()
        self.world.kill(self)

    def on_collide(self, player):
        if player.tethered:
            return
        player.attach(self)


class Cheese(Collectable):
    SPRITE_NAME = 'cheese-fragment'


class Ice(Collectable):
    SPRITE_NAME = 'ice-fragment'


class Metal(Collectable):
    SPRITE_NAME = 'metal-fragment'


class Asteroid(Collidable):
    RADIUS = 32
    EJECT_SPEED = 50
    EJECT_RANDOMNESS = 30

    SPRITE_NAMES = [
        'asteroid'
    ]

    @classmethod
    def load(cls):
        cls.SPRITES = [load_centred(name) for name in cls.SPRITE_NAMES]

    @classmethod
    def random(cls, world):
        while True:
            x = (random.random() - 0.5) * 2000
            y = (random.random() - 0.5) * 2000
            pos = v(x, y)
            if pos.length2 > 4e5:
                # Don't put asteroids too close to the moon
                break
        return cls(world, pos)

    def __init__(self, world, position, velocity=v(0, 0), img=None):
        self.world = world
        self.position = position
        self.velocity = velocity
        self.sprite = pyglet.sprite.Sprite(img or random.choice(self.SPRITES))
        # self.sprite.scale = scale
        self.sprite.rotation = random.random() * 360
        self.angular_velocity = (random.random() - 0.5) * 60
        self.world.spawn(self)

    def draw(self):
        self.sprite.draw()

    def update(self, ts):
        self.position += self.velocity * ts
        self.sprite.position = self.position
        self.sprite.rotation += self.angular_velocity * ts

    def fragment_class(self):
        return AsteroidFragment

    def spawn_fragment(self, position, velocity=v(0, 0)):
        """Spawn a fragment at the given position."""
        cls = self.fragment_class()
        cls(self.world, position, velocity)

        new_radius = math.sqrt(self.RADIUS * self.RADIUS - 81)
        frac = new_radius / self.RADIUS
        self.sprite.scale *= frac
        self.RADIUS *= frac
        if self.RADIUS < 10:
            self.world.kill(self)
            cls(self.world, self.position)

    def fragment(self, position):
        """Eject a fragment given a bullet impact at position."""
        outwards = (position - self.position).normalized()

        # Place the new fragment where it cannot collide immediately
        edge_pos = self.position + outwards * (self.RADIUS + 8)

        # Fire outwards
        vel =  outwards * self.EJECT_SPEED

        # Add a random component
        vel += v(0, random.random() * self.EJECT_RANDOMNESS).rotated(random.random() * 360)

        self.spawn_fragment(edge_pos, vel)


class AsteroidFragment(Asteroid):
    RADIUS = 8

    SPRITE_NAMES = [
        'asteroid-fragment',
    ]

    def fragment(self, position):
        self.world.kill(self)


class CheeseAsteroid(Asteroid):
    SPRITE_NAMES = [
        'cheese',
    ]

    def fragment_class(self):
        return Cheese


class MetalAsteroid(Asteroid):
    SPRITE_NAMES = [
        'metal',
    ]

    def fragment_class(self):
        return Metal


class IceAsteroid(Asteroid):
    SPRITE_NAMES = [
        'ice',
    ]

    def fragment_class(self):
        return Ice


def spawn_random_asteroid(world):
    cls = random.choice([Asteroid] * 10 + [
        CheeseAsteroid,
        IceAsteroid,
        MetalAsteroid,
    ])
    cls.random(world)


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


CLASSES = [
    Asteroid,
    AsteroidFragment,
    MetalAsteroid,
    IceAsteroid,
    CheeseAsteroid,
    Moon,
    Metal,
    Ice,
    Cheese,
]


def load_all():
    for c in CLASSES:
        c.load()
