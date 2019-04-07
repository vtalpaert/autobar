from django.apps import AppConfig
from django.db.models.signals import post_save


class HardwareConfig(AppConfig):
    name = 'hardware'

    def ready(self):
        from .interfaces import HardwareInterface
        interface = HardwareInterface.getInstance()
        post_save.connect(interface.order_post_save, sender='recipes.Order', dispatch_uid='HardwareInterface')
