from wasabi.geom import v
import pyglet.clock
from pyglet.event import EventDispatcher


class Mission(EventDispatcher):
    def setup(self, game):
        """Called to bind the game to the mission.

        Subclasses should not need to override this.

        """
        self.game = game
        self.world = game.world

    def say(self, message):
        """Print a message."""
        self.game.say(message)

    def start(self):
        """Called when the mission starts.

        This might spawn objects, set up event handlers and timers, and so on.

        """

    def finish(self):
        """Clear any unwanted state, timers, etc.
        """
        self.world.hud.clear_messages()

    def draw(self):
        """Draw any mission-specific HUD etc."""

    def skip(self):
        """Skip the mission, but set any persistent state."""
        self.start()
        self.finish()


Mission.register_event_type('on_success')
Mission.register_event_type('on_failure')


class Preamble(Mission):
    def start(self):
        self.say("{control}: Stand by {name}, we're going to run some diagnostics.")
        pyglet.clock.schedule_once(
            lambda dt, game: game.say("{control}: {name}, your system readouts are green. You are go for mission."),
            6,
            self
        )
        pyglet.clock.schedule_once(
            lambda dt, game: game.next_mission(),
            6,
            self.game
        )


class Mission1(Mission):
    def start(self):
        from objects import IceAsteroid
        from labels import Signpost
        self.say('The base needs water.')
        a = IceAsteroid(self.world, v(1500, -1200))
        self.world.add_signpost(
            Signpost(self.world.camera, 'Ice', a),
        )

    def finish(self):
        self.world.hud.clear_messages()
        self.world.clear_signposts()


MISSIONS = [
    Preamble(),
    Mission1(),
]
