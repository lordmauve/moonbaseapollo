# coding: utf8
import random
import math
import pyglet.sprite
from loader import load_centred
from wasabi.geom import v
from wasabi.geom.poly import Rect

from effects import Explosion
from labels import FloatyLabel, GOLD
from ships import LUGGER, CUTTER


class Collider(object):
    """Base class for objects that can look for collisions."""
    COLGROUPS = 1
    COLMASK = 0xffffffff

    def get_bounding_rect(self):
        return Rect.from_cwh(self.position, self.RADIUS * 2, self.RADIUS * 2)

    def iter_collisions(self):
        aabb = self.get_bounding_rect()
        potential = self.world.spatial_hash.potential_intersection(aabb)
        return (o for o in potential if o is not self and self.colliding(o))

    def colliding(self, other):
        if self.COLMASK & other.COLGROUPS:
            r = self.RADIUS + other.RADIUS
            return (self.position - other.position).length2 < r * r
        return False


class Bullet(Collider):
    RADIUS = 3
    SPEED = 200

    COLGROUPS = 0x8
    COLMASK = 0xfd

    @classmethod
    def load(cls):
        if not hasattr(cls, 'BULLET'):
            cls.BULLET = load_centred('bullet')

    def __init__(self, world, pos, dir, initial_velocity=v(0, 0)):
        self.world = world
        self.position = pos
        self.velocity = (dir * self.SPEED + initial_velocity)
        self.sprite = pyglet.sprite.Sprite(Bullet.BULLET)
        self.sprite.position = pos.x, pos.y
        self.sprite.rotation = 90 - dir.angle
        self.world.spawn(self)

    def draw(self):
        self.sprite.position = self.position
        self.sprite.draw()

    def update(self, ts):
        self.position += self.velocity * ts
        self.do_collisions()

    def do_collisions(self):
        for o in self.iter_collisions():
            self.world.dispatch_event('on_object_shot', o)

            if isinstance(o, Asteroid):
                o.fragment(self.position)

            if isinstance(o, (Asteroid, Moon)):
                Explosion(self.world, self.position, particle_amount=10)
            else:
                Explosion(self.world, self.position)

            if hasattr(o, 'shot'):
                o.shot()

            self.kill()
            break

    def kill(self):
        self.world.kill(self)


class Collidable(Collider):
    """Objects that can be collided with.

    All collidable objects are assumed to be circles, with a fixed radius
    RADIUS in pixels, and a centre given by inst.position, which must be a
    wasabi.geom.vector.Vector.

    Collidable objects maintain their references in the world's spatial hash.
    We use "fat bounds" with error tracking to reduce the frequency with which
    we have to move objects.

    """
    _position = v(0, 0)
    _bounds_pos = v(float('inf'), float('inf'))
    _fat_bounds = None
    FATNESS = 50  # how much to offset by; increase this for fast-moving objects
    alive = True

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, v):
        self._position = v
        if (self._position - self._bounds_pos).length2 > self.FATNESS:
            self._update_bounds()
            self._bounds_pos = self._position

    def _update_bounds(self):
        fat_r = self.RADIUS + self.FATNESS
        new_bounds = Rect.from_cwh(self.position, fat_r * 2, fat_r * 2)
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

    def kill(self):
        self.world.kill(self)
        self.alive = False

    def explode(self):
        """Explode the object."""
        Explosion(self.world, self.position)
        self.kill()
        self.world.dispatch_event('on_object_destroyed', self)


class Collector(Collidable):
    id = None
    COLMASK = 0x10
    COLGROUPS = 0x2

    def can_collect(self, o):
        return isinstance(o, Collectable) and (
            o.destination is None or o.destination == self.id
        )

    def collect(self, o):
        o.kill()
        self.world.dispatch_event('on_item_collected', self, o)

    def do_collisions(self):
        for o in self.iter_collisions():
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

    def draw(self):
        """Moon base graphic is currently part of moon."""

    def update(self, dt):
        self.position = self.moon.position + self.OFFSET.rotated(-self.moon.rotation)
        self.do_collisions()


class BaseStation(Collector):
    RADIUS = 30.0

    @classmethod
    def load(cls):
        if not hasattr(cls, 'img'):
            cls.img = load_centred(cls.SPRITE_NAME)
            cls.img.anchor_y = 40

    def __init__(self, world, position):
        self.world = world
        self.position = position
        self.sprite = pyglet.sprite.Sprite(self.img)
        self.sprite.position = self.position
        self.world.spawn(self)

    def draw(self):
        self.sprite.draw()

    def update(self, dt):
        self.do_collisions()


