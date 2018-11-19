import os
os.environ['GPIOZERO_PIN_FACTORY'] = os.environ.get('GPIOZERO_PIN_FACTORY', 'mock')

# https://cdn.sparkfun.com/datasheets/Sensors/ForceFlex/hx711_english.pdf
# https://github.com/gandalf15/HX711/blob/dev/HX711_Python3/hx711.py

import time
from gpiozero import GPIOZeroWarning, SmoothedInputDevice, DigitalInputDevice, DigitalOutputDevice


class HX711(SmoothedInputDevice):
    """
    DOUT
    PD_SCK
    """
    _gains = {
        0: {128: 1, 64: 3},  # channel A
        1: {32: 2}  # channel B
    }
    _bits = 24
    _default_gain = {0: 128, 1: 32}
    _differential = True
    _supply_voltage_range = (2.6, 5.5)
    _power_down_delay = 0.00006  # 60 us
    _ready_counter = 40
    _threshold = -1  # TODO test this

    _value_max = 0x7fffff  # highest possible value from hx711
    _value_min = 0x800000  # lowest possible value from hx711

    def __init__(self, dout, pd_sck, channel=0, max_voltage=3.3, pin_factory=None):
        self._dout = DigitalInputDevice(pin=dout, pin_factory=pin_factory)
        self._pd_sck = DigitalOutputDevice(pin=pd_sck, pin_factory=pin_factory)
        self._channel = channel
        self._gain = self._default_gain[self._channel]
        if max_voltage < 2.6 or 5.5 < max_voltage:
            raise GPIOZeroWarning(
                'Max voltage should be in range %s.' % str(self._supply_voltage_range)
            )
        self.max_voltage = max_voltage
        super(HX711, self).__init__(
            pin=None,
            threshold=0.5,
            queue_len=10,
            partial=False,
            # average=median,
            pin_factory=None
        )

    @property
    def gain(self):
        return self._gain

    @gain.setter
    def gain(self, gain):
        if gain in self._gains[self._channel]:
            self._gain = gain
            time.sleep(0.5)
            # after changing channel or gain it has to wait 50 ms to allow adjustment.
            # the data before is garbage and cannot be used.
        else:
            raise ValueError(
                'For channel %i your gain must be chosen from %s.'
                % (self._channel, self._gains[self._channel].keys())
            )

    def _read(self):
        self._pd_sck.off()  # start by setting the pd_sck to 0
        ready_counter = 0
        while self._dout.value is True:  # if DOUT pin is low data is ready for reading
            time.sleep(0.01)  # sleep for 10 ms because data is not ready
            ready_counter += 1
            if ready_counter == self._ready_counter:  # if counter reached max value then return False
                print('self._read() not ready after %i trials' % self._ready_counter)
                return

        # read first 24 bits of data
        data_in = 0  # 2's complement data from hx 711
        for _ in range(self._bits):
            start_counter = time.perf_counter()
            # request next bit from hx 711
            self._pd_sck.on()
            self._pd_sck.off()
            end_counter = time.perf_counter()
            if end_counter - start_counter >= self._power_down_delay:  # check if the hx 711 did not turn off...
                # if pd_sck pin is HIGH for 60 us and more than the HX 711 enters power down mode.
                print('Not enough fast while reading data')
                print('Time elapsed: {}'.format(end_counter - start_counter))
                return
            # Shift the bits as they come to data_in variable.
            # Left shift by one bit then bitwise OR with the new bit.
            data_in = (data_in << 1) | int(self._dout.value)  # TODO: cast int? on value

        # set gain
        for _ in range(self._gains[self._channel][self._gain]):
            start_counter = time.perf_counter()
            self._pd_sck.on()
            self._pd_sck.off()
            end_counter = time.perf_counter()
            if end_counter - start_counter >= self._power_down_delay:
                print('Not enough fast while setting gain and channel')
                print('Time elapsed: {}'.format(end_counter - start_counter))
                # hx711 has turned off. First few readings are inaccurate.
                # Despite it, this reading was ok and data could be used. TODO
                return

        # print 2's complement value
        print('Binary value as received: {}\n'.format(bin(data_in)))

        # check if data is valid
        if data_in in [self._value_min, self._value_max]:
            print('Invalid data detected: {}\n'.format(data_in))
            return  # return false because the data is invalid

        # calculate int from 2's complement
        if data_in & 0x800000:
            # 0b1000 0000 0000 0000 0000 0000 check if the sign bit is 1. Negative number.
            signed_data = -((data_in ^ 0xffffff) + 1)  # convert from 2's complement to int
        else:  # else do not do anything the value is positive number
            signed_data = data_in

        print('Converted 2\'s complement value: {}\n'.format(signed_data))
        return signed_data

    def power_down(self):
        """
        Power down method turns off the hx711.
        """
        self._pd_sck.off()
        self._pd_sck.on()
        time.sleep(0.01)

    def power_up(self):
        """
        power up function turns on the hx711.
        """
        self._pd_sck.off()
        time.sleep(0.01)

    @property
    def weight(self):
        return  # TODO


if __name__ == '__main__':
    cell = HX711(dout=16, pd_sck=20)
    while True:
        print("value", cell.value)
