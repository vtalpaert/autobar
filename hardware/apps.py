from django.apps import AppConfig
from django.db.models.signals import post_save
from django.db.utils import OperationalError


class HardwareConfig(AppConfig):
    name = 'hardware'

    def ready(self):
        try:
            from .serving import CocktailArtist
            artist = CocktailArtist.getInstance()
            post_save.connect(artist.order_post_save, sender='recipes.Order', dispatch_uid='CocktailArtist')
        except OperationalError:
            print("Artist will not receive Orders. This is normal during migrations.")
