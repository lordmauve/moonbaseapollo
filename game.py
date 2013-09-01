import random
import math
from collections import namedtuple, defaultdict

import pyglet
from pyglet.window import key
from pyglet.event import EventDispatcher, EVENT_HANDLED
from pyglet import gl
from wasabi.geom import v
from wasabi.geom.poly import Rect

from loader import load_centred
from objects import Moon, Collidable, spawn_random_collectable, load_all
from effects import Explosion
from labels import TrackingLabel, FONT_FILENAME, Signpost


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
            cls.ASTEROID_FRAG = load_centred('asteroid-fragment')

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

    def fragment(self):
        frag_pos = self.position + v(50, 0)
        Asteroid(self.world, frag_pos.x, frag_pos.y, Asteroid.ASTEROID_FRAG)


ShipModel = namedtuple('ShipModel', 'name sprite rotation acceleration max_speed radius mass')

CUTTER = ShipModel(
    name='Cutter',
    sprite=load_centred('cutter'),
    rotation=100.0,  # angular velocity, degrees/second
    acceleration=15.0,  # pixels per second per second
    max_speed=200.0,  # maximum speed in pixels/second
    radius=5.0,
    mass=1
)


class Player(object):
    ship_count = defaultdict(int)
    TETHER_FORCE = 0.5
    TETHER_DAMPING = 0.9

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
        self.MASS = self.ship.mass
        self.world.spawn(self)
        self.tethered = None

        self.pick_name()

        TrackingLabel(
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
        if self.tethered:
            self.draw_tractor_beam()
            self.tethered.draw()
            self.sprite.draw()
        else:
            self.sprite.draw()

    def draw_tractor_beam(self):
        p1 = self.position
        p2 = self.tethered.position
        along = (p2 - p1)
        across = along.rotated(90).normalised() * self.tethered.RADIUS
        gl.glEnable(gl.GL_BLEND)
        gl.glBegin(gl.GL_TRIANGLES)
        gl.glColor4f(0, 128, 0, 0.4)
        gl.glVertex2f(*p1)
        gl.glColor4f(0, 128, 0, 0)
        gl.glVertex2f(*(p2 + across))
        gl.glVertex2f(*(p2 - across))
        gl.glEnd()

    def update_tethered(self, ts):
        along = self.position - self.tethered.position
        if along.length2 > 900:
            # Force is proportional to length of along
            impulse = along * self.TETHER_FORCE * ts
            self.tethered.velocity += impulse / self.tethered.MASS
            self.velocity -= impulse / self.MASS

        # Apply damping to the relative velocity
        self.tethered.velocity -= self.TETHER_DAMPING * (self.tethered.velocity - self.velocity) * ts

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

        if self.tethered:
            self.update_tethered(ts)

        # Cap speed
        speed = self.velocity.length
        if speed > self.ship.max_speed:
            self.velocity *= self.ship.max_speed / speed

        # Constant acceleration formula
        self.position += 0.5 * (u + self.velocity) * ts

        self.do_collisions()

    def do_collisions(self):
        for o in self.world.collidable_objects:
            if o.colliding(self):
                o.on_collide(self)
                break

    def explode(self):
        Explosion(self.world, self.position)
        self.kill()
        self.world.dispatch_event('on_player_death')

    def kill(self):
        self.world.kill(self)
        self.release()
        self.alive = False

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
        Bullet(self.world, self.position, dir, self.velocity)

    def attach(self, other):
        self.tethered = other
        other.tethered_to = self

    def release(self):
        if self.tethered:
            self.tethered.tethered_to = None
            self.tethered = None


class Bullet(object):
    RADIUS = 5
    SPEED = 200

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
        for o in self.world.collidable_objects:
            if o.colliding(self):
                self.kill()
                if isinstance(o, Asteroid):
                    o.fragment()
                break

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
        TrackingLabel(
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
        for i in xrange(20):
            spawn_random_collectable(self)
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
        load_all()
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

    def on_key_press(self, symbol, modifiers):
        if symbol == key.Z:
            player = self.world.player
            if player.alive:
                if player.tethered:
                    player.release()
                else:
                    player.shoot()
            return EVENT_HANDLED

    def start(self):
        self.window.push_handlers(self.keyboard, on_draw=self.on_draw)
        self.window.push_handlers(self.on_key_press)
        pyglet.clock.schedule_interval(self.update, 1.0 / FPS)
        pyglet.app.run()

    def on_draw(self):
        self.window.clear()
        self.world.draw()

    def update(self, ts):
        self.world.update(ts)


if __name__ == '__main__':
    game = Game()
