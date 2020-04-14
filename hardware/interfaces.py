from itertools import count
from threading import Lock
import time

from django.utils.log import logging

from django.conf import settings
from hardware.singletonmixin import Singleton
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

from hardware import process_order

logger = logging.getLogger('autobar')


class HardwareInterface(Singleton):
    def __init__(self):
        print('Interface id', id(self))
        self._serving = False
        self._last_order = None

        # cell
        if CELL_AVAILABLE:
            # TODO config of cell should happen in HX711
            self._cell = HX711(settings.GPIO_DT, settings.GPIO_SCK)
            defaults = settings.WEIGHT_CELL_DEFAULT[self._cell.channel][self._cell.gain]
            self._cell.ratio = defaults['ratio']
            self._cell.offset = defaults['offset']
        elif settings.INTERFACE_USE_DUMMY:
            self._cell = DummyCell()
        else:
            self._cell = None

        # buttons
        pass

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
