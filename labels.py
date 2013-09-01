import math
import pyglet
from wasabi.geom import v


FONT_FILENAME = 'gun4fc.ttf'
FONT_NAME = 'Gunship Condensed'


class FadeyLabel(object):
    FADE_START = 8.0   # seconds
    FADE_END = 10.0  # seconds

    FADE_TIME = FADE_END - FADE_START

    def __init__(
            self, world, text, follow,
            offset=v(10, -20),
            colour=(255, 255, 255)):
        self.world = world
        self.follow = follow
        self.colour = colour
        self.offset = offset
        self.label = pyglet.text.Label(
            text,
            font_name=FONT_NAME,
            color=colour + (255,)
        )
        self.age = 0
        self.world.spawn(self)

    def update(self, ts):
        if not self.follow.alive:
            self.kill()
        self.age += ts
        if self.age >= self.FADE_END:
            # Dead
            self.kill()
        elif self.age > self.FADE_START:
            # Fading
            alpha = 1.0 - (self.age - self.FADE_START) / self.FADE_TIME
            self.label.color = self.colour + (int(255 * alpha),)

    def kill(self):
        self.world.objects.remove(self)

    def draw(self):
        # track the thing we are labelling
        self.label.x, self.label.y = v(self.follow.position) + self.offset

        # Draw label
        self.label.draw()


class Signpost(object):
    @classmethod
    def load(cls):
        if not hasattr(cls, 'pointers'):
            ul = pyglet.image.load('sprites/pointer.png').get_texture()
            ul.anchor_x = 0
            ul.anchor_y = ul.height
            cls.pointers = {
                ('left', 'top'): ul,
                ('right', 'top'): ul.get_transform(flip_x=True),
                ('left', 'bottom'): ul.get_transform(flip_y=True),
                ('right', 'bottom'): ul.get_transform(flip_x=True, flip_y=True)
            }

    def __init__(self, camera, text, follow, colour=(255, 255, 255, 255)):
        self.camera = camera
        self.follow = follow
        self.colour = colour
        self.text = text
        self.label = pyglet.text.Label(
            text,
            font_name=FONT_NAME,
            color=colour
        )
        self.load()
        self.sprite = pyglet.sprite.Sprite(next(self.pointers.itervalues()))
        self.sprite.color = colour[:3]

    def draw(self):
        pos = self.follow.position
        vp = self.camera.get_viewport()
        if vp.contains(pos):
            return

        x, y = pos

        if x < vp.l:
            lx = vp.l + 10
            dx = vp.l - x
        elif x > vp.r:
            lx = vp.r - 10
            dx = x - vp.r
        else:
            lx = x
            dx = 0

        if y < vp.b:
            ly = vp.b + 10
            dy = vp.b - y
        elif y > vp.t:
            ly = vp.t - 10
            dy = y - vp.t
        else:
            ly = y
            dy = 0

        cx, cy = self.camera.position

        anchor_x = 'left' if x < cx else 'right'
        anchor_y = 'bottom' if y < cy else 'top'

        lx = int(lx + 0.5)
        ly = int(ly + 0.5)

        self.sprite.image = self.pointers[anchor_x, anchor_y]
        self.sprite.position = lx, ly

        self.label.anchor_x = anchor_x
        self.label.anchor_y = anchor_y

        dist = int(math.sqrt(dx * dx + dy * dy) + 0.5)

        if dist > 200:
            dist = '%0.1fkm' % (dist / 1000.0)
        else:
            dist = '%dm' % dist

        if x < cx:
            self.label.text = '%s ( %s )' % (self.text, dist)
            self.label.x = lx + 26
        else:
            self.label.text = '( %s ) %s' % (dist, self.text)
            self.label.x = lx - 26

        self.label.y = ly + (10 if anchor_y == 'bottom' else -10)

        self.sprite.draw()
        self.label.draw()
