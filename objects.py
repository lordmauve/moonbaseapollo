# coding: utf8
import random
import math
import pyglet.sprite
from loader import load_centred
from wasabi.geom import v
from wasabi.geom.poly import Rect

from effects import Explosion
from labels import FloatyLabel, GOLD


class Collidable(object):
    """Objects that can be collided with.

    All collidable objects are assumed to be circles, with a fixed radius
    RADIUS in pixels, and a centre given by inst.position, which must be a
    wasabi.geom.vector.Vector.

    Collidable objects maintain their references in the world's spatial hash.
    We use "fat bounds" with error^2 counting to reduce the frequency with which
    we have to move objects.

    """
    _position = v(0, 0)
    _position_error = float('inf')
    _fat_bounds = None
    alive = True

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, v):
        self._position_error += (v - self.position).length2
        self._position = v
        if self._position_error > 2500:
            self._update_bounds()
            self._position_error = 0

    def _update_bounds(self):
        fat_r = self.RADIUS + 50
        new_bounds = Rect.from_cwh(self.position, fat_r, fat_r)
        if self._fat_bounds:
            try:
                self.world.spatial_hash.remove_rect(self._fat_bounds, self)
            except (KeyError, IndexError):
                # weren't in there anyway
                pass
            else:
                self.world.spatial_hash.add_rect(new_bounds, self)
        else:
            if self.alive:
                self.world.spatial_hash.add_rect(new_bounds, self)
        self._fat_bounds = new_bounds

    def colliding(self, other):
        r = self.RADIUS + other.RADIUS
        return (self.position - other.position).length2 < r * r

    def on_collide(self, player):
        player.explode()


class Collector(Collidable):
    id = None

    def can_collect(self, o):
        return isinstance(o, Collectable) and (
            o.destination is None or o.destination == self.id
        )

    def collect(self, o):
        o.kill()
        self.world.dispatch_event('on_item_collected', self, o)
        if o.VALUE:
            FloatyLabel(
                self.world, u'+%d€' % o.VALUE,
                position=o.position,
                colour=GOLD
            )

    def do_collisions(self):
        for o in self.world.collidable_objects:
            if o.colliding(self):
                if self.can_collect(o):
                    self.collect(o)
                    return


class MoonBase(Collector):
    id = 'moonbase'
    alive = True
    RADIUS = 50.0
    OFFSET = v(0, 130.0)

    def __init__(self, world, moon):
        self.world = world
        self.moon = moon

    @property
    def position(self):
        return self.moon.position + self.OFFSET.rotated(-self.moon.rotation)


class CommsStation(Collector):
    RADIUS = 30.0

    @classmethod
    def load(cls):
        if not hasattr(cls, 'img'):
            cls.img = load_centred('comms-station')
            cls.img.anchor_y = 40

    def __init__(self, world, position):
        self.position = position
        self.world = world
        self.sprite = pyglet.sprite.Sprite(self.img)
        self.sprite.position = self.position
        self.world.spawn(self)

    def draw(self):
        self.sprite.draw()

    def update(self, dt):
        self.do_collisions()


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
        self.moonbase = MoonBase(world, self)

        self.world.spawn(self)

    def draw(self):
        self.sprite.rotation = self.rotation
        self.sprite.draw()

    def update(self, ts):
        self.rotation += self.ANGULAR_VELOCITY * ts
        self.moonbase.do_collisions()


class Collectable(Collidable):
    RADIUS = 9.0
    SPRITE_NAME = None  # Subclasses should set this
    MASS = 0.5
    VALUE = 5
    MAX_ANGULAR_VELOCITY = 60

    @classmethod
    def load(cls):
        if not hasattr(cls, 'img'):
            cls.img = load_centred(cls.SPRITE_NAME)

    def __init__(self, world, position, velocity=v(0, 0), destination='moonbase'):
        """Create a collectable.

        destination is the id of a collector this is bound for. It will not be
        accepted at other collectors.

        Pass destination=None to allow the collectable to be collected at all
        collectors.

        """
        self.world = world
        self.position = position
        self.velocity = velocity
        self.destination = destination

        self.sprite = pyglet.sprite.Sprite(self.img)
        self.sprite.rotation = random.random() * 360
        self.angular_velocity = (random.random() - 0.5) * self.MAX_ANGULAR_VELOCITY
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
                if isinstance(o, Collector):
                    continue

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
    VALUE = 20


class Ice(Collectable):
    SPRITE_NAME = 'ice-fragment'
    VALUE = 15


class Metal(Collectable):
    SPRITE_NAME = 'metal-fragment'
    VALUE = 30


class FrozenFood(Collectable):
    SPRITE_NAME = 'frozen-food'
    VALUE = 35
    MASS = 2
    RADIUS = 14


class Astronaut(Collectable):
    SPRITE_NAME = 'astronaut'
    VALUE = 0
    MAX_ANGULAR_VELOCITY = 15  # don't make them sick!

    alive = True

    @classmethod
    def load(cls):
        super(Astronaut, cls).load()
        if not hasattr(cls, 'NAMES'):
            cls.NAMES = [l.strip() for l in pyglet.resource.file('names.txt', 'rU') if l.strip()]

    def __init__(self, *args, **kwargs):
        self.name = kwargs.pop('name', None) or random.choice(self.NAMES)
        super(Astronaut, self).__init__(*args, **kwargs)

    def explode(self):
        super(Astronaut, self).explode()
        self.world.dispatch_event('on_astronaut_death', self)

    def kill(self):
        self.alive = False
        super(Astronaut, self).kill()


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
    def random(cls, world, random=random):
        while True:
            dist = random.normalvariate(2500, 1000)
            if dist > 500:
                # Don't put asteroids too close to the moon
                break
        angle = random.random() * 360
        pos = v(0, dist).rotated(angle)
        return cls(world, pos)

    def __init__(self, world, position, velocity=v(0, 0), img=None):
        self.world = world
        self.position = position
        self.velocity = velocity
        self.sprite = pyglet.sprite.Sprite(img or random.choice(self.SPRITES))
        # self.sprite.scale = scale
        self.rotation = random.random() * 360
        self.angular_velocity = (random.random() - 0.5) * 60
        self.world.spawn(self)

    def draw(self):
        self.sprite.rotation = self.rotation
        self.sprite.position = self.position
        self.sprite.draw()

    def update(self, ts):
        self.position += self.velocity * ts
        self.rotation += self.angular_velocity * ts

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


def spawn_random_asteroids(world, num):
    r = random.Random()
    r.seed(0)
    for i in xrange(num):
        Asteroid.random(world, random=r)


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
    Astronaut,
    CommsStation,
    FrozenFood
]


def load_all():
    for c in CLASSES:
        c.load()
