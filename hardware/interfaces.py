from collections import namedtuple, OrderedDict
from itertools import count
from threading import Lock
import time

from django.utils.log import logging

from autobar import settings
from hardware.singletonmixin import Singleton
from hardware.demultiplexer import DeMultiplexer
try:
    from hardware.hx711 import HX711
    CELL_AVAILABLE = True
except RuntimeError:
    CELL_AVAILABLE = False
from hardware.js_pygame import Joystick

logger = logging.getLogger('autobar')

INTERFACE_STATES = {
    0: 'free',
    1: 'manual',
    2: 'controlled',
}

SCALE_STATES = OrderedDict((
    (0, 'empty'),
    (1, 'waiting_for_glass'),
    (2, 'serving'),
    (3, 'done'),
))


class HardwareInterface(Singleton):
    def __init__(self):
        self._state_mutex = Lock()
        self._state = 0
        self._last_button = None
        self._scale = 0
        #self._pump_states = dict(((pump_id, False) for pump_id in range(settings.PUMPS_NB)))

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
        else:
            self._cell = None

        # buttons
        self._joy = Joystick(
            self,
            name=settings.JOYSTICK_NAME,
            on_pressed='_button_pressed',
            on_released='_button_released'
        )
        self._joy.start()

    @property
    def locked(self):
        return self._state_mutex.locked()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        if not self.locked and state in INTERFACE_STATES and state != self.state:
            if state == 0:
                self._state_mutex.release()
                self._state = 0
            elif self._state_mutex.acquire():
                self._state = state
            else:
                logger.error('Interface could not change state from %s to %s' % (self.state, state))

    @property
    def scale_state(self):
        return self._scale

    @scale_state.setter
    def scale_state(self, state):
        if state in SCALE_STATES and state == (self.scale_state + 1) % 4:
            self._scale = state
        else:
            raise ValueError('Invalid scale state')

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
        return self._cell.zero()

    def cell_set_ration(self, actual_weight):
        self._cell.ratio = actual_weight / self._cell.get_data()

    def cell_weight(self):
        return self._cell.get_weight()

    def cell_wait_for_weight_total(self, weight, timeout=None, wait_secs: float=0, reversed_condition=False):
        start_counter = time.perf_counter()
        while self.cell_weight() < weight and not reversed_condition\
                or reversed_condition and self.cell_weight() > weight:
            if timeout:
                if time.perf_counter() > timeout + start_counter:
                    return False
            time.sleep(wait_secs)
        return True

    def controlled_serve(self, pump_n_weight: list):
        if self.state == 0 and self.scale_state == 0:
            self.state = 3  # locks state
            self.scale_state = 1  # waiting for glass
            if self.state != 3:
                logger.critical(
                    'Trying to serve in controlled state, but there is a state lock error (locked: %s, state:%s!'
                    % (str(self.locked), str(self.state))
                )
                self.scale_state = 0
                self.state = 0  # damage control
                return False
            glass_detected = self.cell_wait_for_weight_total(
                settings.WEIGHT_CELL_GLASS_DETECTION_VALUE,
                timeout=settings.WEIGHT_CELL_GLASS_DETECTION_TIMEOUT,
                wait_secs=0.01
            )
            time.sleep(settings.DELAY_BEFORE_SERVING)
            glass_detected_weight = self.cell_weight()
            if not glass_detected and not settings.ALLOW_NO_GLASS_DETECTION:
                logger.debug('Glass not detected (only %s)' % str(glass_detected_weight))
                return False
            self.scale_state = 2  # serving
            for pump, weight in pump_n_weight:
                current_weight = self.cell_weight()
                if weight < settings.WEIGHT_CELL_MINIMUM_DETECTION:
                    pass
                try:
                    self.demux_start(pump)
                    quantity_reached = self.cell_wait_for_weight_total(
                        weight + current_weight,
                        timeout=settings.WEIGHT_CELL_SERVING_TIMEOUT,
                        wait_secs=0,
                    )
                finally:
                    self.demux_stop(pump)
                if not quantity_reached:
                    logger.info(
                        'Pump %i is not serving within %s. Stopping cocktail'
                        % (pump, str(settings.WEIGHT_CELL_SERVING_TIMEOUT))
                    )
                    self.cell_wait_for_weight_total(
                        glass_detected_weight + settings.WEIGHT_CELL_MINIMUM_DETECTION,
                        timeout=None,
                        wait_secs=1,
                        reversed_condition=True,
                    )  # we wait until glass removed
                    self.scale_state = 0
                    self.state = 0  # release state lock
                    return False
                time.sleep(settings.DELAY_BETWEEN_SERVINGS)
            logger.debug('Finished serving')
            self.demux_stop()
            self.scale_state = 3  # done, wait for glass lifting
            self.cell_wait_for_weight_total(
                glass_detected_weight + settings.WEIGHT_CELL_MINIMUM_DETECTION,
                timeout=None,
                wait_secs=1,
                reversed_condition=True,
            )  # we wait until glass removed
            self.scale_state = 0
            self.state = 0  # release state lock
            return True
        else:
            logger.error('Serving in controlled state refused')
            return False
