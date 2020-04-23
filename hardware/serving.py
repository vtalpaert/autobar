import subprocess
import time
import threading

from django.utils.log import logging
from django.conf import settings

from gpiozero import Button, LED
from gpiozero.pins.mock import MockFactory

from hardware.singletonmixin import Singleton
try:
    from hardware.weight import WeightModule
except (RuntimeError, ModuleNotFoundError):
    class WeightModule:
        dummy = True
        def init_from_settings_and_config(self, settings, config):
            print('No WeightModule')
        def make_constant_weight_measure(self, *args, **kwargs):
            return 100
        def close(self):
            pass
from hardware.pumps import Pumps

from recipes.models import Configuration, Dispenser

logger = logging.getLogger('autobar')


class ServeOrderThread(threading.Thread):
    def __init__(self, order, artist):
        super().__init__()
        self.deamon = True
        self.exit_event = threading.Event()
        self.order = order
        self.config = artist.config
        self.artist = artist
        self.green_button = None
        self.green_button_led = None

    def init_gpio(self):
        pin_factory = MockFactory() if self.config.hardware_use_dummy else None
        self.green_button = Button(
            pin=settings.GPIO_GREEN_BUTTON,
            bounce_time=self.config.button_bounce_time_green,
            hold_time=self.config.button_hold_time_green,
            pin_factory=pin_factory)
        self.green_button_led = LED(pin=settings.GPIO_GREEN_BUTTON_LED, pin_factory=pin_factory)

    def close_gpio(self):
        if self.green_button is not None:
            self.green_button.close()
        if self.green_button_led is not None:
            self.green_button_led.close()

    def abandon_order(self):
        logger.info('Abandon %s' % self.order)
        self.order.status = 4
        self.order.save()

    def wait_to_start(self):
        logger.debug('Waiting to start %s' % self.order)
        self.green_button_led.on()
        self.order.status = 1
        self.order.save()

        # this cannot be None, because no max_try is provided
        start_weight = self.artist.weight_module.make_constant_weight_measure()
        logger.debug('Current weight %sg, must reach %sg more for glass detection' % (start_weight, self.config.ux_glass_detection_value))

        start = time.time()
        while True:
            if self.exit_event.is_set():
                logger.debug('Exit thread while waiting to start')
                self.green_button_led.off()
                return False

            if self.config.ux_use_green_button_to_start_serving:
                # button triggers the start
                if self.green_button.is_active:
                    logger.debug('Green button pressed, start serving %s' % self.order)
                    return True
                time.sleep(0.01)  # some delay ? TODO
            else:
                # glass weight triggers the start

                # this call contains a (while weight is None) but for max_try only
                # if weight is None we will come back here later thanks to the while True loop
                weight = self.artist.weight_module.make_constant_weight_measure(clear=False, max_try=10)

                if weight is not None and weight - start_weight > self.config.ux_glass_detection_value:
                    # glass detected
                    logger.debug('Detected a weight above the ux_glass_detection_value (%sg)' % self.config.ux_glass_detection_value)
                    return True

            if time.time() - start > self.config.ux_timeout_glass_detection:  # TODO rename field
                # timeout
                logger.debug('Timeout (%ss) while waiting to start %s' % (self.config.ux_timeout_glass_detection, self.order))
                if self.config.ux_serve_even_if_no_glass_detected:
                    logger.info('No trigger to start serving, but I will do it anyway because ux_serve_even_if_no_glass_detected is True')
                    return True
                self.green_button_led.off()
                return False

    def serve_dose(self, dose):
        if dose.ingredient.added_separately:
            logger.debug('You can add %s separately' % dose.ingredient)
            self.order.doses_served += 1
            self.order.save()
            return True
        dispenser = Dispenser.get_available_dispenser(dose)
        if dispenser is None:
            # no dispenser, that should not happen since we checked is_available
            # but let's imagine two doses share the same ingredient which became empty in the meantime
            logger.error('No available dispenser providing %s. Stopping cocktail' % dose.ingredient)
            return False

        # this cannot be None, because no max_try is provided
        start_weight = self.artist.weight_module.make_constant_weight_measure()
        logger.debug('Current weight %sg, will stop when I reach %sg more' % (start_weight, dose.weight))

        logger.debug('Starting pump %s' % dispenser.number)
        if not self.artist.pumps.start(dispenser.number):
            # it did not start, Pumps logs by itself the problem
            return False

        logger.debug('Start serving %s using %s' % (dose, dispenser))
        start = time.time()
        while True:  # main loop
            if self.exit_event.is_set():
                # exit called
                logger.debug('Exit thread while serving %s for %s' % (dose, self.order))
                logger.debug('Stopping pump %s' % dispenser.number)
                self.artist.pumps.stop(dispenser.number)
                return False

            # this call contains a (while weight is None) but for max_try only
            # if weight is None we will come back here later thanks to the while True loop
            weight = self.artist.weight_module.make_constant_weight_measure(clear=False, max_try=10)

            if weight is not None and weight - start_weight > dose.weight:
                # weight reached
                logger.debug('I finished %s for %s' % (dose, self.order))
                logger.debug('Stopping pump %s' % dispenser.number)
                self.artist.pumps.stop(dispenser.number)
                time.sleep(self.config.ux_delay_between_two_doses)
                end_weight = self.artist.weight_module.make_constant_weight_measure()
                logger.debug('I distributed %i grams when you asked for %i grams' % (end_weight - start_weight, dose.weight))
                self.order.doses_served += 1
                self.order.save()
                return True

            if time.time() - start > self.config.ux_timeout_serving:
                # timeout
                logger.debug('Timeout (%ss) while serving %s for %s using pump %i' % (self.config.ux_timeout_serving, dose, self.order, dispenser.number))
                logger.debug('Stopping pump %s' % dispenser.number)
                self.artist.pumps.stop(dispenser.number)
                if self.config.ux_mark_not_serving_dispensers_as_empty and not dispenser.is_empty:
                    logger.info('Mark %s as empty' % dispenser)
                    dispenser.is_empty = True
                    dispenser.save()
                return False

            if self.green_button.is_active:
                # button interruption
                logger.debug('Button interrupt while serving %s for %s' % (dose, self.order))
                logger.debug('Stopping pump %s' % dispenser.number)
                self.artist.pumps.stop(dispenser.number)
                return False

    def serve_order(self):
        logger.debug('I am starting %s' % self.order)
        self.green_button_led.blink(
            on_time=self.config.button_blink_time_led_green,
            off_time=self.config.button_blink_time_led_green)
        time.sleep(self.config.ux_delay_before_start_serving)
        doses = self.order.mix.ordered_doses()  # we already verified order.mix is True in accept_new_order
        self.order.status = 2
        self.order.save()
        for dose in doses:
            if not self.serve_dose(dose):
                self.green_button_led.off()
                return False
        self.green_button_led.off()
        return True

    def finish_order(self):
        logger.info('Finished %s' % self.order)
        self.order.status = 3
        self.order.save()

    def run(self):
        try:
            self.init_gpio()
            if self.wait_to_start():
                if self.serve_order():
                    self.finish_order()
                else:
                    self.abandon_order()
            else:
                self.abandon_order()
        finally:
            self.artist.pumps.stop_all()
            self.close_gpio()
            self.artist.busy = False  # tell artist we are done


