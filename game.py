import random
import pyglet
from pyglet.window import key
from wasabi.geom import v

WIDTH = 1024
HEIGHT = 600

FPS = 30

# Set up pyglet resource loader
pyglet.resource.path += [
    'sprites/',
    'fonts/',
]
pyglet.resource.reindex()


def make_centred(image):
    w = image.width
    h = image.height
    image.anchor_x = w // 2
    image.anchor_y = h // 2
    return image


def load_centred(img):
    return make_centred(pyglet.image.load('sprites/%s.png' % img))


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

    def draw(self):
        self.sprite.draw()

    def update(self, ts):
        pass


class World(object):
    def __init__(self, keyboard):
        self.keyboard = keyboard
        self.objects = []
        self.generate_asteroids()

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

    def update_player(self, ts):
        if self.keyboard[key.UP]:
            print "UP"
        if self.keyboard[key.DOWN]:
            print "DOWN"
        if self.keyboard[key.LEFT]:
            print "LEFT"
        if self.keyboard[key.RIGHT]:
            print "RIGHT"

    def update(self, ts):
        self.update_player(ts)
        for o in self.objects:
            o.update(ts)

    def draw(self):
        # draw a black background
        pyglet.gl.glClearColor(0, 0, 0, 1)

        for o in self.objects:
            o.draw()


class Game(object):
    def __init__(self):
        self.window = pyglet.window.Window(
            width=WIDTH,
            height=HEIGHT
        )
        self.keyboard = key.KeyStateHandler()
        Asteroid.load()
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
