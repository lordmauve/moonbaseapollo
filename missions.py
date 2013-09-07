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


# If true, print the script steps as they are being run
DEBUG_MISSIONS = False


message_sound = pyglet.resource.media('message.wav', streaming=False)
goal_sound = pyglet.resource.media('goal.wav', streaming=False)



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
        self.skipping = False

    def start(self):
        self.current = 0
        self.next()

    def wait(self, delay):
        if self.skipping:
            return
        if delay:
            pyglet.clock.schedule_once(self.next, delay)
        else:
            self.next()

    def next(self, *args):
        """Call the next callable."""
        if self.skipping:
            return

        try:
            f = self.callables[self.current]
        except IndexError:
            self.dispatch_event('on_finish')
        else:
            self.current += 1
            if DEBUG_MISSIONS:
                print f.func.__name__, f.args[1:], f.keywords
            f()

    def skip(self):
        self.skipping = True
        try:
            for f in self.callables[self.current:]:
                f()
        finally:
            self.skipping = False

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

        self.handlers_installed = False

    def setup(self, game):
        """Called to bind the game to the mission.

        Subclasses should not need to override this.

        """
        self.game = game
        self.world = game.world

        if not self.handlers_installed:
            self.world.push_handlers(
                self.on_object_shot, self.on_item_collected,
                self.on_object_tractored, self.on_region_entered,
                self.on_astronaut_death, self.on_object_destroyed,
                self.on_object_released
            )
            self.handlers_installed = True
        self.hud = self.game.world.hud

        # Set up clean state
        self.shot_messages = {}
        self.tractored_messages = {}
        self.region_message = None
        self.waiting_enter_region = False
        self.need_class = None
        self.must_tractor = None
        self.must_release = None
        self.must_earn = 0
        self.critical_objects = []
        self.target_objects = []
        self.extra_params = {}
        self.persistent_items = WeakSet()  # items to be killed if we restart
        self.nonpersistent_items = WeakSet()  # items to be killed at mission end

        # Clear any leftover messages
        self.hud.clear_messages()

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

    @script
    def say(self, message, colour=hud.DEFAULT_COLOUR, delay=3, sound=message_sound):
        """Record a message that will be shown on the message window."""
        self.game.say(message, colour=colour)
        sound.play()
        self.wait(delay)

    def goal(self, title):
        self.say("New mission: " + title, colour=GREEN, delay=0, sound=goal_sound)

    @script
    def spawn(self, *args, **kwargs):
        """Spawn a thing."""
        self.do_spawn(*args, **kwargs)

    @script
    def spawn_above_moonbase(self, class_name, *args, **kwargs):
        """Spawn a thing above the moonbase, wherever it may be right now."""
        moon = self.world.moon
        position = moon.position + v(0, 220).rotated(-moon.rotation)
        self.do_spawn(class_name, position, *args, **kwargs)

    def do_spawn(self, class_name, position, signpost=None, id=None, persistent=True, delay=0, **kwargs):
        # Destroy any existing instance that may exist
        if id:
            try:
                inst = self.world.get_by_id(id)
            except KeyError:
                pass
            else:
                self.world.kill(inst)

        module, clsname = class_name.rsplit('.', 1)
        __import__(module)
        cls = getattr(sys.modules[module], clsname)

        inst = cls(self.game.world, position=position, **kwargs)
        if signpost:
            if not isinstance(signpost, basestring):
                signpost = inst.name
            signpost = Signpost(self.game.world, signpost, inst, GOLD)
            self.nonpersistent_items.add(signpost)

        label = None
        if getattr(inst, 'name', None):
            label = TrackingLabel(self.world, inst.name, follow=inst)
            self.world.spawn(label)
            self.nonpersistent_items.add(label)

        if id:
            self.world.set_id(inst, id)
            self.extra_params[id] = inst

        if persistent:
            self.persistent_items.add(inst)
        else:
            self.nonpersistent_items.add(inst)
        self.wait(delay)

    @script
    def show_signpost(self, id, text=None):
        """Re-show a signpost for a persistent named object from a previous mission."""
        inst = self.world.get_by_id(id)
        text = text or inst.name
        signpost = Signpost(self.world, text, inst, GOLD)
        self.nonpersistent_items.add(signpost)
        self.next()

    @script
    def player_must_collect(self, class_name, number=1):
        """Wait for the player to collect number of the item denoted by class_name.

        class_name is a string of the form module.Class, so that no importing
        needs to occur to define the missions.

        """
        self.need_class = class_name
        self.needed = number

    @script
    def player_must_tractor(self, id):
        """Wait for the player to tractor the given item."""
        self.must_tractor = id

    @script
    def player_must_release(self, id):
        """Wait for the player to release the given item."""
        self.must_release = (id, None)

    @script
    def player_must_release_in_region(self, id, pos, radius):
        """Wait for the player to release the given item."""
        self.must_release = (id, (pos, radius))

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
        """Fail the mission if the object with the given id is destroyed."""
        self.critical_objects.append(id)
        self.next()

    @script
    def player_must_enter_region(self, position, radius):
        """Add a one-off message if the player enters a particular region."""
        self.waiting_enter_region = True
        self.world.set_target_region(position, radius)

    @script
    def player_must_destroy(self, id):
        """Wait for the player to destroy the object with the given id."""
        self.target_objects.append(id)

    @script
    def player_must_earn(self, credits):
        """Wait for player to earn certain number of credits"""
        self.must_earn = credits

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
        elif self.must_earn > 0:
            self.must_earn -= item.VALUE
            if self.must_earn <= 0:
                self.next()
            else:
                self.game.say('Good work! You need to collect %d more credits.' % self.must_earn)

    def on_object_shot(self, item):
        try:
            message, colour = self.shot_messages.pop(get_class_name(item))
        except KeyError:
            pass
        else:
            self.game.say(message, colour=colour)

    def on_object_destroyed(self, item):
        if not hasattr(item, 'id'):
            return

        if item.id in self.critical_objects:
            self.game.say("{control}: Mission critical object was destroyed!", colour=RED)
            self.dispatch_event("on_failure")
        elif item.id in self.target_objects:
            self.target_objects.pop(self.target_objects.index(item.id))
            if len(self.target_objects) == 0:
                self.game.say("{control}: All targets destroyed!")
                self.next()

    def on_object_tractored(self, item):
        try:
            message, colour = self.tractored_messages.pop(get_class_name(item))
        except KeyError:
            pass
        else:
            self.game.say(message, colour=colour)

        if self.must_tractor:
            if getattr(item, 'id', None) == self.must_tractor:
                self.must_tractor = None
                self.next()

    def on_object_released(self, item):
        if self.must_release:
            id, pos = self.must_release
            if getattr(item, 'id', None) == id:
                if pos:
                    # If a radius was specified, check we released within it
                    p, r = pos
                    if (item.position - p).length2 > r *r:
                        return
                self.must_release = None
                self.next()

    def on_astronaut_death(self, astronaut):
        self.game.say("{control}: Oh my god! You killed %s! You bastard!" % astronaut.name)

    def on_failure(self):
        self.game.say("{control}: Mission failed! Try again.", colour=RED)

    def finish(self):
        pyglet.clock.unschedule(self.next)
        pyglet.clock.unschedule(self.next)
        pyglet.clock.unschedule(self.on_clock_tick)
        self.clear_items()
        self.clear_time_limit()
        self.extra_params = {}
        self.world.clear_target_region()
        if self.handlers_installed:
            self.world.pop_handlers()
            self.handlers_installed = False

    def rewind(self):
        """Finish and revert state to before the mission."""
        self.finish()
        self.clear_items(False)

    def restart(self, *args):
        """Rewind to the start of the mission and then start it afresh."""
        self.rewind()
        self.setup(self.game)  # reinstate handlers
        self.start()

    def skip(self):
        """Skip the mission, but set any persistent state."""
        super(Mission, self).skip()
        self.hud.clear_messages()
        self.finish()


