class Pump:
    def __init__(self):
        self.off()

    def on(self):
        self.is_on = True

    def off(self):
        self.is_on = False

class Pumps:
    def __init__(self):
        self.pumps = [Pump() for pin in []]

    def stop_all(self):
        return [pump.off() for pump in self.pumps]

    def stop(self, pump_id):
        pass

    def start(self, pump_id):
        pass
