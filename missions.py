import sys
from functools import wraps, partial
from wasabi.geom import v
import pyglet.clock
from pyglet.event import EventDispatcher
from labels import Signpost, GOLD, GREEN
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


def get_class_name(inst):
    return '%s.%s' % (
        inst.__class__.__module__,
        inst.__class__.__name__
    )


class Mission(Script):
    """Configure the game to run a mission."""
    def __init__(self, name):
        self.name = name
        super(Mission, self).__init__()
        MISSIONS.append(self)
        self.shot_messages = {}
        self.tractored_messages = {}

    def setup(self, game):
        """Called to bind the game to the mission.

        Subclasses should not need to override this.

        """
        self.game = game
        self.world = game.world
        self.world.push_handlers(
            self.on_object_shot, self.on_item_collected, self.on_object_tractored
        )

    @script
    def say(self, message, colour=hud.DEFAULT_COLOUR, delay=3):
        """Record a message that will be shown on the message window."""
        self.game.say(message, colour=colour)
        self.wait(delay)

    def goal(self, title):
        self.say("New mission: " + title, colour=GREEN, delay=0)

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

    @script
    def say_if_object_shot(self, class_name, message, colour=hud.DEFAULT_COLOUR):
        """Add a one-off message if an object of a given class is shot."""
        self.shot_messages[class_name] = (message, colour)
        self.next()

    @script
    def say_if_object_tractored(self, class_name, message, colour=hud.DEFAULT_COLOUR):
        """Add a one-off message if an object of a given class is tractored."""
        self.tractored_messages[class_name] = (message, colour)
        self.next()

    def on_item_collected(self, collector, item):
        if get_class_name(item) == self.need_class:
            self.needed -= 1
            if self.needed <= 0:
                self.need_class = None
                self.next()

    def on_object_shot(self, item):
        try:
            message, colour = self.shot_messages.pop(get_class_name(item))
        except KeyError:
            pass
        else:
            self.game.say(message, colour=colour)

    def on_object_tractored(self, item):
        try:
            message, colour = self.tractored_messages.pop(get_class_name(item))
        except KeyError:
            pass
        else:
            self.game.say(message, colour=colour)

    def finish(self):
        pyglet.clock.unschedule(self.next)
        self.world.pop_handlers()
        self.world.hud.clear_messages()
        self.world.clear_signposts()

    def skip(self):
        """Skip the mission, but set any persistent state."""
        self.start()
        self.finish()


Mission.register_event_type('on_failure')


m = Mission('Harvesting Ice')
m.say("{control}: Stand by {name}, we're going to run some diagnostics.", delay=6)
m.say("{control}: {name}, your system readouts are green. You are go for mission.")
m.say("{control}: The base needs water.")
m.say("{control}: You can harvest water from asteroids made of ice.")
m.goal("Collect some ice")
m.spawn('objects.IceAsteroid', v(1500, -1200), signpost='Ice')
m.say_if_object_shot('objects.IceAsteroid', 'Move your ship over an ice cube to collect it.')
m.say_if_object_shot('objects.Asteroid', 'Be careful! Shooting rocks will blast out dangerous rock fragments.')
m.say_if_object_tractored('objects.Ice', 'Great! Now take this back to the moon base. Press Z to release.')
m.player_must_collect('objects.Ice')