Mission.register_event_type('on_failure')

m = Mission('Diagnostics')
m.say("{control}: Stand by {name}, we're going to run some diagnostics.", delay=5)
m.say("{control}: Let's take you out for a spin. Head towards this marker.", delay=0)
m.goal('Move to the marker')
m.say('Hold LEFT/RIGHT to rotate. Hold UP to thrust.', colour=WHITE, delay=0)
m.spawn('objects.Marker', v(-300, 200), signpost='Waypoint', persistent=False)
m.player_must_collect('objects.Marker')
m.say("{control}: And now this one.")
m.spawn('objects.Marker', v(300, -200), signpost='Waypoint', persistent=False)
m.player_must_collect('objects.Marker')
m.say("{control}: {name}, your systems are looking good. You are mission ready!")


ICE_POS = v(1500, -1200)
m = Mission('Harvesting Ice')
m.say("{control}: We are all very thirsty down here. Can you find us a source of water?", delay=1)
m.say("You can harvest water from asteroids made of ice.", colour=WHITE, delay=2)
m.goal("Collect some ice")
m.spawn('objects.IceAsteroid', ICE_POS, signpost='Ice')
m.player_must_enter_region(ICE_POS, 400)
m.say('Press Z to shoot the asteroid.', colour=WHITE, delay=0)
m.say_if_object_shot('objects.IceAsteroid', 'Move your ship over an ice cube to grab it with your tractor beam.', colour=WHITE)
m.say_if_object_shot('objects.Asteroid', 'Be careful! Shooting rocks will blast out dangerous rock fragments.', colour=WHITE)
m.say_if_object_tractored('objects.Ice', 'Great! Now take this back to the moon base.', colour=WHITE)
m.say_if_region_entered(v(0, 0), 400, 'Dropping off cargo is best done very slowly and carefully. Press Z to release.', colour=WHITE)
m.player_must_collect('objects.Ice')
m.say("{control}: Delicious, anid ice cold too!")


