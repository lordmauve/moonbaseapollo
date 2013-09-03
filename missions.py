import sys
import random
from contextlib import contextmanager
from functools import wraps, partial
from wasabi.geom import v
import pyglet.clock
from pyglet.event import EventDispatcher
from labels import Signpost, TrackingLabel, GOLD, GREEN, WHITE, RED
from weakref import WeakSet
import hud


def random_positions(num, average_range=1000, standard_deviation=400):
    """Yield num random positions"""
    while num:
        dist = random.normalvariate(average_range, standard_deviation)
        if dist < 600:
            continue
        angle = random.random() * 360
        yield v(dist, 0).rotated(angle)
        num -= 1


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
        self.critical_objects = []
        self.extra_params = {}
        self.persistent_items = WeakSet()  # items to be killed if we restart
        self.nonpersistent_items = WeakSet()  # items to be killed at mission end

    def setup(self, game):
        """Called to bind the game to the mission.

        Subclasses should not need to override this.

        """
        self.game = game
        self.world = game.world
        self.world.push_handlers(
            self.on_object_shot, self.on_item_collected,
            self.on_object_tractored, self.on_region_entered,
            self.on_astronaut_death, self.on_object_destroyed,
        )
        self.hud = self.game.world.hud

    def clear_items(self, nonpersistent_only=True):
        items = list(self.nonpersistent_items)
        self.nonpersistent_items.clear()
        if not nonpersistent_only:
            items.extend(self.persistent_items)
            self.persistent_items.clear()
        for o in items:
            try:
                o.kill()
            except Exception:
                # doesn't matter if it's already dead
                try:
                    self.world.kill(o)
                except Exception:
                    pass

    def restart(self):
        self.clear_items(False)
        self.start()

    @script
    def say(self, message, colour=hud.DEFAULT_COLOUR, delay=3):
        """Record a message that will be shown on the message window."""
        self.game.say(message, colour=colour)
        self.wait(delay)

    def goal(self, title):
        self.say("New mission: " + title, colour=GREEN, delay=0)

    @script
    def spawn(self, class_name, position, signpost=None, id=None, persistent=True, delay=0, **kwargs):
        module, clsname = class_name.rsplit('.', 1)
        __import__(module)
        cls = getattr(sys.modules[module], clsname)

        inst = cls(self.game.world, position=position, **kwargs)
        if signpost:
            if not isinstance(signpost, basestring):
                signpost = inst.name
            self.game.world.add_signpost(
                Signpost(self.game.world.camera, signpost, inst, GOLD)
            )

        label = None
        if getattr(inst, 'name', None):
            label = TrackingLabel(self.world, inst.name, follow=inst)
            self.world.spawn(label)

        if id:
            inst.id = id
            self.extra_params[id] = inst

        if persistent:
            self.persistent_items.add(inst)
        else:
            self.nonpersistent_items.add(inst)
        if label:
            self.nonpersistent_items.add(label)

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
    def fail_if_object_destroyed(self, id):
        self.critical_objects.append(id)

    @script
    def player_must_enter_region(self, position, radius):
        """Add a one-off message if the player enters a particular region."""
        self.waiting_enter_region = True
        self.world.set_target_region(position, radius)

    @script
    def set_time_limit(self, t):
        """Set a time limit to complete the next activity."""
        self.time_limit = int(t)
        self.hud.set_countdown(self.time_limit)
        pyglet.clock.schedule_interval(self.on_clock_tick, 1)
        self.next()

    @script
    def clear_time_limit(self):
        """Set a time limit to complete the next activity."""
        pyglet.clock.unschedule(self.on_clock_tick)
        self.hud.clear_countdown()
        self.next()

    @contextmanager
    def time_limit(self, t):
        self.set_time_limit(t)
        yield
        self.clear_time_limit()

    def on_clock_tick(self, dt):
        self.time_limit -= 1
        if self.time_limit < 0:
            self.hud.clear_countdown()
            pyglet.clock.unschedule(self.on_clock_tick)
            self.game.say('You ran out of time!', colour=RED)
            self.dispatch_event('on_failure')
        else:
            self.hud.set_countdown(self.time_limit)

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
            else:
                self.game.say('Good work! You need to collect %d more.' % self.needed, colour=GREEN)

    def on_object_shot(self, item):
        try:
            message, colour = self.shot_messages.pop(get_class_name(item))
        except KeyError:
            pass
        else:
            self.game.say(message, colour=colour)

    def on_object_destroyed(self, item):
        self.game.say("{control}: Mission critical object was destroyed!", colour=RED)
        self.dispatch_event("on_failure")

    def on_object_tractored(self, item):
        try:
            message, colour = self.tractored_messages.pop(get_class_name(item))
        except KeyError:
            pass
        else:
            self.game.say(message, colour=colour)

    def on_astronaut_death(self, astronaut):
        self.game.say("{control}: Oh my god! You killed %s! You bastard!" % astronaut.name)
        # self.dispatch_event('on_failure')

    def on_failure(self):
        self.game.say("{control}: Mission failed! Try again.", colour=RED)
        self.restart()

    def finish(self):
        pyglet.clock.unschedule(self.next)
        self.clear_items()
        self.extra_params = {}
        self.world.clear_target_region()
        self.world.pop_handlers()
        self.world.clear_signposts()

    def rewind(self):
        """Finish and revert state to before the mission."""
        self.finish()
        self.clear_items(False)

    def skip(self):
        """Skip the mission, but set any persistent state."""
        self.start()
        # TODO
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


