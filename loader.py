import os.path
import pyglet.image
import pyglet.resource


FONT_FILENAME = 'gun4fc.ttf'
RESOURCE_DIRS = [
    'sprites',
    'fonts',
    'data',
    'sounds'
]


def relpath(p):
    """Get the absolute path of the relative path p."""
    basedir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(basedir, d))


# Set up pyglet resource loader
pyglet.resource.path += [relpath(d) for d in RESOURCE_DIRS]
pyglet.resource.reindex()
pyglet.resource.add_font(FONT_FILENAME)


def make_centred(image):
    w = image.width
    h = image.height
    image.anchor_x = w // 2
    image.anchor_y = h // 2
    return image


def load_centred(img):
    return make_centred(pyglet.image.load('sprites/%s.png' % img))