CHEESE_POS = v(-1000, 800)
m = Mission('Collect some cheese!')
m.spawn('objects.CheeseAsteroid', CHEESE_POS, signpost='Anomaly')
m.say("{control}: {name}, our scans are picking up an anomalistic scent.", delay=1)
m.say("{control}: Please can you investigate and bring us back a sample?", delay=2)
m.goal("Investigate Strange Whiff")
m.player_must_enter_region(CHEESE_POS, 300)
m.say("{control}: Cheese! Well I never!")
m.say("{control}: We need enough for lunch.", delay=0)
m.goal("Collect 2 cheeses")
m.player_must_collect('objects.Cheese', 2)


STATION_POS = v(700, 4600)
def respawn_comm_station(m):
    m.spawn('objects.CommsStation', STATION_POS, signpost=True, id='comm-station-4', persistent=True)

m = Mission('Transport the astronaut')
m.say("{control}: Return to base, {name}, for your next mission.", delay=0)
m.player_must_enter_region(v(0, 0), 500)
m.spawn_above_moonbase('objects.Astronaut', id='astronaut', signpost=True, persistent=False, destination='comm-station-4')
m.say("{control}: This is {astronaut.name}.", delay=2)
respawn_comm_station(m)
m.say("{control}: {name}, please take {astronaut.name} to Comm Station 4.", delay=3)
m.goal('Transport {astronaut.name} to Comm Station 4')
m.say_if_object_tractored('objects.Astronaut', '{astronaut.name}: Fly safely, please?')
m.fail_if_object_destroyed(id='astronaut')
m.player_must_collect('objects.Astronaut')
m.say("{astronaut.name}: Thanks. I'm just going to go be sick now.")