STATION_POS = v(1000, 3000)
m = Mission('Transport the astronaut')
m.say("{control}: Return to base, {name}, for your next mission.", delay=0)
m.player_must_enter_region(v(0, 0), 300)
m.spawn('objects.Astronaut', v(160, 160), id='astronaut', signpost=True, persistent=False, destination='comm-station-4')
m.say("{control}: This is {astronaut.name}.")
m.spawn('objects.CommsStation', STATION_POS, signpost='Comm Station 4', id='comm-station-4')
m.say("{control}: {name}, please take {astronaut.name} to Comm Station 4.")
m.goal('Transport {astronaut.name} to Comm Station 4')
m.player_must_collect('objects.Astronaut')
m.fail_if_object_destroyed(id='astronaut')
m.say("{astronaut.name}: Thanks. I'm just going to go be sick now.")


# TODO!
#m = Mission('Defend the station')
#m.spawn('objects.Asteroid', STATION_POS + v(1000, 0), signpost='Asteroid', velocity=v(-20, 0), id='asteroid')
#m.say('{control}: Emergency, {name}! An asteroid is heading for Comm Station 4')
#m.goal('Destroy the asteroid')
#m.player_must_destroy('asteroid')


m = Mission('Collect metal')
m.say("{control}: {name}, our fabrication facility is just about ready.")
m.say("{control}: We want you to supply us with metal.")
m.goal('Collect 4 metal')
for pos in random_positions(3):
    m.spawn('objects.MetalAsteroid', pos, signpost='Metal')
m.player_must_collect('objects.Metal', 4)
m.say("{control}: Thank you, {name}, we're firing up the furnaces.")


m = Mission('Retrieve supply drop')
m.say('{control}: {name}, we are expecting a resupply of frozen food from Earth.', delay=1.5)
m.say('{control}: We need you to collect it and guide it through the asteroid belt.')
m.spawn('objects.FrozenFood', v(-2500, -300), velocity=v(30, 0), signpost='Frozen Food Supplies')
m.player_must_collect('objects.FrozenFood')
m.say('{control}: Delicious! They gave us a flake too!')


m = Mission('Restock water')
m.say('{control}: Emergency {name}, our water reclamator has sprung a leak!')
m.say('{control}: We need you to restock our water tanks before our plants die!', delay=1)
for p in random_positions(4):
    m.spawn('objects.IceAsteroid', p, signpost='Ice')
m.goal('Collect 6 Ice in 5 minutes')
with m.time_limit(300):
    m.player_must_collect('objects.Ice', 6)
m.say('{control}: Thanks, {name}. We think we have the leak under control now.')
