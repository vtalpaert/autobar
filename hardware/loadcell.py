import os
os.environ['GPIOZERO_PIN_FACTORY'] = os.environ.get('GPIOZERO_PIN_FACTORY', 'mock')

# https://cdn.sparkfun.com/datasheets/Sensors/ForceFlex/hx711_english.pdf
# https://github.com/dudapickler/hx711_SPI/blob/master/HX711_SPI.c

from gpiozero import AnalogInputDevice, GPIOZeroWarning


class HX711(AnalogInputDevice):
    """
    Raspberry MISO -> DOUT
    Raspberry MOSI -> PD_SCK
    """
    _start_send = 0x00
    _start_read = 0x00
    _gains = {
        0: {128: 0x80, 64: 0xa8},  # channel A
        1: {32: 0xa0}  # channel B
    }
    _bits = 24
    _default_gain = {0: 128, 1: 32}
    _differential = True
    _supply_voltage_range = (2.6, 5.5)

    def __init__(self, channel=0, max_voltage=3.3, **spi_args):
        self._channel = channel
        self._gain = self._default_gain[self._channel]
        if max_voltage < 2.6 or 5.5 < max_voltage:
            raise GPIOZeroWarning(
                'Max voltage should be in range %s.' % str(self._supply_voltage_range)
            )
        super(HX711, self).__init__(self._bits, max_voltage, **spi_args)

    @property
    def gain(self):
        return self._gain

    @gain.setter
    def gain(self, gain):
        if gain in self._gains[self._channel]:
            self._gain = gain
        else:
            raise ValueError(
                'For channel %i your gain must be chosen from %s.'
                % (self._channel, self._gains[self._channel].keys())
            )

    def _read(self):
        dt = None
        while dt != self._start_read:
            resp = self._spi.transfer((self._start_send,))
            dt = self._words_to_int(
                resp, 4
            )
        print("last start", dt)
        resp = self._spi.transfer(self._send())
        print("resp", resp)
        return self._words_to_int(
            resp, self.bits
        )

    def _send(self):
        return (0xaa,)*6 + (self._gains[self._channel][self.gain],)


if __name__ == '__main__':
    cell = HX711(mosi_pin=20, miso_pin=16)
    while True:
        print("raw", cell.raw_value)
        print("value", cell.value)
