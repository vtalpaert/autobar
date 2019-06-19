from abc import ABC
import time

from django.utils.log import logging

from django.conf import settings
from hardware.background_threads import BackgroundThread

logger = logging.getLogger('autobar')


class AdvanceOrder(BackgroundThread, ABC):
    def __init__(self, interface, order):
        self.interface = interface
        self.order = order
        super().__init__(target=self.advance_order)

    def advance_order(self):
        raise NotImplementedError()


class WaitForGlass(AdvanceOrder):
    """The order is accepted, we are waiting for the glass"""
    def advance_order(self):
        # will move status to 'Serving'
        glass_detected = self.interface.cell_wait_for_weight_total(
            settings.WEIGHT_CELL_GLASS_DETECTION_VALUE,
            timeout=settings.WEIGHT_CELL_GLASS_DETECTION_TIMEOUT,
            wait_secs=0.01
        )
        time.sleep(settings.DELAY_BEFORE_SERVING)
        glass_detected_weight = self.interface.cell_weight()
        if not glass_detected and not settings.ALLOW_NO_GLASS_DETECTION:
            # refused
            logger.debug('Glass not detected (only %s)' % str(glass_detected_weight))
            self.order.status = 4  # abandon
            self.order.accepted, self.interface._last_order = False, None
            self.interface.state = 0  # abandon this order
            return self.order.save()
        else:
            # status goes to 'Serving' here
            self.order.status = 2  # serving
            logger.debug('Glass detected (weight %s)' % str(glass_detected_weight))
            return self.order.save()


class Serve(AdvanceOrder):
    def _wait_for_glass_removed(self, glass_weight):
        self.interface.cell_wait_for_weight_total(
            glass_weight + settings.WEIGHT_CELL_MINIMUM_DETECTION,
            timeout=1,
            wait_secs=1,
            reversed_condition=True,
        )

    def advance_order(self):
        # will move status to 'Done'
        doses = self.order.mix.ordered_doses() if self.order.mix else []
        logger.debug(str(doses))
        glass_weight = self.interface.cell_weight()

        for dose in doses:
            dispensers_query = dose.ingredient.dispensers(ignore_empty=False)
            if not dispensers_query.exists():
                # refuse order
                logger.error('No available dispenser providing %s. Stopping cocktail' % dose.ingredient)
                self.order.status = 4  # abondon
                self.order.accepted, self.interface._last_order = False, None
                self.interface.state = 0
                return self.order.save()
            dispenser, weight = dispensers_query[0], dose.quantity
            current_weight = self.interface.cell_weight()
            if weight < settings.WEIGHT_CELL_MINIMUM_DETECTION:
                logger.debug(
                    '%s is under WEIGHT_CELL_MINIMUM_DETECTION (%s)'
                    % (dose, settings.WEIGHT_CELL_MINIMUM_DETECTION)
                )
                continue  # next dose
            try:
                self.interface.demux_start(dispenser.number)
                quantity_is_reached = self.interface.cell_wait_for_weight_total(
                    weight + current_weight,
                    timeout=settings.WEIGHT_CELL_SERVING_TIMEOUT,
                    wait_secs=0,
                )
            finally:
                self.interface.demux_stop(dispenser.number)
            if not quantity_is_reached:
                logger.info(
                    'Pump %i is not serving within %s seconds'
                    % (dispenser.number, str(settings.WEIGHT_CELL_SERVING_TIMEOUT))
                )
                if self.interface.cell_weight() < current_weight + 2 * settings.WEIGHT_CELL_MINIMUM_DETECTION:
                    # seems like the dispenser is empty
                    if settings.MARK_NOT_SERVING_DISPENSERS_AS_EMPTY:
                        logger.info('Marked %s as empty' % dispenser)
                        dispenser.is_empty = True
                        dispenser.save()

                # wait for glass removed
                self._wait_for_glass_removed(glass_weight)

                # abandon
                self.order.state = 4
                self.order.accepted = False
                self.state = 0
                self._last_order = None
                return order.save()
            time.sleep(settings.DELAY_BETWEEN_SERVINGS)
        self.interface.demux_stop()
        logger.info('Served one %s.' % self.order.mix)
        self.order.status, self.interface._last_order = 3, None  # done
        self._wait_for_glass_removed(glass_weight)
        self.interface.state = 0  # release state lock
        return self.order.save()

