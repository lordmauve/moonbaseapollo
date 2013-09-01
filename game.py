import random
import math
from collections import namedtuple, defaultdict

import pyglet
from pyglet.window import key
from pyglet.event import EventDispatcher
from pyglet import gl
from wasabi.geom import v
from wasabi.geom.poly import Rect

from loader import load_centred
from objects import Moon, Collidable
from effects import Explosion
from labels import FadeyLabel, FONT_FILENAME, Signpost


WIDTH = 1024
HEIGHT = 600

FPS = 30

# Set up pyglet resource loader
pyglet.resource.path += [
    'sprites/',
    'fonts/',
]
pyglet.resource.reindex()
pyglet.resource.add_font(FONT_FILENAME)


class Asteroid(Collidable):
    RADIUS = 32

    @classmethod
    def load(cls):
        if not hasattr(cls, 'ASTEROID1'):
            cls.ASTEROID1 = load_centred('asteroid')

    @classmethod
    def random(cls, world):
        while True:
            x = (random.random() - 0.5) * 2000
            y = (random.random() - 0.5) * 2000
            if x * x + y * y > 4e5:
                break
        img = random.choice((cls.ASTEROID1,))
        return cls(world, x, y, img)

    @property
    def pos(self):
        return v(self.x, self.y)

    def __init__(self, world, x, y, img):
        self.world = world
        self.position = v(x, y)
        self.sprite = pyglet.sprite.Sprite(img)
        self.sprite.position = x, y
        # self.sprite.scale = scale
        self.sprite.rotation = random.random() * 360
        self.angular_velocity = (random.random() - 0.5) * 60
        self.world.spawn(self)

    def draw(self):
        self.sprite.draw()

    def update(self, ts):
        self.sprite.rotation += self.angular_velocity * ts


ShipModel = namedtuple('ShipModel', 'name sprite rotation acceleration max_speed radius')

CUTTER = ShipModel(
    name='Cutter',
    sprite=load_centred('cutter'),
    rotation=100.0,  # angular velocity, degrees/second
    acceleration=15.0,  # pixels per second per second
    max_speed=200.0,  # maximum speed in pixels/second
    radius=5.0
)


class Player(object):
    ship_count = defaultdict(int)

    def __init__(self, world, x, y, ship=CUTTER):
        self.world = world
        self.velocity = v(0.0, 30.0)
        self.position = v(x, y)
        self.ship = ship
        self.sprite = pyglet.sprite.Sprite(ship.sprite)
        self.sprite.position = x, y
        self.sprite.rotation = 0.0
        self.alive = True
        self.RADIUS = self.ship.radius
        self.world.spawn(self)

        self.pick_name()

        FadeyLabel(
            self.world,
            self.name,
            follow=self,
            colour=(0, 128, 0)
        )

    def pick_name(self):
        """Pick a name for this ship.

        Each new incarnation of the ship has a different ID.

        """
        self.ship_count[self.ship.name] += 1
        self.name = '%s %d' % (
            self.ship.name,
            self.ship_count[self.ship.name]
        )

    def draw(self):
        self.sprite.position = self.position
        self.sprite.draw()

    def update(self, ts):
        u = self.velocity

        if self.world.keyboard[key.Z]:
            self.shoot()

        if self.world.keyboard[key.UP]:
            self.thrust(ts)
        if self.world.keyboard[key.LEFT]:
            self.rotate_acw(ts)
        if self.world.keyboard[key.RIGHT]:
            self.rotate_cw(ts)

        speed = self.velocity.length
        if speed > self.ship.max_speed:
            self.velocity *= self.ship.max_speed / speed
        # Constant acceleration formula
        self.position += 0.5 * (u + self.velocity) * ts

        self.do_collisions()

    def do_collisions(self):
        for o in self.world.collidable_objects:
            if o.colliding(self):
                self.kill()

    def kill(self):
        Explosion(self.world, self.position)
        self.world.kill(self)
        self.alive = False
        self.world.dispatch_event('on_player_death')

    def rotate_cw(self, ts):
        """Rotate clockwise."""
        self.sprite.rotation += self.ship.rotation * ts

    def rotate_acw(self, ts):
        """Rotate anticlockwise."""
        self.sprite.rotation -= self.ship.rotation * ts

    def thrust(self, ts):
        rotation = math.radians(self.sprite.rotation)
        accel = self.ship.acceleration
        a = v(
            math.sin(rotation) * accel,
            math.cos(rotation) * accel
        )
        self.velocity += a

    def shoot(self):
        rotation = math.radians(self.sprite.rotation)
        dir = v(
            math.sin(rotation),
            math.cos(rotation)
        )
        self.world.shoot(self.position, dir)


