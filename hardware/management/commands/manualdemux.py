from time import sleep

from django.core.management.base import BaseCommand

from hardware.interfaces import GpioInterface


class Command(BaseCommand):
    help = 'Manually control the demux'

    def handle(self, *args, **options):
        interface = GpioInterface.getInstance()
        while True:
            try:
                output = int(input('Output number: '))
                t = float(input('Time [s]: '))
                interface.demux_start(output)
                print('demux: %i is on !' % output)
                sleep(t)
                interface.demux_stop(output=output)
                print('demux: %i is off' % output)
            finally:
                print('demux: all stop')
                interface.demux_stop()