m = Mission('Defend the station')
respawn_comm_station(m)
m.spawn('objects.DangerousAsteroid', STATION_POS + v(1000, 0), signpost='Asteroid', velocity=v(-20, 0), id='asteroid')
m.say('{control}: Emergency, {name}! An asteroid is heading for Comm Station 4', delay=1)
m.goal('Destroy the asteroid')
m.fail_if_object_destroyed('comm-station-4')
m.player_must_destroy('asteroid')
m.say('{control}: Thanks. Comm Station 4 is safe now.')


SPACEDOCK_POS = v(-3000, 1600)
m = Mission('Update ship')
m.say("{control}: Good news, {name}!", delay=0)
m.spawn('objects.SpaceDock', SPACEDOCK_POS)
m.fail_if_object_destroyed('lugger')
m.spawn('objects.Lugger', SPACEDOCK_POS + v(30, -35), signpost='Lugger 1', rotation=180, persistent=False, id='lugger')
m.say("{control}: A ship ugprade just arrived at space dock.", delay=1)
m.say("{control}: Go get it then!", delay=2)
m.goal('Collect new ship')
m.say_if_region_entered(SPACEDOCK_POS, 300, 'Manouver {name} to dock with Lugger 1.', colour=WHITE)
m.player_must_collect('objects.Lugger')
m.say('{control}: {lugger.name}, your callsign is now {name}.', delay=10)


m = Mission('Collect metal')
m.say("{control}: {name}, our fabrication facility is just about ready.", delay=0)
m.say("{control}: We want you to supply us with metal.", delay=1)
m.goal('Collect 4 metal')
for pos in random_positions(3):
    m.spawn('objects.MetalAsteroid', pos, signpost='Metal')
m.player_must_collect('objects.Metal', 4)
m.say("{control}: Thank you, {name}, we're firing up the furnaces.")


m = Mission('Retrieve supply drop')
m.say('{control}: {name}, we are expecting a resupply of frozen food from Earth.', delay=1.5)
m.say('{control}: We need you to collect it and guide it through the asteroid belt.')
m.spawn('objects.FrozenFood', v(-4500, 300), velocity=v(30, 0), signpost='Frozen Food Supplies', id='food')
m.fail_if_object_destroyed(id='food')
m.player_must_collect('objects.FrozenFood')
m.say('{control}: Delicious! They gave us a flake too!')


TARGET_POS = v(3000, -3000)
m = Mission('Launch Satellite')
m.fail_if_object_destroyed('satellite')
m.say("{control}: The metal you provided us has helped up build a satellite uplink.", delay=1)
m.spawn_above_moonbase('objects.Satellite', signpost=True, id='satellite', destination='nowhere')
m.say("{control}: Please can you get it into place for us?", delay=2)
m.goal('Pick up the satellite')
m.player_must_tractor('satellite')
m.say('{control}: We have picked out a spot where we would like you to set it up.', delay=1)
m.spawn('objects.FixedMarker', TARGET_POS, signpost='Target Site', persistent=False, id='marker')
m.player_must_enter_region(TARGET_POS, 300)
m.say("{control}: Anywhere here looks fine.", delay=0)
m.player_must_release_in_region('satellite', TARGET_POS, 600)
#m.destroy('marker')
m.say("{control}: Excellent, {satellite.name} is coming online. Readings look good.")


DROID_POS = v(-2630, 3000)
m = Mission('Destroy droid')
m.say("{control}: {name}, our mining droid CP-9 has stopped responding.", delay=1)
m.say("{control}: It is armed and dangerous! ", delay=3)
m.spawn('objects.Droid', DROID_POS, signpost='DROID CP-9', id='droid')
m.goal('Destroy a malfunctioning droid')
m.player_must_enter_region(DROID_POS, 200)
m.say("DROID CP-9: Enemy Approaching. ATTACK MODE ENABLED!", colour=RED, delay=1)
m.say("{control}: Looks like CP-9 is malfunctioning. Destroy it!", delay=2)
m.player_must_destroy('droid')
m.say("{control}: Thanks, we will ask all our droids to be retested")


