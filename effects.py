import pyglet
import pyglet.sprite
from loader import load_centred
from wasabi.geom import v

from particles import StaticEmitter, explosion_particles, Particle, domain


explosion_sound = pyglet.resource.media('space-explosion.wav', streaming=False)


class Explosion(object):
    MAX_AGE = 0.6
    MIN_SCALE = 0.1
    EXPANSION = 5.0

    @classmethod
    def load(cls):
        if not hasattr(cls, 'img'):
            cls.img = load_centred('explosion')

    def __init__(self, world, position, particle_colour=(0.6, 0.6, 0.6), particle_amount=0):
        self.world = world
        self.position = v(position)
        self.load()
        self.age = 0
        self.sprite = pyglet.sprite.Sprite(self.img)
        self.sprite.position = self.position
        self.sprite.scale = self.MIN_SCALE
        self.world.spawn(self)
        sound = explosion_sound.play()
        x, y = self.position - self.world.player.position
        sound.position = x, y, 0.0
        sound.min_distance = 300
        if particle_amount:
            self.spawn_particles(particle_colour, particle_amount)
        else:
            self.emitter = None

    def spawn_particles(self, particle_colour, particle_amount):
        self.emitter = StaticEmitter(
            template=Particle(
                position=tuple(self.position) + (0,),
                color=particle_colour
            ),
            size=domain.Line(
                (10, 10, 0),
                (3, 3, 0),
            ),
            rotation=domain.Line(
                (0, 0, -10),
                (0, 0, 10),
            ),
            velocity=domain.Disc(
                (0, 0, 0),
                (0, 0, 1),
                100,
                40
            ),
            rate=particle_amount * 10
        )
        explosion_particles.bind_controller(self.emitter)

    def draw(self):
        self.sprite.draw()

    def update(self, ts):
        self.age += ts
        if self.age > 0.1 and self.emitter:
            explosion_particles.unbind_controller(self.emitter)
            self.emitter = None
        if self.age > self.MAX_AGE:
            self.world.kill(self)
        self.sprite.scale = self.MIN_SCALE + self.age * self.EXPANSION
        self.sprite.opacity = int(255 * (1 - (self.age / self.MAX_AGE)))

