from gpiozero import DigitalOutputDevice

from django.conf import settings

class Pumps:
    def __init__(self, pin_factory=None):
        self.pumps = [DigitalOutputDevice(pin=pin, pin_factory=pin_factory) \
            for pin in settings.GPIO_PUMPS]

    def stop_all(self):
        return [pump.off() for pump in self.pumps]

    def stop(self, pump_id):
        self.pumps[pump_id].off()

    def start(self, pump_id):
        self.pumps[pump_id].on()

    def close(self):
        return [pump.close() for pump in self.pumps]
