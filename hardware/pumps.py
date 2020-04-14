from gpiozero import DigitalOutputDevice

class Pumps:
    def __init__(self):
        self.pumps = [DigitalOutputDevice(pin=pin) for pin in []]

    def stop_all(self):
        return [pump.off() for pump in self.pumps]

    def stop(self, pump_id):
        self.pumps[pump_id].off()

    def start(self, pump_id):
        self.pumps[pump_id].on()
