import os
os.environ['GPIOZERO_PIN_FACTORY'] = os.environ.get('GPIOZERO_PIN_FACTORY', 'mock')

import math
import string

from gpiozero import SourceMixin, CompositeDevice, DigitalOutputDevice
from gpiozero import GPIOPinMissing, CompositeDeviceBadOrder, GPIOZeroError


class DeMultiplexerNBits(SourceMixin, CompositeDevice):
    """
    Extends :class:`CompositeDevice` and represents a generic de-multiplexer.

    A de-multiplexer is a binary to 1 of N decoder with inhibit. This is useful
    to realize a channel selector.

    The outputs are numbered from 0 to n-1. The inputs are one inhibit (INH)
    pin, several pins coding the output in binary (called by a letter
    starting at A). The output pin takes the COM value when INH is low.
    You can set the COM using the value property.

    To control 8 outputs, you will need to set a, b, and c pins. 16 outputs
    requires an additional d pin.

    See::
        https://en.wikipedia.org/wiki/Multiplexer
        http://www.ti.com/lit/ds/symlink/cd4051b.pdf

    The following code will write output 3 for 1 second::

        # from gpiozero import DeMultiplexerNBits
        import time

        demux8 = DeMultiplexerNBits(8, inh=1, a=2, b=3, c=4, com=5, use_com=True)
        demux8.value = True  # if use_com
        print(demux8._state)  # '000'
        demux8.write(3)
        print(demux8._state)  # '011'
        demux8.inhibit = False
        time.sleep(1)
        demux8.inhibit = True

    :param int n:
        Number of outputs you would like to control. Usually a power of 2
        like 4, 8 or 16.

    :param int inh:
        The GPIO pin connected to the inhibit pin.

    :param int a,b,c,d...:
        The GPIO pins connected to the A, B, C, etc pins. They encode the active
        channel.

    :param bool use_com:
        Set to whether you are controlling the COM pin yourself. Use ``False``
        if for example you connected your pin to Vss or Ground.

    :param int com:
        Eventual GPIO pin connected to the COM pin. Required only if `use_com`
        is ``True``.

    :param int initial_inhibit:
        Defaults to ``True``. The value taken initially by the INH pin.

    :param Factory pin_factory:
        See :doc:`api_pins` for more information (this is an advanced feature
        which most users can ignore).
    """
    def __init__(self, n, use_com=False, initial_inhibit=True, pin_factory=None, **kwargs):
        self.n = n
        if n < 2 or n > 67108864:
            raise ValueError(
                "Impossible to control %i outputs with this class" % n
            )  # the pins' names are letters, so 2**26 outputs maximum
        self._nb_inputs = self._how_many_inputs_for_n_bits(n)
        self._named_inputs = list(string.ascii_lowercase)[:self._nb_inputs]
        expected_pins = ['inh'] + use_com * ['com'] + self._named_inputs
        devices = dict([
            (name, DigitalOutputDevice(value, pin_factory=pin_factory))
            for name, value in kwargs.items()
        ])

        try:
            super(DeMultiplexerNBits, self).__init__(
                    **devices,
                    _order=expected_pins,
                    pin_factory=pin_factory
            )
        except KeyError as k:
            raise GPIOPinMissing(
                "You are missing a pin %s" % k
            )
        except CompositeDeviceBadOrder:
            raise GPIOZeroError(
                "You are giving too many inputs to control the de-multiplexer"
            )
        self.inhibit = initial_inhibit

    @staticmethod
    def _how_many_inputs_for_n_bits(n):
        return math.ceil(math.log2(n))

    @property
    def value(self):
        """
        This is the value the output will take.
        """
        return self.com.value

    @value.setter
    def value(self, value):
        self.com.value = value

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

    @property
    def _state(self):
        """
        String coding the internal binary encoded channel. Output 3 active is '011'.
        """
        return ''.join([str(int(self.__getattr__(name).value)) for name in self._named_inputs[::-1]])

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
        bin_coded_output = '{:b}'.format(output).zfill(self._nb_inputs)
        for name, value in zip(self._named_inputs, bin_coded_output[::-1]):
            self.__getattr__(name).value = bool(int(value))  # transform '0' in False
        return bin_coded_output


if __name__ == "__main__":
    import time
    demux8 = DeMultiplexerNBits(8, inh=0, a=1, b=2, c=3)
    for output in range(8):
        demux8.write(output)
        print(output, demux8._state)
        demux8.inhibit = False
        print(" on")
        time.sleep(3)
        demux8.inhibit = True
        print(" off")
        time.sleep(5)
