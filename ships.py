from collections import namedtuple
from labels import GREEN, RED, YELLOW
from loader import load_centred


ShipModel = namedtuple('ShipModel', 'name sprite rotation acceleration max_speed radius mass colour')


CUTTER = ShipModel(
    name='Cutter',
    sprite=load_centred('cutter'),
    rotation=100.0,  # angular velocity, degrees/second
    acceleration=350.0,  # pixels per second per second
    max_speed=150.0,  # maximum speed in pixels/second
    radius=8.0,
    mass=1,
    colour=GREEN
)


LUGGER = ShipModel(
    name='Lugger',
    sprite=load_centred('lugger'),
    rotation=200.0,  # angular velocity, degrees/second
    acceleration=420.0,  # pixels per second per second
    max_speed=150.0,  # maximum speed in pixels/second
    radius=14.0,
    mass=2,
    colour=RED
)


CLIPPER = ShipModel(
    name='Clipper',
    sprite=load_centred('clipper'),
    rotation=150.0,  # angular velocity, degrees/second
    acceleration=550.0,  # pixels per second per second
    max_speed=350,  # maximum speed in pixels/second
    radius=14.0,
    mass=1.5,
    colour=YELLOW
)


SHIPS = [
    CUTTER,
    LUGGER,
    CLIPPER
]

