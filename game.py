import pyglet
from pyglet.window import key


WIDTH = 1024
HEIGHT = 600

FPS = 30


class World(object):
    def __init__(self):
        self.asteroids = []
        self.colonies = []

    def on_key_press(self, symbol, modifiers):
        if symbol == key.UP:
            print "UP"
        elif symbol == key.DOWN:
            print "DOWN"
        elif symbol == key.LEFT:
            print "LEFT"
        elif symbol == key.RIGHT:
            print "RIGHT"
        else:
            print symbol, modifiers


class Game(object):
    def __init__(self):
        self.window = pyglet.window.Window(
            width=WIDTH,
            height=HEIGHT
        )
        self.world = World()
        self.start()

    def start(self):
        self.window.push_handlers(on_key_press=self.on_key_press)
        pyglet.clock.schedule_interval(self.update, 1.0 / FPS)
        pyglet.app.run()

    def on_key_press(self, symbol, modifiers):
        self.world.on_key_press(symbol, modifiers)

    def update(self, ts):
        pass


if __name__ == '__main__':
    game = Game()
