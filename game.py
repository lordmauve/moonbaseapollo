import math
from collections import namedtuple, defaultdict
from contextlib import contextmanager

import pyglet
from pyglet.window import key
from pyglet.event import EventDispatcher, EVENT_HANDLED
from pyglet import gl
from wasabi.geom import v
from wasabi.geom.poly import Rect
from wasabi.geom.spatialhash import SpatialHash

from loader import load_centred
from objects import Collider, Moon, Collidable, Collectable, spawn_random_asteroids, load_all, Asteroid, Collector
from effects import Explosion
from labels import TrackingLabel, Signpost, GREEN, GOLD, CYAN
from hud import HUD


WIDTH = 1024
HEIGHT = 600

FPS = 30


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


@contextmanager
def log_exceptions():
    """Suppress exceptions but print them to the console."""
    try:
        yield
    except Exception:
        import traceback
        traceback.print_exc()


class Player(Collider):
    ship_count = defaultdict(int)
    TETHER_FORCE = 0.5
    TETHER_DAMPING = 0.9

    COLGROUPS = 0x4
    COLMASK = 0xfffffffd

    def __init__(self, world, x, y, ship=CUTTER):
        self.world = world
        self.velocity = v(0.0, 5.0)
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
            colour=GREEN
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
        for o in self.iter_collisions():
            if isinstance(o, Collectable):
                if not self.tethered:
                    self.attach(o)
            else:
                self.explode()

            # Process only one collision
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
        self.release()
        self.world.dispatch_event('on_object_tractored', other)
        self.tethered = other
        other.tethered_to = self

    def release(self):
        if self.tethered:
            self.tethered.tethered_to = None
            self.tethered = None


class Bullet(Collider):
    RADIUS = 3
    SPEED = 200

    COLGROUPS = 0x8
    COLMASK = 0xfffffffd

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
        for o in self.iter_collisions():
            self.world.dispatch_event('on_object_shot', o)
            self.kill()
            if isinstance(o, Asteroid):
                o.fragment(self.position)
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
        self.non_collidable_objects = []
        self.spatial_hash = SpatialHash(cell_size=300.0)
        self.target_region = None

        self.money = 40

        self.camera = Camera()
        self.hud = HUD(WIDTH, HEIGHT)

        self.setup_projection_matrix()
        self.setup_world()

    def spawn_player(self):
        self.money -= 10
        self.hud.set_money(self.money)
        if self.money > 0:
            self.player = Player(self, 0, 180)
            self.camera.track(self.player)
        else:
            self.say("{control}: Not enough points to restart!")

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

        self.signposts = [Signpost(
            self.camera,
            'Moonbase Alpha',
            moon.moonbase
        )]
        self.spawn_player()
        self.hud.set_money(self.money)

    def spawn(self, o):
        self.objects.append(o)
        if isinstance(o, Collidable):
            self.spatial_hash.add_rect(o._fat_bounds, o)
            self.collidable_objects.append(o)
        else:
            self.non_collidable_objects.append(o)

    def kill(self, o):
        self.objects.remove(o)
        if isinstance(o, Collidable):
            self.spatial_hash.remove_rect(o._fat_bounds, o)
            self.collidable_objects.remove(o)
        else:
            self.non_collidable_objects.remove(o)

    def generate_asteroids(self):
        spawn_random_asteroids(self, 1000)
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
        for o in self.non_collidable_objects:
            o.update(ts)

        # Only update collidable objects near the camera
        vp = Rect.from_cwh(self.camera.position, 3000, 3000)
        culled = list(self.spatial_hash.potential_intersection(vp))
        for o in culled:
            o.update(ts)

        self.camera.track(self.player)

        if self.target_region and self.player.alive:
            position, radius2 = self.target_region
            if (self.player.position - position).length2 < radius2:
                self.dispatch_event('on_region_entered')
                self.clear_target_region()

    def draw(self):
        # draw a black background
        gl.glClearColor(0, 0, 0, 1)
        self.camera.set_matrix()

        vp = self.camera.get_viewport()
        culled = self.spatial_hash.potential_intersection(vp)
        for o in culled:
            o.draw()

        for o in self.non_collidable_objects:
            o.draw()

        for s in self.signposts:
            s.draw()
        self.hud.draw()

    def say(self, message, colour=CYAN):
        msg = message.format(
            name=self.player.name,
            control='Moonbase Alpha'
        )
        self.hud.append_message(msg, colour=colour)

    def add_signpost(self, s):
        self.signposts.append(s)

    def clear_signposts(self):
        del self.signposts[1:]

    def on_item_collected(self, collector, item):
        self.money += item.VALUE
        self.hud.set_money(self.money)

    def set_target_region(self, position, radius):
        """Set a circular target region.
        When entering this region, the on_region_entered event will be fired.
        """
        self.target_region = (position, radius * radius)

    def clear_target_region(self):
        self.target_region = None


