from time import sleep

from django.core.management.base import BaseCommand

from hardware.pumps import Pumps


class Command(BaseCommand):
    help = 'Manually control the pumps'

    def handle(self, *args, **options):
        pumps = Pumps()
        try:
            while True:
                pump_id = int(input('Pump number: '))
                t = float(input('Time [s]: '))
                pumps.start(pump_id)
                print('Pump %i is on !' % pump_id)
                sleep(t)
                pumps.stop(pump_id)
                print('Pump %i is off' % pump_id)
        finally:
            print('Stop all pumps')
            pumps.stop_all()
