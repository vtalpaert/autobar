from django.core.management.base import BaseCommand

from hardware.weight import WeightModule


class Command(BaseCommand):
    help = 'Helps you find the correct settings for the weight cell'

    def handle(self, *args, **options):
        module = WeightModule()
        module.interactive_settings()
