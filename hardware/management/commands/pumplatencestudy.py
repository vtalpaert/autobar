import csv
import time


from django.core.management.base import BaseCommand

from hardware.interfaces import HardwareInterface
from hardware.hx711 import GPIOQueue


class Command(BaseCommand):
    help = 'Outputs a .csv for measuring the inertia of the pump and the corresponding weights'

    def handle(self, *args, **options):
        pump = int(input('Enter a pump number for the tests: '))
        queue_len = int(input('Enter a queue length for the background thread: '))
        target_weight = float(input('Enter a target weight for this experience: '))

        self.setup(queue_len)
        time.sleep(0.1)
        data = self.serve(pump, target_weight)
        filename = 'pump%i_queue%i_target%i.csv' % (pump, queue_len, int(target_weight))

        with open(filename, 'w') as f:
            writer = csv.writer(f)
            writer.writerows(data)

    def setup(self, queue_len):
        self.interface = HardwareInterface.getInstance()
        self.interface._cell._queue.stop()
        self.interface._cell._queue = GPIOQueue(self, queue_len=queue_len, sample_wait=0, partial=True)
        self.interface._cell._queue.start()
        self.interface.cell_zero()

    def serve(self, pump, target_weight):
        data = []
        start_counter = time.perf_counter()
        try:
            self.interface.demux_start(pump)
            measured_weight = self.interface.cell_weight()
            while measured_weight < target_weight:
                measured_weight = self.interface.cell_weight()
                data.append((time.perf_counter() - start_counter, measured_weight, 0))
        finally:
            self.interface.demux_stop(pump)
        last_measured_weight = self.interface.cell_weight()
        finished_serving = time.perf_counter()
        while time.perf_counter() - finished_serving < 1:  # 1 more second
            measured_weight = self.interface.cell_weight()
            data.append((time.perf_counter() - start_counter, measured_weight, last_measured_weight))
        return data
