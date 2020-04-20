import subprocess
import time

from django.utils.log import logging
from django.conf import settings

from gpiozero import Button, LED
from gpiozero.pins.mock import MockFactory

from hardware.singletonmixin import Singleton
try:
    from hardware.weight import WeightModule
except RuntimeError:
    class WeightModule:
        dummy = True
        def init_from_settings_and_config(self, settings, config):
            print('No WeightModule')
        def kill_current_task(self):
            print('Kill task called')
        def close(self):
            pass
from hardware.pumps import Pumps

from recipes.models import Configuration

logger = logging.getLogger('autobar')


class CocktailArtist(Singleton):  # inherits Singleton, there can only be one artist at a time
    def __init__(self):
        print('Artist id', id(self))  # unique

        self.busy = False  # ready to take orders
        self.current_order = None  # not mixing anything
        self.weight_module = WeightModule()
        self.pumps = None
        self.red_button = None
        self.green_button = None
        self.green_button_led = None
        self.reload_with_new_config()

    def close(self):
        self.weight_module.close()
        if self.pumps is not None:
            self.pumps.close()
        if self.red_button is not None:
            self.red_button.close()
        if self.green_button is not None:
            self.green_button.close()
        if self.green_button_led is not None:
            self.green_button_led.close()

    def reload_with_new_config(self, config=None):
        logger.info('Cocktail artist loads config')
        self.close()
        if config is None:
            config = Configuration.get_solo()

        self.weight_module.init_from_settings_and_config(settings, config)

        # gpiozero objects
        pin_factory = MockFactory() if config.hardware_use_dummy else None
        self.pumps = Pumps(pin_factory)
        self.red_button = Button(
            pin=settings.GPIO_RED_BUTTON,
            bounce_time=config.button_bounce_time_red,
            hold_time=config.button_hold_time_red,
            pin_factory=pin_factory)
        self.red_button.when_held = self.on_red_button
        self.green_button = Button(
            pin=settings.GPIO_GREEN_BUTTON,
            bounce_time=config.button_bounce_time_green,
            hold_time=config.button_hold_time_green,
            pin_factory=pin_factory)
        self.green_button.when_held = self.on_green_button
        self.green_button_led = LED(pin=settings.GPIO_GREEN_BUTTON_LED, pin_factory=pin_factory)

    def on_green_button(self):
        logger.debug('Green button pressed')
        if self.current_order is not None and self.current_order.status == 1:
            self.force_serve_state()

    def on_red_button(self):
        logger.debug('Red button pressed')
        self.close_browser()

    def shutdown(self):
        logger.info('Shutdown called')
        subprocess.call(['sudo', 'shutdown', '-h', 'now'], shell=False)

    def close_browser(self):
        logger.info('Close chromium browser')
        subprocess.call(['killall', 'chromium-browser'], shell=False)

    def clean_pumps(self, start_at_pump=0):
        nb_pumps = len(settings.GPIO_PUMPS)
        if self.busy:
            logger.info('Clean pumps command ignored because the Artist is busy')
            return
        if start_at_pump < nb_pumps and not self.weight_module.dummy:
            logger.info('Will now clean pump %s' % start_at_pump)
            self.busy = True
            def end():
                self.pumps.stop(start_at_pump)
                self.busy = False
                self.clean_pumps(start_at_pump=start_at_pump + 1)
            self.pumps.start(start_at_pump)
            self.weight_module.trigger_on_condition(stop, lambda weight: weight < -50, 60, stop)
        else:
            logger.info('Done cleaning pumps')

    def force_serve_state(self):
        # must not bounce
        if self.busy and self.current_order is not None:
            if self.current_order.status == 1:
                self.move_current_order_to_serving()
            if self.current_order.status == 2:
                logger.info('Cannot force already serving, abandon (TODO could pass)')
                self.abandon_current_order()

    def emergency_stop(self):
        self.weight_module.kill_current_task()
        self.abandon_current_order()
        logger.info('Emergency stop!')

    def abandon_current_order(self):
        self.pumps.stop_all()
        self.green_button_led.off()
        logger.info('Abandon current order %s' % self.current_order)
        if self.current_order is not None and self.current_order.status != 4:
            # pass this if already abandoned
            self.current_order.status = 4  # abandon
            self.current_order.save()  # triggers order_post_save but we won't do anything
        self.current_order = None  # forget about current order
        self.busy = False  # ready to take on new orders

    def move_current_order_to_serving(self):
        # no verification on status, do it outside this method
        # this is executed in a separate thread, so sleep is not a problem
        config = Configuration.get_solo()
        time.sleep(config.ux_delay_before_start_serving)
        self.current_order.status = 2
        self.current_order.save()

    def move_current_order_to_finished(self):
        self.green_button_led.off()
        self.current_order.status = 3
        self.current_order.save()
        self.current_order = None  # forget about current order
        self.busy = False  # ready to take on new orders

    def wait_for_glass(self):
        config = Configuration.get_solo()
        pass_this_step_condition = lambda weight: weight > config.ux_glass_detection_value
        def glass_timeout():
            if config.ux_serve_even_if_no_glass_detected:
                self.move_current_order_to_serving()
            else:
                logger.info('Time out while waiting for glass for %s' % self.current_order)
                self.abandon_current_order()
        if self.weight_module.trigger_on_condition(
            self.move_current_order_to_serving,
            pass_this_step_condition,
            config.ux_timeout_glass_detection,
            glass_timeout
        ):
            logger.debug('Will move %s to serving when glass is detected' % self.current_order)
            return
        else:
            logger.error('Could not start background task in WaitForGlass state for %s' % self.current_order)
            return self.abandon_current_order()

    def get_available_dispenser(self, dose):
        config = Configuration.get_solo()
        dispensers_query = dose.ingredient.dispensers(filter_out_empty=config.ux_empty_dispenser_makes_mix_not_available)
        if dispensers_query.exists():
            return dispensers_query[0]
        else:
            return None

    def serve_dose(self, dose):
        config = Configuration.get_solo()
        dispenser = self.get_available_dispenser(dose)
        if dispenser is None:
            # can't serve
            logger.error('No available dispenser providing %s. Stopping cocktail' % dose.ingredient)
            return self.abandon_current_order()
        current_weight = self.weight_module.make_constant_weight_measure()
        stop_serving_when = lambda weight: ((weight - current_weight) > dose.weight)
        logger.debug('Current weight %sg, will stop when I reach %sg more' % (current_weight, dose.weight))
        def finished_dose():
            self.pumps.stop(dispenser.number)
            time.sleep(config.ux_delay_between_two_doses)
            self.current_order.doses_served += 1
            self.current_order.save()
        def timeout_serving():
            self.pumps.stop(dispenser.number)
            logger.info('Pump %i is not serving within %s seconds' % (dispenser.number, str(config.ux_timeout_serving)))
            if config.ux_mark_not_serving_dispensers_as_empty:
                logger.info('Mark %s as empty' % dispenser)
                dispenser.is_empty = True
                dispenser.save()
        self.pumps.start(dispenser.number)
        if self.weight_module.trigger_on_condition(finished_dose, stop_serving_when, config.ux_timeout_serving, timeout_serving):
            logger.debug('Started serving %s using %s' % (dose, dispenser))
            return
        else:
            self.pumps.stop(dispenser.number)
            logger.error('Could not start background task to serve %s for %s' % (dose, self.current_order))
            return self.abandon_current_order()

    def serve(self):
        config = Configuration.get_solo()
        self.green_button_led.blink(
            on_time=config.button_blink_time_led_green,
            off_time=config.button_blink_time_led_green)
        doses = self.current_order.mix.ordered_doses() if self.current_order.mix else []
        if self.current_order.doses_served < len(doses):
            # we have a new dose to serve
            dose = doses[self.current_order.doses_served]
            self.serve_dose(dose)
        elif self.current_order.doses_served == len(doses):
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
                available = 'no mix' if order.mix is None else order.mix.is_available()
                logger.error('%s refused (was I busy?: %s, is available?: %s)' % (order, self.busy, available))
                if order.accepted:
                    order.accepted = False
                    return order.save()
                return

        if order.accepted and self.current_order == order and self.busy:
            # current accepted order is processed here
            if order.status == 1:
                config = Configuration.get_solo()
                if config.ux_use_green_button_to_start_serving:
                    pass  # nothing to do, button press will trigger next state
                else:
                    self.wait_for_glass()
            elif order.status == 2:
                self.serve()
            # elif order.status: don't care
