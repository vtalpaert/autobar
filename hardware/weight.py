#!/usr/bin/env python3

from collections import deque
import time
from statistics import median, StatisticsError
import threading
import weakref

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

from recipes.models import Configuration

class HX711(object):
    """
    HX711 represents chip for reading load cells.
    """
    _bits = 24
    _power_down_delay = 0.00006  # enters power down mode if pd_sck pin is HIGH for at least 60 us.

    def __init__(self,
                 dout_pin,
                 pd_sck_pin,
                 gain=128,
                 channel='A'):
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

        self._data = {'A': {128: 1, 64: 3}, 'B': {32: 2}}

        GPIO.setup(self._pd_sck, GPIO.OUT)  # pin _pd_sck is output only
        GPIO.setup(self._dout, GPIO.IN)  # pin _dout is input only
        self._channel, self._gain = channel, gain  # one to initialize
        self.channel, self.gain = channel, gain  # one to raise errors properly

    @property
    def channel(self):
        return self._channel

    @channel.setter
    def channel(self, channel):
        if channel not in self._data:
            print('Invalid channel %s, using A' % channel)
            channel = 'A'
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
        self._gain = gain
        self._read()
        time.sleep(0.5)

    def zero(self):
        """
        sets the current data as an offset for the current channel and gain.
        Also known as tare.

        Returns:
            bool: True when it is ok. False otherwise.
        """
        result = self._read()
        if result is not False:
            self.offset = result
        return result is not False

    def _set_channel_gain(self):
        """
        _set_channel_gain is called only from _read method.
        It finishes the data transmission for HX711 which sets
        the next required gain and channel.

        Returns: bool True if HX711 is ready for the next reading
            False if HX711 is not ready for the next reading
        """
        num = self._data[self._channel][self._gain]
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
        result = self._read()
        return result is not False


class BackgroundTask(threading.Thread):
    """TODO
    """

    def __init__(self, lock, condition, callback, delay, timeout, on_timeout):
        super().__init__()
        self.deamon = True
        self.exit_event = threading.Event()
        self.lock = lock
        self.condition = weakref.proxy(condition)
        self.callback = weakref.proxy(callback)
        self.delay = delay
        self.timeout = timeout
        self.on_timeout = weakref.proxy(on_timeout)

    def run(self):
        start = time.time()
        while not self.condition() and not self.exit_event.is_set():
            if time.time() - start > self.timeout:
                print('timeout!')
                # release before on_timeout
                self.lock.release()
                self.on_timeout()
                return  # exit
            time.sleep(self.delay)
        # release before callback, in case callback starts a new thread
        self.lock.release()
        if not self.exit_event.is_set():
            self.callback()


class WeightModule(object):
    dummy = False

    def __init__(self):
        self.background_task_lock = threading.Lock()
        self.thread = None
        self.cell = None
        self.offset = 0
        self.ratio = 1

    def init_from_settings_and_config(self, settings, config):
        """Pass settings and config since this file works without Django"""
        self.cell = HX711(
            settings.GPIO_DT,
            settings.GPIO_SCK,
            gain=config.weight_cell_gain,
            channel=config.weight_cell_channel
        )
        self.delay_measure = config.weight_module_delay_measure
        self.queue = deque(maxlen=config.weight_module_queue_length)
        self.offset = config.weight_cell_offset
        self.ratio = config.weight_cell_ratio

    def interactive_settings(self):
        gpio_dt = int(input("Enter GPIO DT:"))
        gpio_sck = int(input("Enter GPIO SCK:"))
        channel = input("Enter channel (A or B)")
        gain = int(input("Enter gain (32, 64 or 128)"))
        maxlen = 100
        self.cell = HX711(gpio_dt, gpio_sck, gain=gain, channel=channel)
        self.delay_measure = 0.02
        self.queue = deque(maxlen=maxlen)
        self.offset = 0
        self.ratio = 1

        # tare
        input("Empty the scale and presse enter")
        print("Taring")
        if not self.cell.power_up():
            print("Cell could not power up")
        success = [self.get_value() is not None for _ in range(maxlen)]
        print("Had", sum(success), "good readings on", maxlen)
        self.offset = self.get_value()
        print("Offset will be", self.offset)

        # ratio
        known = float(input("Put a known weight on scale, and enter here the weight in grams"))
        print("Wait")
        self.queue.clear()
        success = [self.get_value() is not None for _ in range(maxlen)]
        print("Had", sum(success), "good readings on", maxlen)
        value = self.get_value()
        print("I read", value, ", minus offset is now", value - self.offset)
        self.ratio = known / (value - self.offset)
        print("My ratio is", self.ratio)
        print("You wanted to read", known, "grams. My calculation outputs", self.convert_value_to_weight(value))

        # test
        print("Will now run a few tests")
        def you_failed():
            print("You failed to follow the above instruction")
        def when_removed():
            print("You removed the weight")
            time.sleep(0.1)
            def when_put_back_on():
                print("You put the weight back")
                time.sleep(0.1)
                def too_fast():
                    raise Exception("You should not see this")
                def expected_timeout():
                    print("We had the timeout, as expected")
                    print("This was the last test")
                print("I will now timeout in 5 seconds")
                self.trigger_on_condition(too_fast, lambda weight: False, 5, expected_timeout)
            print("You have 10 seconds to put the weight back on")
            self.trigger_on_condition(when_put_back_on, lambda weight: weight > 0.9 * known, 10, you_failed)
        print("You have 10 seconds to remove the weight")
        self.trigger_on_condition(when_removed, lambda weight: weight < 0.9 * known, 10, you_failed)
        print("Tests are running in background")
        input("Enter to exit (but don't exit if tests are running")

    def get_value(self):
        if self.cell is None:
            return None
        value = self.cell._read()
        if value is False:
            return None
        self.queue.append(value)
        if self.queue:
            return median(self.queue)
        else:
            return None

    def convert_value_to_weight(self, value):
        """Linear a*(x-b). Note parenthesis"""
        return self.ratio * (value - self.offset)

    def make_constant_weight_measure(self):
        self.queue.clear()
        for _ in range(maxlen):
            value = self.get_value()
        return self.convert_value_to_weight(value)

    def trigger_on_condition(self, callback, weight_condition, timeout, on_timeout):
        """Will frequently test condition and trigger callback when True

        weight_condition should look like: lambda weight: weight > 10
        """
        def apply_condition():
            value = self.get_value()
            if value is None:
                return False  # do not trigger
            else:
                weight = self.convert_value_to_weight(value)
                return weight_condition(weight)
        self.thread = BackgroundTask(self.background_task_lock, apply_condition, callback, self.delay_measure, timeout, on_timeout)
        acquired = self.background_task_lock.acquire()
        if acquired:
            self.queue.clear()
            if self.cell.power_up():
                self.thread.start()  # will release lock
                return True
            return False
        else:
            return False

    def kill_current_task(self):
        if self.thread is not None:
            self.thread.exit_event.set()


if __name__ == '__main__':
    module = WeightModule()
    module.interactive_settings()
