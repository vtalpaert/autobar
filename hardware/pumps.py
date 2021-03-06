from gpiozero import DigitalOutputDevice
from threading import Lock

from django.conf import settings
from django.utils.log import logging

logger = logging.getLogger('autobar')


class Pumps:
    def __init__(self, pin_factory=None, safety_lock=True):
        self.safety_lock = safety_lock
        if safety_lock:
            self._one_pump_at_a_time = Lock()
            self._started_pump = None
        self.pumps = [DigitalOutputDevice(pin=pin, pin_factory=pin_factory) \
            for pin in settings.GPIO_PUMPS]
        logger.debug('Acquired GPIO control for the pumps, safety is %s' % ('on' if safety_lock else 'off'))

    def stop_all(self):
        if self.safety_lock:
            if self._started_pump is not None:
                logger.debug('You stopped all pumps, including the only running one pump %i' % self._started_pump)
                self._started_pump = None
                self._one_pump_at_a_time.release()
            else:
                logger.debug('You stopped all pumps, even if none was running')
        else:
            logger.debug('All pumps off')
        for pump in self.pumps:
            pump.off()
        return True

    def stop(self, pump_id):
        self.pumps[pump_id].off()
        if self.safety_lock:
            if self._started_pump is not None and self._started_pump == pump_id:
                logger.debug('You stopped the running pump %i' % pump_id)
                self._started_pump = None
                self._one_pump_at_a_time.release()
                return True
            else:
                logger.error('Pump %i is off, but I think %s is still running. You will not be able to start another one' % (pump_id, self._started_pump))
                return False
        else:
            logger.debug('Pump %i off' % pump_id)
            return True

    def start(self, pump_id):
        if self.safety_lock:
            acquired = self._one_pump_at_a_time.acquire()
            if acquired:
                self._started_pump = pump_id
                self.pumps[pump_id].on()
                logger.debug('Pump %i is now the only one started (%s)' % (pump_id, self.pumps[pump_id].is_active))
                return True
            else:
                logger.error('Will not start pump %i because pump %s is already running' % (pump_id, self._started_pump))
                return False
        else:
            self.pumps[pump_id].on()
            logger.debug('Pump %i on (%s)' % (pump_id, self.pumps[pump_id].on()))
            return True

    def close(self):
        logger.debug('Close pumps GPIO interface')
        closed = [pump.close() for pump in self.pumps]
        self.pumps = []  # puts pumps out of scope
        return closed