class CommsStation(BaseStation):
    name = 'Comm Station 4'
    SPRITE_NAME = 'comms-station'


class SolarFarm(BaseStation):
    RADIUS = 30.0
    name = 'Solar Farm'
    SPRITE_NAME = 'solar-farm'


class SpaceDock(BaseStation):
    RADIUS = 30.0
    name = 'Spacedock'
    SPRITE_NAME = 'spacedock'


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
        self.moonbase.update(ts)


class Marker(Collidable):
    """Mark the place where a player must go."""
    COLGROUPS = 0x100

    ANGULAR_VELOCITY = 10
    RADIUS = 48
    VALUE = 0

    @classmethod
    def load(cls):
        if not hasattr(cls, 'img'):
            cls.img = load_centred('marker')

    def __init__(self, world, position):
        self.world = world
        self.position = position
        self.sprite = pyglet.sprite.Sprite(self.img)
        self.sprite.position = position
        self.world.spawn(self)

    def draw(self):
        self.sprite.draw()

    def update(self, ts):
        self.sprite.rotation += self.ANGULAR_VELOCITY * ts


class FixedMarker(Marker):
    """A marker that doesn't disappear if touched."""
    COLGROUPS = 0


class Collectable(Collidable):
    RADIUS = 9.0
    SPRITE_NAME = None  # Subclasses should set this
    MASS = 0.5
    VALUE = 5
    MAX_ANGULAR_VELOCITY = 60

    # don't collide with the collector
    # (because the collector collides with us)
    COLMASK = 0xfffffff9
    COLGROUPS = 0x10

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
        collisions = self.iter_collisions()
        for o in collisions:
            if isinstance(o, Collectable):
                o.explode()
            self.explode()
            return

    def kill(self):
        """Remove the object from the world."""
        if self.tethered_to:
            self.tethered_to.release()
        self.world.kill(self)
        self.alive = False


class Cheese(Collectable):
    SPRITE_NAME = 'cheese-fragment'
    VALUE = 35


class Ice(Collectable):
    SPRITE_NAME = 'ice-fragment'
    VALUE = 20


class Metal(Collectable):
    SPRITE_NAME = 'metal-fragment'
    VALUE = 40


class Coin(Collectable):
    SPRITE_NAME = 'coin'
    VALUE = 10


class FrozenFood(Collectable):
    SPRITE_NAME = 'frozen-food'
    VALUE = 50
    MASS = 2
    RADIUS = 14


class MedicalCrate(Collectable):
    SPRITE_NAME = 'medical-supplies'
    VALUE = 80
    MASS = 1.5
    RADIUS = 11


class SwappableShip(Collectable):
    VALUE = 100
    MASS = 1.5
    RADIUS = 20
    COLGROUPS = 0x100

    def __init__(self, world, position, rotation=0):
        self.img = self.ship.sprite
        super(SwappableShip, self).__init__(world, position, destination='')
        self.swapped = False
        self.sprite.rotation = rotation
        self.angular_velocity = 0

    def swap(self):
        if self.swapped:
            return  # Can't swap back
        s = self.world.player.ship
        self.sprite.image = s.sprite
        player = self.world.player
        self.name = player.name
        self.world.set_player_ship(self.ship.name)
        # Exchange positions and rotations and names
        self.position, player.position = player.position, self.position
        self.sprite.rotation, player.sprite.rotation = player.sprite.rotation, self.sprite.rotation
        self.swapped = True
        self.world.dispatch_event('on_item_collected', player, self)

    def do_collisions(self):
        pass


class Lugger(SwappableShip):
    ship = LUGGER
    name = ship.name


class Battery(Collectable):
    SPRITE_NAME = 'battery'
    VALUE = 60
    MASS = 1.5
    RADIUS = 14
    MAX_ANGULAR_VELOCITY = 0  # Start non-rotating

    def __init__(self, *args, **kwargs):
        super(Battery, self).__init__(*args, **kwargs)
        self.sprite.rotation = 0

    def update(self, dt):
        if self.tethered_to:
            # Rotate once tethered
            self.angular_velocity += dt
            self.angular_velocity = min(self.angular_velocity, 8.0)  # cap
        super(Battery, self).update(dt)


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


class Satellite(Collectable):
    SPRITE_NAME = 'colonysat'
    VALUE = 0
    RADIUS = 14
    MASS = 4

    name = 'ColonySat 1'

    def __init__(self, *args, **kwargs):
        super(Satellite, self).__init__(*args, **kwargs)
        self.angular_velocity = 10

    def update(self, dt):
        if not self.tethered_to:
            self.velocity *= 0.5 ** dt
        else:
            self.angular_velocity *= 0.5 ** dt
        super(Satellite, self).update(dt)