class CocktailArtist(Singleton):  # inherits Singleton, there can only be one artist at a time
    def __init__(self):
        print('Artist id', id(self))  # unique
        self._config = None  # holder
        self.thread = None
        self.busy = False  # ready to take orders
        self.weight_module = WeightModule()
        self.pumps = None
        self.red_button = None
        self.reload_with_new_config()

    def close(self):
        logger.debug('Closing hardware interface')
        self.stop_thread()
        self.weight_module.close()
        if self.pumps is not None:
            self.pumps.close()
        if self.red_button is not None:
            self.red_button.close()

    @property
    def config(self):
        if self._config is None:
            logger.debug('Cocktail artist loads config')
            self._config = Configuration.get_solo()  # even if this is in cache, will keep pointer to it
        return self._config

    def reload_with_new_config(self, config=None):
        self.close()
        self._config = config  # if None, self.config will load a new one
        config = self.config

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
        logger.error('Not implemented')

    def emergency_stop(self):
        logger.info('Emergency stop!')
        self.stop_thread()
        self.pumps.stop_all()

    @property
    def current_order(self):
        if not self.busy or self.thread is None:
            return None
        return self.thread.order

    def stop_thread(self):
        if self.thread is not None:
            logger.debug('Stop thread %s' % self.thread)
            self.thread.exit_event.set()

    def accept_new_order(self, order):
        if self.busy:
            logger.error('We are already busy')
            return False
        if order.mix is None:
            logger.error('Your order has no associated mix')
            return False
        if not order.mix.is_available():
            logger.error('This mix is not available')
            return False

        logger.debug('%s is accepted' % order)
        self.busy = True
        self.thread = ServeOrderThread(order, self)
        self.thread.start()  # good bye
        # thread will set busy = False

        return True  # accepted and thread started
