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

    class DummyCell:
        weight = 0

        def get_weight(self):
            self.weight += 1
            return self.weight

from hardware.js_pygame import Joystick

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
        return self._cell.zero()

    def cell_raw_value(self):
        return self._cell.value

    def cell_reset(self):
        self._cell.ratio = 1
        self._cell.offset = 0

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

    def _wait_for_glass(self):
        glass_detected = self.cell_wait_for_weight_total(
            settings.WEIGHT_CELL_GLASS_DETECTION_VALUE,
            timeout=settings.WEIGHT_CELL_GLASS_DETECTION_TIMEOUT,
            wait_secs=0.01
        )
        time.sleep(settings.DELAY_BEFORE_SERVING)
        return glass_detected

    def _wait_for_glass_removed(self, glass_weight):
        self.cell_wait_for_weight_total(
            glass_weight + settings.WEIGHT_CELL_MINIMUM_DETECTION,
            timeout=1,
            wait_secs=1,
            reversed_condition=True,
        )

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
                # will move status to 'Serving'
                glass_detected = self._wait_for_glass()
                glass_detected_weight = self.cell_weight()
                if not glass_detected and not settings.ALLOW_NO_GLASS_DETECTION:
                    # refused
                    logger.debug('Glass not detected (only %s)' % str(glass_detected_weight))
                    order.accepted, self._last_order = False, None
                    self.state = 0  # abandon this order
                    return order.save()
                else:
                    # status goes to 'Serving' here
                    order.status = 2  # serving
                    logger.debug('Glass detected (weight %s)' % str(glass_detected_weight))
                    return order.save()

            elif order.status == 2:
                # will move status to 'Done'
                doses = order.mix.ordered_doses() if order.mix else []
                logger.debug(str(doses))
                glass_weight = self.cell_weight()

                for dose in doses:
                    dispensers_query = dose.ingredient.dispensers(ignore_empty=False)
                    if not dispensers_query.exists():
                        # refuse order
                        logger.error('No available dispenser providing %s. Stopping cocktail' % dose.ingredient)
                        order.accepted, self._last_order = False, None
                        self.state = 0
                        return order.save()
                    dispenser, weight = dispensers_query[0], dose.quantity
                    current_weight = self.cell_weight()
                    if weight < settings.WEIGHT_CELL_MINIMUM_DETECTION:
                        logger.debug(
                            '%s is under WEIGHT_CELL_MINIMUM_DETECTION (%s)'
                            % (dose, settings.WEIGHT_CELL_MINIMUM_DETECTION)
                        )
                        continue  # next dose
                    try:
                        self.demux_start(dispenser.number)
                        quantity_is_reached = self.cell_wait_for_weight_total(
                            weight + current_weight,
                            timeout=settings.WEIGHT_CELL_SERVING_TIMEOUT,
                            wait_secs=0,
                        )
                    finally:
                        self.demux_stop(dispenser.number)
                    if not quantity_is_reached:
                        logger.info(
                            'Pump %i is not serving within %s seconds'
                            % (dispenser.number, str(settings.WEIGHT_CELL_SERVING_TIMEOUT))
                        )
                        if self.cell_weight() < current_weight + 2 * settings.WEIGHT_CELL_MINIMUM_DETECTION:
                            # seems like the dispenser is empty
                            if not settings.IGNORE_EMPTY_DISPENSER:
                                logger.info('Marked %s as empty' % dispenser)
                                dispenser.is_empty = True
                                dispenser.save()

                        # wait for glass removed
                        self._wait_for_glass_removed(glass_weight)

                        # abandon
                        order.accepted = False
                        self.state = 0
                        self._last_order = None
                        return order.save()
                    time.sleep(settings.DELAY_BETWEEN_SERVINGS)
                self.demux_stop()
                logger.info('Served one %s.' % order.mix)
                order.status, self._last_order = 3, None  # done
                self._wait_for_glass_removed(glass_weight)
                self.state = 0  # release state lock
                return order.save()
