import pyglet.image


def make_centred(image):
    w = image.width
    h = image.height
    image.anchor_x = w // 2
    image.anchor_y = h // 2
    return image


def load_centred(img):
    return make_centred(pyglet.image.load('sprites/%s.png' % img))