m = Mission('Restock water')
m.say('{control}: Emergency {name}, our water reclamator has sprung a leak!', delay=1)
m.say('{control}: We need you to restock our water tanks before our plants die!', delay=2)
for p in random_positions(4):
    m.spawn('objects.IceAsteroid', p, signpost='Ice')
m.goal('Collect 6 Ice in 5 minutes')
with m.time_limit(300):
    m.player_must_collect('objects.Ice', 6)
m.say('{control}: Thanks, {name}. We think we have the leak under control now.')


SOLAR_FARM = v(-2000, -1300)
BATTERY = SOLAR_FARM + v(0, 65)
m = Mission("Collect battery from Solar Farm")
m.say("{control}: {name}, the base is running out of power.", delay=1)
m.say("{control}: Can you bring a battery pack from the Solar Farm?", delay=2)
m.spawn('objects.SolarFarm', SOLAR_FARM, signpost='Solar Farm')
m.goal("Collect battery pack")
m.player_must_enter_region(SOLAR_FARM, 200)
m.say("Solar Farm: Ahoy, {name}!", delay=0)
m.say("Solar Farm: One battery pack, full of juice!", delay=1)
m.spawn("objects.Battery", BATTERY, destination='moonbase', persistent=False)
m.say_if_object_tractored('objects.Battery', "Return battery pack to {control}", colour=GREEN)
m.player_must_collect('objects.Battery')
m.say("{control}: Thanks, we could have all died without power!")


m = Mission('Earn credits')
credits_needed = 100
m.say('{control}: {name}, we need to collect resources quickly.', delay=0)
m.say('{control}: Collect %d credits as soon as possible' % credits_needed,
      delay=1)
asteroid_types = [
    ('objects.IceAsteroid', 'Ice'),
    ('objects.CheeseAsteroid', 'Cheese'),
    ('objects.MetalAsteroid', 'Metal')
]
for p in random_positions(4):
    ast = random.choice(asteroid_types)
    m.spawn(ast[0], p, signpost=ast[1])
m.goal('Earn %d credits' % credits_needed)
m.player_must_earn(credits_needed)
m.say('{control}: Thanks, {name}. We think we have enough resources stocked now.')


# Next mission (draft)
#
m = Mission('Rescue an astronaut')
m.spawn('objects.Astronaut', STATION_POS + v(500, 500), velocity=v(30, 30), destination='comm-station-4', signpost=True, id='astronaut')
respawn_comm_station(m)
m.say('Comm Station 4: We have an emergency situation here, {name}.', delay=1)
m.fail_if_object_destroyed(id='astronaut')
m.say('Comm Station 4: {astronaut.name} got hit by an exhaust jet while on a space walk.', delay=1)
m.say('Comm Station 4: We need you to stage a rescue mission, FAST!', delay=0)
m.goal('Rescue {astronaut.name}')
with m.time_limit(100):
    m.player_must_tractor('astronaut')
m.show_signpost('comm-station-4')
m.say('Comm Station 4: We have a sick bay here. Hurry!', delay=0)
m.goal('Return {astronaut.name} to Comm Station 4')
with m.time_limit(100):
    m.player_must_collect('objects.Astronaut')
m.say('Comm Station 4: Stand by, {name}.', delay=10)
m.say("Comm Station 4: {astronaut.name} isn't breathing...", delay=0.5)
m.say("Comm Station 4: We need you to fetch adrenaline from {control}, stat!")
m.spawn_above_moonbase('objects.MedicalCrate', destination='comm-station-4', signpost="Medical crate", id='medicrate')
m.fail_if_object_destroyed(id='medicrate')
m.goal('Fetch medical supplies')
with m.time_limit(180):
    m.player_must_collect('objects.MedicalCrate')
m.say('Comm Station 4: Thanks, {name}.', delay=1)
m.say('Comm Station 4: Administering adrenaline.', delay=10)
m.say('{astronaut.name}: *gasps*', delay=1)
m.say('{astronaut.name}: What happened? How did I get here?')

