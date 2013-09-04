from math import floor, ceil
import random
from pyglet import gl
from wasabi.geom import v
from wasabi.geom.poly import Rect
from pyglet.graphics import Batch


BLOCK_SIZE = 5000

STARS_PER_BLOCK = 2000

FOVY = 40.0
NEAR_PLANE = 500.0
FAR_PLANE = BLOCK_SIZE + NEAR_PLANE

FAR_PLANE_SCALE = (FAR_PLANE + NEAR_PLANE) / NEAR_PLANE


class Starfield(object):
    def __init__(self):
        self.batch = Batch()
        self.blocks = {}

    def draw(self, camera):
        self.build_blocks(camera)

        # set up projection matrix
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glPushMatrix()
        gl.glLoadIdentity()
        gl.gluPerspective(
            FOVY, camera.aspect(),
            NEAR_PLANE, FAR_PLANE
        )
        self.batch.draw()
        gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW)

    def build_blocks(self, camera):
        # compute correct clip rect on far plane
        l, b = camera.position + camera.offset * FAR_PLANE_SCALE
        r, t = camera.position - camera.offset * FAR_PLANE_SCALE

        # Create blocks
        l = int(floor(l / BLOCK_SIZE))
        r = int(ceil(r / BLOCK_SIZE))
        b = int(floor(b / BLOCK_SIZE))
        t = int(ceil(t / BLOCK_SIZE))

        for y in xrange(b, t):
            for x in xrange(l, r):
                if (x, y) in self.blocks:
                    continue
                self.blocks[x, y] = StarfieldBlock(
                    rect=Rect.from_blwh(v(x, y) * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
                    batch=self.batch
                )


class StarfieldBlock(object):
    """A cubic block of stars."""
    def __init__(self, rect, batch):
        self.rect = rect
        self.build_list(batch)

    def build_list(self, batch):
        rng = random.Random()
        rng.seed(hash(self.rect.bottomleft()))

        b, l = self.rect.bottomleft()
        w = self.rect.w
        h = self.rect.h

        coords = []
        cols = []
        for i in xrange(STARS_PER_BLOCK):
            z = rng.random()
            coords.extend([
                rng.random() * w + l,
                rng.random() * h + b,
                rng.uniform(-BLOCK_SIZE * z, 0)
            ])
            cols.extend([1.0 - z] * 3)

        self.vlist = batch.add(
            STARS_PER_BLOCK, gl.GL_POINTS, None,
            ('v3f', coords),
            ('c3f', cols),
        )

    def __del__(self):
        self.vlist.delete()
