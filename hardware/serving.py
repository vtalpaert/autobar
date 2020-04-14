import subprocess

from django.utils.log import logging
from django.conf import settings

from gpiozero import Button, LED
from gpiozero.pins.mock import MockFactory

from hardware.singletonmixin import Singleton
try:
    from hardware.weight import WeightModule
except RuntimeError:
    class WeightModule:
        def init_from_settings(self, settings):
            print('No WeightModule')
        def kill_current_task(self):
            print('Kill task called')
from hardware.pumps import Pumps

logger = logging.getLogger('autobar')


class CocktailArtist(Singleton):  # inherits Singleton, there can only be one artist at a time
    def __init__(self):
        print('Artist id', id(self))  # unique
        self.busy = False  # ready to take orders
        self.current_order = None  # not mixing anything
        self.weight_module = WeightModule()
        self.weight_module.init_from_settings(settings)

        # gpiozero objects
        pin_factory = MockFactory() if settings.INTERFACE_USE_DUMMY else None
        self.pumps = Pumps(pin_factory)
        self.red_button = Button(pin=settings.GPIO_RED_BUTTON, bounce_time=settings.RED_BUTTON_BOUNCE_TIME, hold_time=settings.RED_BUTTON_HOLD_TIME, pin_factory=pin_factory)
        self.red_button.when_held = self.on_red_button
        self.green_button = Button(pin=settings.GPIO_GREEN_BUTTON, bounce_time=settings.GREEN_BUTTON_BOUNCE_TIME, hold_time=settings.GREEN_BUTTON_HOLD_TIME, pin_factory=pin_factory)
        self.green_button.when_held = self.on_green_button
        self.green_button_led = LED(pin=settings.GPIO_GREEN_BUTTON_LED, pin_factory=pin_factory)

    def on_green_button(self):
        logger.debug('Green button pressed')
        self.force_serve_state()

    def on_red_button(self):
        logger.debug('Red button pressed')
        self.shutdown()

    def shutdown(self):
        logger.info('Shutdown called')
        subprocess.call(['shutdown', '-h', 'now'], shell=False)

    def force_serve_state(self):
        # must not bounce
        if self.busy and self.current_order is not None:
            if self.current_order.status == 1:
                self.move_current_order_to_serving()
            if self.current_order.status == 2:
                self.abandon_current_order()

    def emergency_stop(self):
        self.weight_module.kill_current_task()
        self.abandon_current_order()
        logger.info('Emergency stop!')

    def abandon_current_order(self):
        self.pumps.stop_all()
        self.green_button_led.off()
        if self.current_order.status != 4:
            # pass this if already abandoned
            self.current_order.status = 4  # abandon
            self.current_order.save()  # triggers order_post_save but we won't do anything
        self.current_order = None  # forget about current order
        self.busy = False  # ready to take on new orders

    def move_current_order_to_serving(self):
        # no verification on status, do it outside this method
        # this is executed in a separate thread, so sleep is not a problem
        time.sleep(settings.DELAY_BEFORE_SERVING)
        self.current_order.status = 2
        self.current_order.save()

    def move_current_order_to_finished(self):
        self.green_button_led.off()
        self.current_order.status = 3
        self.current_order.save()
        #self.current_order = None  # forget about current order
        self.busy = False  # ready to take on new orders

    def wait_for_glass(self):
        pass_this_step_condition = lambda weight: weight > settings.WEIGHT_CELL_GLASS_DETECTION_VALUE
        def glass_timeout():
            if settings.SERVE_EVEN_IF_NO_GLASS_DETECTED:
                self.move_current_order_to_serving()
            else:
                logger.info('Time out while waiting for glass for %s' % self.current_order)
                self.abandon_current_order()
        if self.weight_module.trigger_on_condition(
            self.move_current_order_to_serving,
            pass_this_step_condition,
            settings.WEIGHT_CELL_GLASS_DETECTION_TIMEOUT,
            glass_timeout
        ):
            logger.debug('Will move %s to serving when glass is detected' % self.current_order)
            return
        else:
            logger.error('Could not start background task in WaitForGlass state for %s' % self.current_order)
            return self.abandon_current_order()

    def get_available_dispenser(self, dose):
        dispensers_query = dose.ingredient.dispensers(filter_out_empty=True)
        if dispensers_query.exists():
            return dispensers_query[0]
        else:
            return None

    def serve_dose(self, dose):
        dispenser = self.get_available_dispenser(dose)
        if dispenser is None:
            # can't serve
            logger.error('No available dispenser providing %s. Stopping cocktail' % dose.ingredient)
            return self.abandon_current_order()
        current_weight = self.weight_module.make_constant_weight_measure()
        stop_serving_when = lambda weight: weight - current_weight > dose.weight
        def finished_dose():
            self.pumps.stop(dispenser.number)
            time.sleep(settings.DELAY_BETWEEN_SERVINGS)
            order.doses_served += 1
            order.save()
        def timeout_serving():
            self.pumps.stop(dispenser.number)
            logger.info('Pump %i is not serving within %s seconds' % (dispenser.number, str(settings.WEIGHT_CELL_SERVING_TIMEOUT)))
            if settings.MARK_NOT_SERVING_DISPENSERS_AS_EMPTY:
                logger.info('Mark %s as empty' % dispenser)
                dispenser.is_empty = True
                dispenser.save()
        self.pumps.start(dispenser.number)
        if self.weight_module.trigger_on_condition(finished_dose, stop_serving_when, settings.WEIGHT_CELL_SERVING_TIMEOUT, timeout_serving):
            logger.debug('Started serving %s using %s' % (dose, dispenser))
            return
        else:
            self.pumps.stop(dispenser.number)
            logger.error('Could not start background task to serve %s for %s' % (dose, self.current_order))
            return self.abandon_current_order()

    def serve(self):
        self.green_button_led.blink(on_time=settings.GREEN_BUTTON_LED_BLINK_TIME, off_time=GREEN_BUTTON_LED_BLINK_TIME)
        doses = order.mix.ordered_doses() if order.mix else []
        if order.doses_served < len(doses):
            # we have a new dose to serve
            dose = doses[order.doses_served]
            self.serve_dose(dose)
        elif order.doses_served == len(doses):
            # all the doses were served
            self.move_current_order_to_finished()

    def order_post_save(self, sender, instance, created, raw, using, update_fields, **kwargs):
        order = instance

        if created:  # on creation of a new order
            if not self.busy and order.mix and order.mix.is_available():
                # we accept order
                self.busy = True
                order.accepted, self.current_order = True, order
                order.status = 1  # next step, the order is waiting for a glass
                self.green_button_led.on()
                logger.debug('%s was accepted' % order)
                return order.save()
            else:
                logger.error('%s refused (was I busy?: %s, has mix: %s)' % (order, self.busy, order.mix is not None))
                if order.accepted:
                    order.accepted = False
                    return order.save()
                return

        if order.accepted and self.current_order == order and self.busy:
            # current accepted order is processed here
            if order.status == 1:
                if settings.USE_GREEN_BUTTON_TO_START_SERVING:
                    pass  # nothing to do, button press will trigger next state
                else:
                    self.wait_for_glass()
            elif order.status == 2:
                self.serve()
            # elif order.status: don't care
