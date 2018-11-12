from time import sleep

from django.core.management.base import BaseCommand

from hardware.interfaces import GpioInterface


class Command(BaseCommand):
    help = 'Manually control the demux'

    def add_arguments(self, parser):
        parser.add_argument('--outputs', help="Use a string to give several outputs as in '0 9 2'")
        parser.add_argument('--time-on', help='On time [s]', default=1, type=int)
        parser.add_argument('--time-off', help='Off time [s]', default=1, type=int)

    def handle(self, *args, **options):
        interface = GpioInterface.getInstance()
        raw_outputs = options['outputs']
        if isinstance(raw_outputs, str):
            outputs = [int(output) for output in raw_outputs.split()]
        elif isinstance(raw_outputs, int):
            outputs = [raw_outputs]
        else:
            outputs = []
        try:
            for output in outputs:
                interface.demux_start(output)
                print('demux: %i is on !' % output)
                sleep(options['time_on'])
                interface.demux_stop(output=output)
                print('demux: %i is off' % output)
                sleep(options['time_off'])
        finally:
            print('demux: all stop')
            interface.demux_stop()
