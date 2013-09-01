import random
import math
import pyglet
from pyglet.window import key
from pyglet import gl
from wasabi.geom import v
from loader import load_centred

from objects import Moonbase

WIDTH = 1024
HEIGHT = 600

FPS = 30

# Set up pyglet resource loader
pyglet.resource.path += [
    'sprites/',
    'fonts/',
]
pyglet.resource.reindex()


class Asteroid(object):
    @classmethod
    def load(cls):
        if not hasattr(cls, 'ASTEROID1'):
            cls.ASTEROID1 = load_centred('asteroid')

    @classmethod
    def random(cls, world):
        x = random.random() * (WIDTH - 100) + 50
        y = random.random() * (HEIGHT - 100) + 50
        img = random.choice((cls.ASTEROID1,))
        return cls(world, x, y, img)

    @property
    def pos(self):
        return v(self.x, self.y)

    def __init__(self, world, x, y, img):
        self.world = world
        self.x = x
        self.y = y
        self.sprite = pyglet.sprite.Sprite(img)
        self.sprite.position = x, y
        # self.sprite.scale = scale
        self.sprite.rotation = random.random() * 360
        self.angular_velocity = (random.random() - 0.5) * 60

    def draw(self):
        self.sprite.draw()

    def update(self, ts):
        self.sprite.rotation += self.angular_velocity * ts


class Player(object):
    @classmethod
    def load(cls):
        if hasattr(cls, 'CUTTER'):
            return
        cls.CUTTER = load_centred('cutter')

    def __init__(self, world, x, y, ship_type='CUTTER'):
        self.world = world
        self.x = x
        self.y = y
        self.sprite = pyglet.sprite.Sprite(getattr(Player, ship_type))
        self.sprite.position = x, y
        # self.sprite.scale = scale
        self.sprite.rotation = random.random() * 360

    def draw(self):
        self.sprite.draw()

    def update(self, ts):
        if self.world.keyboard[key.UP]:
            self.move(forward=True)
        if self.world.keyboard[key.DOWN]:
            self.move(forward=False)
        if self.world.keyboard[key.LEFT]:
            self.rotate(clockwise=False)
        if self.world.keyboard[key.RIGHT]:
            self.rotate(clockwise=True)

    def rotate(self, clockwise=True):
        direction = 1 if clockwise else -1
        self.sprite.rotation += direction * 5

    def move(self, forward=True):
        direction = 1 if forward else -1
        speed = 25
        rotation = math.radians(self.sprite.rotation)
        self.sprite.x += direction * math.sin(rotation) * speed
        self.sprite.y += direction * math.cos(rotation) * speed


class Camera(object):
    def __init__(self, pos=v(0, 0)):
        self.pos = pos
        self.offset = v(WIDTH * -0.5, HEIGHT * -0.5)

    def set_matrix(self):
        x, y = self.pos + self.offset
        gl.glLoadIdentity()
        gl.glTranslatef(-x, -y, 0)


class World(object):
    def __init__(self, keyboard):
        self.keyboard = keyboard
        self.objects = []

        self.camera = Camera()
        self.setup_projection_matrix()
        self.setup_world()

    def setup_world(self):
        """Create the initial world."""
        self.generate_asteroids()
        self.objects.append(Moonbase(self))
        self.player = Player(self, 0, 200)

    def generate_asteroids(self):
        while len(self.objects) < 5:
            ast = Asteroid.random(self)
            self.objects.append(ast)
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
        self.player.update(ts)
        self.camera.pos = self.player.sprite.position
        for o in self.objects:
            o.update(ts)

    def draw(self):
        # draw a black background
        gl.glClearColor(0, 0, 0, 1)
        self.camera.set_matrix()

        for o in self.objects:
            o.draw()
        self.player.draw()


class Game(object):
    def __init__(self):
        self.window = pyglet.window.Window(
            width=WIDTH,
            height=HEIGHT
        )
        self.keyboard = key.KeyStateHandler()

        # load the sprites for objects
        Asteroid.load()
        Player.load()

        # initialise the World and start the game
        self.world = World(self.keyboard)
        self.start()

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