class Bullet(object):
    RADIUS = 5

    @classmethod
    def load(cls):
        if not hasattr(cls, 'BULLET'):
            cls.BULLET = load_centred('bullet')

    def __init__(self, world, pos, dir):
        self.world = world
        self.position = pos
        self.direction = dir
        self.sprite = pyglet.sprite.Sprite(Bullet.BULLET)
        self.sprite.position = pos.x, pos.y
        self.world.spawn(self)

    def draw(self):
        self.sprite.position = self.position
        self.sprite.draw()

    def update(self, ts):
        self.position += 50 * self.direction
        self.do_collisions()

    def do_collisions(self):
        for o in self.world.collidable_objects:
            if o.colliding(self):
                self.kill()

    def kill(self):
        Explosion(self.world, self.position)
        self.world.kill(self)


class Camera(object):
    def __init__(self, position=v(0, 0)):
        self.position = position
        self.offset = v(WIDTH * -0.5, HEIGHT * -0.5)

    def set_matrix(self):
        x, y = self.position + self.offset
        gl.glLoadIdentity()
        gl.glTranslatef(-x, -y, 0)

    def track(self, o):
        self.position = o.position

    def get_viewport(self):
        return Rect.from_cwh(self.position, WIDTH, HEIGHT)


class World(EventDispatcher):
    def __init__(self, keyboard):
        self.keyboard = keyboard
        self.objects = []
        self.collidable_objects = []

        self.camera = Camera()
        self.setup_projection_matrix()
        self.setup_world()

    def spawn_player(self):
        self.player = Player(self, 0, 180)
        self.camera.track(self.player)

    def setup_world(self):
        """Create the initial world."""
        self.generate_asteroids()
        moon = Moon(self)
        FadeyLabel(
            self,
            'Moonbase Alpha',
            follow=moon.moonbase,
            offset=v(30, 15)
        )

        self.moonbase_signpost = Signpost(
            self.camera,
            'Moonbase Alpha',
            moon.moonbase
        )
        self.spawn_player()

    def spawn(self, o):
        self.objects.append(o)
        if isinstance(o, Collidable):
            self.collidable_objects.append(o)

    def kill(self, o):
        self.objects.remove(o)
        if isinstance(o, Collidable):
            self.collidable_objects.remove(o)

    def generate_asteroids(self):
        for i in xrange(50):
            Asteroid.random(self)
            # b = ast.get_bounds()
            # b = Circle(b.centre, b.radius + 100)
            # for o in self.objects:
            #     if o.get_bounds().intersects(b):
            #         break
            # else:
            #     self.objects.append(ast)

    def setup_projection_matrix(self):
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glOrtho(
            WIDTH * -0.5, WIDTH * 0.5,
            HEIGHT * -0.5, HEIGHT * 0.5,
            -100, 100
        )
        gl.glMatrixMode(gl.GL_MODELVIEW)

    def update(self, ts):
        for o in self.objects:
            o.update(ts)
        self.camera.track(self.player)

    def draw(self):
        # draw a black background
        gl.glClearColor(0, 0, 0, 1)
        self.camera.set_matrix()

        for o in self.objects:
            o.draw()

        self.moonbase_signpost.draw()

    def shoot(self, pos, dir):
        Bullet(self, pos, dir)

World.register_event_type('on_player_death')


class Game(object):
    def __init__(self):
        self.window = pyglet.window.Window(
            width=WIDTH,
            height=HEIGHT
        )
        self.keyboard = key.KeyStateHandler()

        # load the sprites for objects
        Asteroid.load()
        Bullet.load()

        # initialise the World and start the game
        self.world = World(self.keyboard)
        self.world.set_handler('on_player_death', self.on_player_death)
        self.start()

    def on_player_death(self):
        # Wait a couple of seconds then respawn the player
        pyglet.clock.schedule_once(
            lambda dt, world: world.spawn_player(),
            2,
            self.world
        )

    def start(self):
        self.window.push_handlers(self.keyboard, on_draw=self.on_draw)
        pyglet.clock.schedule_interval(self.update, 1.0 / FPS)
        pyglet.app.run()

    def on_draw(self):
        self.window.clear()
        self.world.draw()

    def update(self, ts):
        self.world.update(ts)


if __name__ == '__main__':
    game = Game()
