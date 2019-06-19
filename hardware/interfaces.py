from itertools import count
from threading import Lock
import time

from django.utils.log import logging

from django.conf import settings
from hardware.singletonmixin import Singleton
from hardware.demultiplexer import DeMultiplexer
try:
    from hardware.hx711 import HX711
    CELL_AVAILABLE = True
except RuntimeError:
    CELL_AVAILABLE = False

    class DummyCell:
        weight = 0

        def get_weight(self):
            self.weight += 1
            return self.weight

from hardware.js_pygame import Joystick
from hardware import process_order

logger = logging.getLogger('autobar')


class HardwareInterface(Singleton):
    def __init__(self):
        print('Interface id', id(self))
        self._state_mutex = Lock()
        self._state = 0
        self._last_button = None
        self._last_order = None

        # de-multiplexers
        config_demux = settings.DEMUX
        self._demux = [
            DeMultiplexer(*c['logic'], inh=c['inh'])
            for c in config_demux
        ]
        self._outputs_mapping, offset = {}, 0
        for demux in self._demux:
            for demux_output in count():
                if demux_output < demux.n:
                    self._outputs_mapping[demux_output + offset] = (demux, demux_output)
                else:
                    offset += demux.n
                    break
        self.nb_outputs = offset

        # cell
        if CELL_AVAILABLE:
            self._cell = HX711(settings.GPIO_DT, settings.GPIO_SCK)
            defaults = settings.WEIGHT_CELL_DEFAULT[self._cell.channel][self._cell.gain]
            self._cell.ratio = defaults['ratio']
            self._cell.offset = defaults['offset']
        elif settings.INTERFACE_USE_DUMMY:
            self._cell = DummyCell()
        else:
            self._cell = None

        # buttons
        if not settings.INTERFACE_USE_DUMMY:
            try:
                self._joy = Joystick(
                    self,
                    name=settings.JOYSTICK_NAME,
                    on_pressed='_button_pressed',
                    on_released='_button_released'
                )
                self._joy.start()
            except ValueError as e:
                print(e)
        else:
            self._joy = None

    @property
    def locked(self):
        return self._state_mutex.locked()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        if state in settings.INTERFACE_STATES and state != self.state:
            if state == 0:
                self._state_mutex.release()
                self._state = 0
            elif self._state_mutex.acquire():
                self._state = state
            else:
                logger.error('Interface could not change state from %s to %s' % (self.state, state))

    def demux_write(self, output, inhibit=True):
        try:
            demux, demux_output = self._outputs_mapping[output]
        except KeyError:
            raise ValueError('%s is not a valid output number with your configuration' % output)
        demux.write(demux_output)
        demux.inhibit = inhibit

    def _demux_inhibit(self, output=None, inhibit=True):
        if output is None:
            for demux in self._demux:
                demux.inhibit = inhibit
        else:
            demux, _ = self._outputs_mapping[output]
            demux.inhibit = inhibit

    def demux_stop(self, output=None):
        self._demux_inhibit(output=output, inhibit=True)

    def demux_start(self, output):
        self.demux_write(output, inhibit=False)

    def _button_pressed(self, button):
        if not self.locked and button in settings.BUTTONS_TO_PUMP_MAPPING:
            self.state = 1
            pump_id = settings.BUTTONS_TO_PUMP_MAPPING[button]
            self.demux_start(pump_id)
            self._last_button = button

    def _button_released(self, button):
        if self.state == 1 and button in settings.BUTTONS_TO_PUMP_MAPPING:
            if self._last_button == button:
                self.demux_stop()
                self.state = 0

    def cell_zero(self):
        self._cell.offset = self._cell_mean_over_time(lambda: self._cell.value)
        return self._cell.offset

    def cell_raw_value(self):
        return self._cell.value

    def cell_reset(self):
        self._cell.ratio = 1
        self._cell.offset = 0

    def cell_set_ratio(self, actual_weight):
        self._cell.ratio = actual_weight / self._cell_mean_over_time(self._cell.get_data)

    def _cell_mean_over_time(self, fun, seconds=10):
        data = []
        for _ in range(10 * seconds):  # for two seconds
            data.append(fun())
            time.sleep(0.1)
        return sum(data) / len(data)

    def cell_weight(self):
        return self._cell.get_weight()

    def cell_wait_for_weight_total(self, weight, timeout=None, wait_secs: float=0, reversed_condition=False):
        start_counter = time.perf_counter()
        while self.cell_weight() < weight and not reversed_condition\
                or reversed_condition and self.cell_weight() > weight:
            if timeout:
                if time.perf_counter() > timeout + start_counter:
                    return False
            if self.state != 2:
                return False
            time.sleep(wait_secs)
        return True

    def order_post_save(self, sender, instance, created, raw, using, update_fields, **kwargs):
        order = instance

        if created:  # on creation of a new order, change instance state and accept order
            if self.state == 0 and order.mix and order.mix.is_available():
                # will move status to 'Waiting for glass'
                order.accepted, order.status, self._last_order = True, 1, order
                self.state = 2  # locks state
                logger.debug('%s was accepted' % order)
                return order.save()
            else:
                logger.error('%s refused (current state: %i, has mix: %s)' % (order, self.state, order.mix is not None))
                if order.accepted:
                    order.accepted = False
                    return order.save()
                return

        if order.accepted and self._last_order == order and self.state == 2:
            # current accepted order is processed here
            if order.status == 1:
                p = process_order.WaitForGlass(self, order)
                p.start()

            elif order.status == 2:
                p = process_order.Serve(self, order)
                p.start()
