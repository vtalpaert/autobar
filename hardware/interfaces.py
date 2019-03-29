from collections import namedtuple
from itertools import count
from threading import Lock

from autobar import settings
from hardware.singletonmixin import Singleton
from hardware.demultiplexer import DeMultiplexer
try:
    from hardware.hx711 import HX711
    CELL_AVAILABLE = True
except RuntimeError:
    CELL_AVAILABLE = False
from hardware.js_pygame import Joystick


INTERFACE_STATES = {
    0: 'free',
    1: 'manual',
    2: 'controlled',
}


class HardwareInterface(Singleton):
    def __init__(self):
        self._state_mutex = Lock()
        self._state = 0
        self._last_button = None
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
            self._cell = HX711(17, 18)
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
            if state == 0 or state != 0 and self._state_mutex.acquire():
                self._state = state

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
                self._state_mutex.release()
                self.state = 0

    def cell_zero(self):
        return self._cell.zero()

    def cell_set_ration(self, actual_weight):
        self._cell.ratio = actual_weight / self._cell.get_data()

    def cell_weight(self):
        return self._cell.get_weight()
