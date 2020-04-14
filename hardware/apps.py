from django.apps import AppConfig
from django.db.models.signals import post_save


class HardwareConfig(AppConfig):
    name = 'hardware'

    def ready(self):
        from .serving import CocktailArtist
        artist = CocktailArtist.getInstance()
        post_save.connect(artist.order_post_save, sender='recipes.Order', dispatch_uid='CocktailArtist')
