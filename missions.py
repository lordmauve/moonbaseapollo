import sys
import random
from functools import wraps, partial
from wasabi.geom import v
import pyglet.clock
from pyglet.event import EventDispatcher
from labels import Signpost, TrackingLabel, GOLD, GREEN, WHITE, RED
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
        self.region_message = None
        self.waiting_enter_region = False
        self.need_class = None
        self.extra_params = {}

    def setup(self, game):
        """Called to bind the game to the mission.

        Subclasses should not need to override this.

        """
        self.game = game
        self.world = game.world
        self.world.push_handlers(
            self.on_object_shot, self.on_item_collected, self.on_object_tractored,
            self.on_region_entered, self.on_astronaut_death
        )

    @script
    def say(self, message, colour=hud.DEFAULT_COLOUR, delay=3):
        """Record a message that will be shown on the message window."""
        self.game.say(message, colour=colour)
        self.wait(delay)

    def goal(self, title):
        self.say("New mission: " + title, colour=GREEN, delay=0)

    @script
    def spawn(self, class_name, position, signpost=None, id=None, delay=0):
        module, clsname = class_name.rsplit('.', 1)
        __import__(module)
        cls = getattr(sys.modules[module], clsname)

        inst = cls(self.game.world, position=position)
        if signpost:
            self.game.world.add_signpost(
                Signpost(self.game.world.camera, signpost, inst, GOLD)
            )

        if getattr(inst, 'name', None):
            self.world.spawn(
                TrackingLabel(self.world, inst.name, follow=inst)
            )

        if id:
            self.extra_params[id] = inst

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

    @script
    def say_if_region_entered(self, position, radius, message, colour=hud.DEFAULT_COLOUR):
        """Add a one-off message if the player enters a particular region."""
        self.world.set_target_region(position, radius)
        self.region_message = (message, colour)
        self.next()

    @script
    def player_must_enter_region(self, position, radius):
        """Add a one-off message if the player enters a particular region."""
        self.waiting_enter_region = True
        self.world.set_target_region(position, radius)

    def on_region_entered(self):
        if self.region_message:
            self.game.say(*self.region_message)
            self.region_message = None

        if self.waiting_enter_region:
            self.waiting_enter_region = False
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

    def on_astronaut_death(self, astronaut):
        self.game.say("{control}: Oh my god! You killed %s! You bastard!" % astronaut.name)
        self.dispatch_event('on_failure')

    def on_failure(self):
        self.game.say("{control}: Mission failed! Try again.", colour=RED)
        self.start()

    def finish(self):
        pyglet.clock.unschedule(self.next)
        self.extra_params = {}
        self.world.clear_target_region()
        self.world.pop_handlers()
        self.world.clear_signposts()

    def skip(self):
        """Skip the mission, but set any persistent state."""
        self.start()
        self.finish()


Mission.register_event_type('on_failure')


ICE_POS = v(1500, -1200)
m = Mission('Harvesting Ice')
m.say("{control}: Stand by {name}, we're going to run some diagnostics.", delay=6)
m.say("{control}: {name}, your system readouts are green. You are go for mission.")
m.say("{control}: We are all very thirsty down here. Can you find us a source of water?")
m.say("You can harvest water from asteroids made of ice.", colour=WHITE, delay=0)
m.goal("Collect some ice")
m.spawn('objects.IceAsteroid', ICE_POS, signpost='Ice')
m.player_must_enter_region(ICE_POS, 400)
m.say('Press Z to shoot the asteroid.', colour=WHITE)
m.say_if_object_shot('objects.IceAsteroid', 'Move your ship over an ice cube to collect it.', colour=WHITE)
m.say_if_object_shot('objects.Asteroid', 'Be careful! Shooting rocks will blast out dangerous rock fragments.', colour=WHITE)
m.say_if_object_tractored('objects.Ice', 'Great! Now take this back to the moon base.', colour=WHITE)
m.say_if_region_entered(v(0, 0), 400, 'Dropping off cargo is best done very slowly and carefully. Press Z to release.', colour=WHITE)
m.player_must_collect('objects.Ice')
m.say("{control}: Delicious, anid ice cold too!")


CHEESE_POS = v(-1000, 800)
m = Mission('Collect some cheese!')
m.spawn('objects.CheeseAsteroid', CHEESE_POS, signpost='Anomaly')
m.say("{control}: {name}, our scans are picking up an anomalistic scent.")
m.say("{control}: Please can you investigate and bring us back a sample?", delay=0)
m.goal("Investigate Strange Whiff")
m.player_must_enter_region(CHEESE_POS, 300)
m.say("{control}: Cheese! Well I never!")
m.say("{control}: We need enough for lunch.", delay=0)
m.goal("Collect 2 cheeses")
m.player_must_collect('objects.Cheese', 2)


m = Mission('Transport the astronaut')
m.say("{control}: Return to base, {name}, for your next mission.", delay=0)
m.player_must_enter_region(v(0, 0), 300)
m.spawn('objects.Astronaut', v(160, 160), id='astronaut')
m.say("{control}: This is {astronaut.name}.")
m.say("{control}: {name}, please take {astronaut.name} to Comm Station 4.")
m.player_must_enter_region(CHEESE_POS, 300)
