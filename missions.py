import sys
from functools import wraps, partial
from wasabi.geom import v
import pyglet.clock
from pyglet.event import EventDispatcher
from labels import Signpost, GOLD
import hud


def script(func):
    """Decorator so that method calls build a script instead of calling it directly."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.callables.append(partial(func, self, *args, **kwargs))
    return wrapper


class Script(EventDispatcher):
    def __init__(self):
        self.callables = []
        self.current = 0

    def start(self):
        self.current = 0
        self.next()

    def wait(self, delay):
        if delay:
            pyglet.clock.schedule_once(self.next, delay)
        else:
            self.next()

    def next(self, *args):
        """Call the next callable."""
        try:
            f = self.callables[self.current]
        except IndexError:
            self.dispatch_event('on_finish')
        else:
            self.current += 1
            f()

Script.register_event_type('on_finish')

MISSIONS = []


class Mission(Script):
    """Configure the game to run a mission."""
    def __init__(self, name):
        self.name = name
        super(Mission, self).__init__()
        MISSIONS.append(self)

    def setup(self, game):
        """Called to bind the game to the mission.

        Subclasses should not need to override this.

        """
        self.game = game
        self.world = game.world

    @script
    def say(self, message, colour=hud.DEFAULT_COLOUR, delay=2):
        """Record a message that will be shown on the message window."""
        self.game.say(message)
        self.wait(delay)

    @script
    def spawn(self, class_name, position, signpost=None, delay=0):
        module, clsname = class_name.rsplit('.', 1)
        __import__(module)
        cls = getattr(sys.modules[module], clsname)

        inst = cls(self.game.world, position=position)
        if signpost:
            self.game.world.add_signpost(
                Signpost(self.game.world.camera, signpost, inst, GOLD)
            )
        self.wait(delay)

    @script
    def player_must_collect(self, class_name, number=1):
        """Wait for the player to collect number of the item denoted by class_name.

        class_name is a string of the form module.Class, so that no importing
        needs to occur to define the missions.

        """
        self.need_class = class_name
        self.needed = number
        self.game.world.set_handler('on_item_collected', self.on_item_collected)

    def on_item_collected(self, collector, item):
        name = '%s.%s' % (
            item.__class__.__module__,
            item.__class__.__name__
        )
        if name == self.need_class:
            self.needed -= 1
            if self.needed <= 0:
                self.next()

    def finish(self):
        self.world.hud.clear_messages()
        self.world.clear_signposts()

    def skip(self):
        """Skip the mission, but set any persistent state."""
        self.start()
        self.finish()


Mission.register_event_type('on_failure')


m = Mission('Preamble')
m.say("{control}: Stand by {name}, we're going to run some diagnostics.")
m.say("{control}: {name}, your system readouts are green. You are go for mission.")


m = Mission('Harvesting Ice')
m.say("{control}: The base needs water.")
m.spawn('objects.IceAsteroid', v(1500, -1200), signpost='Ice')
m.say("{control}: You can harvest water from asteroids made of ice.")
m.player_must_collect('objects.Ice')
