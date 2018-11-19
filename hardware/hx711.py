#!/usr/bin/env python3

from collections import deque
import time
from statistics import median, StatisticsError

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

import weakref
from threading import Thread, Event


_THREADS = set()
def _threads_shutdown():
    while _THREADS:
        for t in _THREADS.copy():
            t.stop()


class GPIOThread(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None):
        if kwargs is None:
            kwargs = {}
        self.stopping = Event()
        super(GPIOThread, self).__init__(group, target, name, args, kwargs)
        self.daemon = True

    def start(self):
        self.stopping.clear()
        _THREADS.add(self)
        super(GPIOThread, self).start()

    def stop(self):
        self.stopping.set()
        self.join()

    def join(self):
        super(GPIOThread, self).join()
        _THREADS.discard(self)


class GPIOQueue(GPIOThread):
    """
    Extends :class:`GPIOThread`. Provides a background thread that monitors a
    device's values and provides a running *average* (defaults to median) of
    those values. If the *parent* device includes the :class:`EventsMixin` in
    its ancestry, the thread automatically calls
    :meth:`~EventsMixin._fire_events`.
    """
    def __init__(
            self, parent, queue_len=5, sample_wait=0.0, partial=False, average=median):
        assert callable(average)
        super(GPIOQueue, self).__init__(target=self.fill)
        if queue_len < 1:
            raise ValueError('queue_len must be at least one')
        self.queue = deque(maxlen=queue_len)
        self.partial = bool(partial)
        self.sample_wait = float(sample_wait)
        self.full = Event()
        self.parent = weakref.proxy(parent)
        self.average = average

    @property
    def value(self):
        if not self.partial:
            self.full.wait()
        try:
            return self.average(self.queue)
        except (ZeroDivisionError, StatisticsError):
            return False

    def fill(self):
        try:
            while not self.stopping.wait(self.sample_wait):
                read = self.parent._read()
                print(read)
                if read is not False:
                    self.queue.append(read)
                if not self.full.is_set() and len(self.queue) >= self.queue.maxlen:
                    self.full.set()
        except ReferenceError:
            # Parent is dead; time to die!
            pass


