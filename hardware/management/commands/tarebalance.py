from django.core.management.base import BaseCommand

from hardware.interfaces import HardwareInterface


class Command(BaseCommand):
    help = 'Helps you find the correct settings for the weight cell'

    def handle(self, *args, **options):
        interface = HardwareInterface.getInstance()
        interface.cell_reset()
        input('Press enter when weight cell is empty')
        interface.cell_zero()
        weight = float(input('Place a known weight on balance, what should it read [g]: '))
        interface.cell_set_ratio(weight)
        channel, gain = interface._cell.channel, interface._cell.gain
        ratio, offset = interface._cell.ratio, interface._cell.offset
        print(
            'You should configure settings with channel %s, gain %s, offset %s, ratio %s'
            % (channel, gain, offset, ratio)
        )