World.register_event_type('on_player_death')
World.register_event_type('on_item_collected')
World.register_event_type('on_object_shot')
World.register_event_type('on_object_tractored')
World.register_event_type('on_region_entered')
World.register_event_type('on_astronaut_death')


class Game(object):
    def __init__(self):
        self.window = pyglet.window.Window(
            width=WIDTH,
            height=HEIGHT
        )
        self.keyboard = key.KeyStateHandler()

        # load the sprites for objects
        load_all()
        Bullet.load()

        # initialise the World and start the game
        self.world = World(self.keyboard)
        self.world.set_handler('on_player_death', self.on_player_death)
        self.mission = None
        self.mission_number = 0
        self.start()

    def on_player_death(self):
        # Wait a couple of seconds then respawn the player
        pyglet.clock.schedule_once(self.respawn, 2)

    def say(self, message, colour=CYAN):
        params = dict(
            name=self.world.player.name,
            control='Moonbase Alpha'
        )
        if self.mission:
            params.update(self.mission.extra_params)
        msg = message.format(**params)
        self.world.hud.append_message(msg, colour=colour)

    def respawn(self, *args):
        self.world.spawn_player()
        if self.world.player.alive:
            self.say("{control}: Please treat this one more carefully!")

    def on_key_press(self, symbol, modifiers):
        if symbol == key.Z:
            player = self.world.player
            if player.alive:
                if player.tethered:
                    player.release()
                else:
                    player.shoot()
            return EVENT_HANDLED
        elif symbol == key.F3:
            self.next_mission()
        elif symbol == key.F4:
            self.previous_mission()
        elif symbol == key.F5:
            self.reload_missions()

    def reload_missions(self):
        if self.mission:
            with log_exceptions():
                self.mission.rewind()
        try:
            import missions
            reload(missions)
        except Exception:
            import traceback
            traceback.print_exc()
        else:
            print 'Missions reloaded'
            self.restart_mission()

    def restart_mission(self, *args):
        if self.mission:
            with log_exceptions():
                self.mission.finish()

        self.start_mission()

    def start_mission(self, *args):
        # Cancel the next mission event if we got here by key press
        pyglet.clock.unschedule(self.next_mission)

        # Start mission
        with log_exceptions():
            # Gracefully handle exceptions loading missions
            # to allow for it to be reloaded

            import missions
            try:
                self.mission = missions.MISSIONS[self.mission_number]
            except IndexError:
                self.say('Well done! You have completed the game!', colour=GOLD)
            else:
                self.mission.setup(self)
                self.mission.start()
                self.mission.set_handler('on_finish', self.on_mission_finish)

    def on_mission_finish(self):
        self.say('Mission complete!', colour=GOLD)
        pyglet.clock.schedule(self.next_mission, 5)

    def next_mission(self, *args):
        self.mission_number += 1
        print "Skipping to next mission"
        if self.mission:
            with log_exceptions():
                self.mission.finish()
        self.start_mission()

    def previous_mission(self, *args):
        self.mission_number = max(0, self.mission_number - 1)
        print "Skipping to previous mission"
        if self.mission:
            with log_exceptions():
                self.mission.rewind()
        self.start_mission()

    def start(self):
        self.window.push_handlers(self.keyboard, on_draw=self.on_draw)
        self.window.push_handlers(self.on_key_press)
        pyglet.clock.schedule_interval(self.update, 1.0 / FPS)
        self.start_mission()

        while True:
            try:
                pyglet.app.run()
            except Exception:
                import traceback
                traceback.print_exc()
            else:
                break

    def on_draw(self):
        self.window.clear()
        self.world.draw()

    def update(self, ts):
        self.world.update(ts)


if __name__ == '__main__':
    game = Game()
