try:
    from lepton.system import ParticleSystem
    from lepton.renderer import BillboardRenderer
    from lepton.texturizer import SpriteTexturizer
    from lepton.group import ParticleGroup
    from lepton.emitter import StaticEmitter
    from lepton import controller
    from lepton import domain
    from lepton import Particle
    import lepton
except ImportError:
    print "You don't have lepton installed... you won't see all our cool particle effects."""

    class Mock(object):
        """Cheap and dirty mock class."""
        def __call__(self, *args, **kwargs):
            return self

        def __getattr__(self, key):
            return self

    # Mock out all the neat lepton stuff
    Particle = Mock()
    ParticleGroup = Mock()
    controller = Mock()
    domain = Mock()
    StaticEmitter = Mock()
    BillboardRenderer = Mock()
    SpriteTexturizer = Mock()
    particle_system = Mock()
    load_texture = Mock()
else:
    import pyglet.resource
    load_texture = pyglet.resource.texture
    particle_system = lepton.default_system


# We should now be able to define all the particle engine stuff
# without code changes to the rest of the game
exhaust = load_texture('exhaust.png')

exhaust_particles = ParticleGroup(
    controllers=[
        controller.Movement(),
        controller.Lifetime(1),
        controller.ColorBlender([
            (0.0, (1.0, 0.3, 0.3, 0.3)),
            (0.2, (1.0, 0.8, 0.3, 0.3)),
            (0.5, (1.0, 1.0, 1.0, 0.2)),
            (1.0, (1.0, 1.0, 1.0, 0.0)),
        ]),
        controller.Growth(-3)
    ],
    renderer=BillboardRenderer(
        SpriteTexturizer(exhaust.id)
    ),
)


explosion_particles = ParticleGroup(
    controllers=[
        controller.Movement(),
        controller.Lifetime(2),
        controller.Fader(
            start_alpha=1,
            fade_out_start=1,
            fade_out_end=2,
            end_alpha=0.0
        )
    ],
    renderer=BillboardRenderer(
        SpriteTexturizer(exhaust.id)
    ),
)
