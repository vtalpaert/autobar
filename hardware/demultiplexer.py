import os

from django.conf import settings
if settings.INTERFACE_USE_DUMMY:
    os.environ['GPIOZERO_PIN_FACTORY'] = os.environ.get('GPIOZERO_PIN_FACTORY', 'mock')

import string
from collections import OrderedDict, namedtuple

from gpiozero import SourceMixin, CompositeDevice, DigitalOutputDevice


class DeMultiplexer(SourceMixin, CompositeDevice):
    """
    Extends :class:`CompositeDevice` and represents a generic de-multiplexer.

    A de-multiplexer is a binary to 1 of N decoder with inhibit. This is useful
    to realize a channel selector.

    By providing n pins, you can control N=2**n outputs. Typically 3 pins for 8
    outputs, 4 pins for 16.

    The outputs are numbered from 0 to N-1. The device inputs are one inhibit (INH)
    pin, several pins coding the output in binary (called by a letter
    starting at A). The output pin takes the COM value when INH is low.

    See::
        https://en.wikipedia.org/wiki/Multiplexer
        http://www.ti.com/lit/ds/symlink/cd4051b.pdf

    The following code will write output 3 for 1 second::

        # from gpiozero import DeMultiplexer
        from time import sleep

        demux8 = DeMultiplexer(1, 2, 3, inh=0)
        print(demux8.value)  # DeMultiplexerValue(a=False, b=False, c=False) or 000
        demux8.write(3)
        print(demux8.value)  # DeMultiplexerValue(a=True, b=True, c=False) or 011
        demux8.inhibit = False
        sleep(1)
        demux8.inhibit = True

    Notice how the internal value of (True, True, False) is reversed to form 011.
    Indeed the values are given as (A, B, C, ...)

    :param int pins:
        The GPIO pins connected to the A, B, C, etc pins. They encode the active
        channel.

    :param int inh:
        The GPIO pin connected to the inhibit pin.

    :param int com:
        Eventual GPIO pin connected to the COM pin.

    :param int initial_inhibit:
        Defaults to ``True``. The value taken initially by the INH pin.

    :param Factory pin_factory:
        See :doc:`api_pins` for more information (this is an advanced feature
        which most users can ignore).
    """

    # see https://gpiozero.readthedocs.io/en/stable/source_values.html#composite-devices
    DeMultiplexerValue = None

    def __init__(self, *args, inh, com=None, initial_inhibit=True, pin_factory=None):
        self.n = 2 ** len(args)
        self._inputs = OrderedDict([
            (name, DigitalOutputDevice(value, pin_factory=pin_factory))
            for name, value in zip(string.ascii_lowercase, args)
        ])
        self._all = dict(self._inputs)
        self._all['inh'] = DigitalOutputDevice(inh, pin_factory=pin_factory)
        if com is not None:
            self._all['com'] = DigitalOutputDevice(com, pin_factory=pin_factory)
        super(DeMultiplexer, self).__init__(
                **self._all,
                pin_factory=pin_factory
        )
        self.inhibit = initial_inhibit
        self.DeMultiplexerValue = namedtuple('DeMultiplexerValue', self._inputs.keys())

    @property
    def value(self):
        """
        :return: The current binary encoding.
        """
        return self.DeMultiplexerValue(*tuple(device.value for device in self._inputs.values()))

    @value.setter
    def value(self, value):
        for internal_value, device in zip(value, self._inputs.values()):
            device.value = internal_value

    @property
    def is_active(self):
        """
        Returns ``True`` if the demux is not inhibited and ``False``
        otherwise.
        """
        return not self.inhibit

    @property
    def inhibit(self):
        """
        Shortcut to the value of the INH pin.
        :return: The current inhibition state.
        """
        return self.inh.value

    @inhibit.setter
    def inhibit(self, value):
        self.inh.value = value

    def write(self, output):
        """
        Set output to COM value.

        :param int output:
            The number of the output to write to COM.
            Must be between 0 and n-1.
        """
        if output < 0 or output > self.n - 1:
            raise ValueError(
                "Parameter output must be between 0 and n-1"
            )
        bin_coded_output = '{:b}'.format(output).zfill(len(self._inputs))
        for device, value in zip(self._inputs.values(), bin_coded_output[::-1]):
            device.value = bool(int(value))  # transform '0' in False
        return bin_coded_output


if __name__ == "__main__":
    import time
    demux8 = DeMultiplexer(1, 2, 3, inh=0)
    for output in range(8):
        demux8.write(output)
        print(output, demux8.value)
        demux8.inhibit = False
        print(" on")
        time.sleep(3)
        demux8.inhibit = True
        print(" off")
        time.sleep(5)