class Droid(Collidable):
    RADIUS = 40

    @classmethod
    def load(cls):
        if not hasattr(cls, 'img'):
            cls.DROID_OK = load_centred('droid-ok')
            cls.DROID_BERSERK = load_centred('droid-beserk')

    def __init__(self, world, position, velocity=v(0, 0)):
        self.world = world
        self.position = position
        self.velocity = velocity
        self.sprite = pyglet.sprite.Sprite(self.DROID_OK)
        self.rotation = random.random() * 360
        self.angular_velocity = 200
        self.world.spawn(self)
        self.health = 200
        self.player_in_range = False
        self.world.push_handlers(self.on_region_entered)

    def draw(self):
        self.sprite.rotation = self.rotation
        self.sprite.position = self.position
        self.sprite.draw()

    def update(self, ts):
        self.position += self.velocity * ts
        self.rotation += self.angular_velocity * ts

        if self.player_in_range:
            # make the droid madder as it gets shot
            if self.health < 50:
                freq = 0.4
            elif self.health < 100:
                freq = 0.2
            elif self.health < 150:
                freq = 0.1
            else:
                freq = 0.05
            if random.random() < freq:
                self.shoot()

    def on_region_entered(self):
        self.sprite = pyglet.sprite.Sprite(self.DROID_BERSERK)
        self.player_in_range = True

    def shoot(self):
        rotation = math.radians(self.sprite.rotation)
        dir = v(
            math.sin(rotation),
            math.cos(rotation)
        ) * -1
        # laser_sound.play()
        Bullet(self.world, self.position + dir * 60, dir, self.velocity)

    def shot(self):
        self.health -= 10
        if self.health <= 0:
            self.explode()


class Asteroid(Collidable):
    EJECT_SPEED = 50
    EJECT_RANDOMNESS = 30

    SPRITE_NAMES = [
        'asteroid-s1',
        'asteroid-s2',
        'asteroid-m1',
        'asteroid-m2',
        'asteroid-l1',
        'asteroid-l2',
    ]

    RADIUSES = [
        32,
        32,
        46,
        46,
        64,
        64
    ]

    COLMASK = 0xff

    @classmethod
    def load(cls):
        cls.SPRITES = [load_centred(name) for name in cls.SPRITE_NAMES]

    @classmethod
    def generate(cls, world, random=random):
        while True:
            dist = random.normalvariate(2500, 1000)
            if dist > 500:
                # Don't put asteroids too close to the moon
                break
        angle = random.random() * 360
        pos = v(0, dist).rotated(angle)
        return cls(world, pos, random=random)

    def __init__(self, world, position, velocity=v(0, 0), random=random):
        self.world = world
        img, self.RADIUS = random.choice(zip(self.SPRITES, self.RADIUSES))
        self.position = position
        self.velocity = velocity
        self.sprite = pyglet.sprite.Sprite(img)
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
        if random.randint(0, 10) == 0:
            return Coin
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
            self.world.dispatch_event('on_object_destroyed', self)

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


class DangerousAsteroid(Asteroid):
    """A dangerous asteroid that can destroy space stations."""
    COLMASK = 0x02  # Only collectors

    @property
    def SPRITES(self):
        return Asteroid.SPRITES[:2]

    @property
    def RADIUSES(self):
        return Asteroid.RADIUSES[:2]

    def update(self, dt):
        super(DangerousAsteroid, self).update(dt)
        collisions = list(self.iter_collisions())
        for o in collisions:
            o.explode()


class AsteroidFragment(Asteroid):
    RADIUSES = [10]

    SPRITE_NAMES = [
        'asteroid-fragment',
    ]

    def fragment(self, position):
        self.world.kill(self)


class CheeseAsteroid(Asteroid):
    RADIUSES = [32]
    SPRITE_NAMES = ['cheese']

    def fragment_class(self):
        return Cheese


class MetalAsteroid(Asteroid):
    RADIUSES = [32]
    SPRITE_NAMES = ['metal']

    def fragment_class(self):
        return Metal


class IceAsteroid(Asteroid):
    RADIUSES = [32]
    SPRITE_NAMES = ['ice']

    def fragment_class(self):
        return Ice


def spawn_random_asteroids(world, num):
    r = random.Random()
    r.seed(1)
    for i in xrange(num):
        Asteroid.generate(world, random=r)


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
    FrozenFood,
    Coin,
    MedicalCrate,
    Marker,
    Satellite,
    SolarFarm,
    SpaceDock,
    Battery,
    Droid
]


def load_all():
    for c in CLASSES:
        c.load()
