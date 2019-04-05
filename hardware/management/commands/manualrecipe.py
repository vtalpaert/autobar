from time import sleep

from django.core.management.base import BaseCommand

from hardware.interfaces import HardwareInterface


class Command(BaseCommand):
    help = 'Make your own recipe live'

    def handle(self, *args, **options):
        interface = HardwareInterface.getInstance()
        done = False
        pump_n_weight = []
        while not done:
            pump = int(input('Pump number: '))
            weight = float(input('Weight: '))
            pump_n_weight.append((pump, weight))
            done = bool(input('Are you done (0=no, 1=yes): '))
        print('Starting %s' % str(pump_n_weight))
        interface.controlled_serve(pump_n_weight)
