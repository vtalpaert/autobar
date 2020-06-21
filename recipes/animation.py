import os
from itertools import cycle

from django.conf import settings

ANIMATION_DIR = os.path.join(settings.MEDIA_ROOT, 'animation')

def valid_video(f):
    return os.path.isfile(os.path.join(ANIMATION_DIR, f)) and f.endswith('.mp4')

ANIMATIONS = cycle([f for f in
    os.listdir(ANIMATION_DIR) if valid_video(f)])

if not len(ANIMATIONS):
    print(
    """Please! It's really important that you add animations files (.mp4) """
    """inside the {} directory""".format(ANIMATION_DIR)
    )

def get_animation_for_mix(mix):
    """Returns an url to a media, such as animation/1.mp4 (will be combined as {{ MEDIA_URL }}{{ mix.animation_uri }})"""
    return os.path.join('animation', next(ANIMATIONS))