class HX711(object):
    """
    HX711 represents chip for reading load cells.
    """
    _bits = 24
    _power_down_delay = 0.00006  # enters power down mode if pd_sck pin is HIGH for at least 60 us.

    def __init__(self,
                 dout_pin,
                 pd_sck_pin,
                 queue_len=6,
                 gain=128,
                 channel='A',
                 sample_wait=0.1):
        """
        Init a new instance of HX711

        Args:
            dout_pin(int): Raspberry Pi pin number where the Data pin of HX711 is connected.
            pd_sck_pin(int): Raspberry Pi pin number where the Clock pin of HX711 is connected.
            queue(int)
            gain(int): Optional, by default value 128. Options (128 || 64)
            channel(str): Optional, by default 'A'. Options ('A' || 'B')

        Raises:
            TypeError: if pd_sck_pin or dout_pin are not int type
        """
        if not isinstance(dout_pin, int) and not isinstance(pd_sck_pin, int):
            raise TypeError('pins must be type int. ')
        self._dout, self._pd_sck = dout_pin, pd_sck_pin
        self._debug_mode = False

        defaults = {
            'offset': 0,
            'last_raw_data': 0,
            'ratio': 1,
        }
        self._data = {
            'A': {128: dict(defaults), 64: dict(defaults)},
            'B': {32: dict(defaults)}
        }
        self._data['A'][128]['signal'] = 1
        self._data['B'][32]['signal'] = 2
        self._data['A'][64]['signal'] = 3

        GPIO.setup(self._pd_sck, GPIO.OUT)  # pin _pd_sck is output only
        GPIO.setup(self._dout, GPIO.IN)  # pin _dout is input only
        self._channel, self._gain = channel, gain
        self._queue = GPIOQueue(self, queue_len, sample_wait=sample_wait, partial=True)
        self.channel = channel
        self.gain = gain
        self._queue.start()

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self, channel):
        if channel not in self._data:
            raise ValueError('Channel has to be in %s.' % str(self._data.keys()))
        # after changing channel or gain it has to wait 50 ms to allow adjustment.
        # the data before is garbage and cannot be used.
        self._channel = channel
        self._read()
        time.sleep(0.5)

    @property
    def gain(self):
        return self._gain

    @gain.setter
    def gain(self, gain):
        if gain not in self._data[self._channel]:
            raise ValueError('Gain has to be in %s' % str(self._data[self._channel].keys()))
        # after changing channel or gain it has to wait 50 ms to allow adjustment.
        # the data before is garbage and cannot be used.
        self._read()
        time.sleep(0.5)

    def zero(self):
        """
        sets the current data as an offset for the current channel and gain.
        Also known as tare.

        Returns:
            bool: True when it is ok. False otherwise.
        """
        result = self.value
        if result is not False:
            self.offset = result
        return result is not False

    @property
    def offset(self):
        return self._data[self._channel][self._gain]['offset']

    @offset.setter
    def offset(self, offset):
        self._data[self._channel][self._gain]['offset'] = offset

    @property
    def ratio(self):
        """
        set_scale_ratio method sets the ratio for calculating
        weight in desired units. In order to find this ratio for
        example to grams or kg. You must have known weight.

        Args:
            ratio(float): number > 0.0 that is used for
                conversion to weight units
        """
        return self._data[self._channel][self._gain]['ratio']

    @ratio.setter
    def ratio(self, ratio):
        self._data[self._channel][self._gain]['ratio'] = ratio

    @property
    def _last_raw_data(self):
        return self._data[self._channel][self._gain]['last_raw_data']

    @_last_raw_data.setter
    def _last_raw_data(self, data):
        self._data[self._channel][self._gain]['last_raw_data'] = data

    def _set_channel_gain(self):
        """
        _set_channel_gain is called only from _read method.
        It finishes the data transmission for HX711 which sets
        the next required gain and channel.

        Returns: bool True if HX711 is ready for the next reading
            False if HX711 is not ready for the next reading
        """
        num = self._data[self._channel][self._gain]['signal']
        for _ in range(num):
            start_counter = time.perf_counter()
            GPIO.output(self._pd_sck, True)
            GPIO.output(self._pd_sck, False)
            end_counter = time.perf_counter()
            # check if hx 711 did not turn off...
            if end_counter - start_counter >= self._power_down_delay:
                if self._debug_mode:
                    print('Not enough fast while setting gain and channel')
                    print(
                        'Time elapsed: {}'.format(end_counter - start_counter))
                # hx711 has turned off. First few readings are inaccurate.
                # Despite it, this reading was ok and data can be used.
                return False
        return True

    def _read(self):
        """
        _read method reads bits from hx711, converts to INT
        and validate the data.

        Returns: (bool || int) if it returns False then it is false reading.
            if it returns int then the reading was correct
        """
        GPIO.output(self._pd_sck, False)  # start by setting the pd_sck to 0
        ready_counter = 0
        while GPIO.input(self._dout) != 0:  # if DOUT pin is low data is ready for reading
            time.sleep(0.01)  # sleep for 10 ms because data is not ready
            ready_counter += 1
            if ready_counter == 50:  # if counter reached max value then return False
                if self._debug_mode:
                    print('self._read() not ready after 40 trials\n')
                return False

        # read first 24 bits of data
        data_in = 0  # 2's complement data from hx 711
        for _ in range(24):
            start_counter = time.perf_counter()
            # request next bit from hx 711
            GPIO.output(self._pd_sck, True)
            GPIO.output(self._pd_sck, False)
            end_counter = time.perf_counter()
            if end_counter - start_counter >= self._power_down_delay:  # check if the hx 711 did not turn off...
                # if pd_sck pin is HIGH for 60 us and more than the HX 711 enters power down mode.
                if self._debug_mode:
                    print('Not enough fast while reading data')
                    print(
                        'Time elapsed: {}'.format(end_counter - start_counter))
                return False
            # Shift the bits as they come to data_in variable.
            # Left shift by one bit then bitwise OR with the new bit.
            data_in = (data_in << 1) | GPIO.input(self._dout)

        if not self._set_channel_gain():
            return False  # return False because channel was not set properly

        if self._debug_mode:  # print 2's complement value
            print('Binary value as received: {}\n'.format(bin(data_in)))

        # check if data is valid
        if data_in in [0x7fffff, 0x800000]:
            # 0x7fffff is the highest possible value from hx711
            # 0x800000 is the lowest possible value from hx711
            if self._debug_mode:
                print('Invalid data detected: {}\n'.format(data_in))
            return False

        # calculate int from 2's complement
        if data_in & 0x800000:
            # 0b1000 0000 0000 0000 0000 0000 check if the sign bit is 1. Negative number.
            signed_data = -(
                (data_in ^ 0xffffff) + 1)  # convert from 2's complement to int
        else:  # else do not do anything the value is positive number
            signed_data = data_in

        if self._debug_mode:
            print('Converted 2\'s complement value: {}\n'.format(signed_data))
        return signed_data

    @property
    def value(self):
        return self._queue.value

    def get_data(self):
        result = self.value
        if result is not False:
            return result - self.offset
        else:
            return False

    def get_weight(self):
        result = self.value
        if result is not False:
            return float((result - self.offset) / self.ratio)
        else:
            return False

    def power_down(self):
        """
        Power down method turns off the hx711.
        """
        GPIO.output(self._pd_sck, False)
        GPIO.output(self._pd_sck, True)
        time.sleep(0.01)

    def power_up(self):
        """
        power up function turns on the hx711.
        """
        GPIO.output(self._pd_sck, False)
        time.sleep(0.01)

    def reset(self):
        """
        reset method resets the hx711 and prepare it for the next reading.

        Returns: bool True when it is ready for reading.
            Else it is not and it returns False
        """
        self.power_down()
        self.power_up()
        result = self.value
        return result is not False


if __name__ == '__main__':
    from collections import deque
    from itertools import count
    dt = deque(maxlen=50)
    cell = HX711(16, 20)
    cell._debug_mode = True
    while cell.zero() is False:
        print("zero")
    while True:
        start_counter = time.perf_counter()
        for i in count():
            data = cell.get_data()
            if data is not False:
                break
        end_counter = time.perf_counter()
        dt.append(1 / (end_counter - start_counter))
        mean = sum(dt) / len(dt)
        print('data:', data, '\tfreq:', mean, '\terrors:', i, '\n')
