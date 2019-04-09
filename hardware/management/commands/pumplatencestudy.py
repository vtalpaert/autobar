import csv
import time


from django.core.management.base import BaseCommand

from hardware.interfaces import HardwareInterface
from hardware.hx711 import GPIOQueue


def clean_data(data):
    clean = []
    for ts, weight, target in data:
        if clean:
            if clean[-1][1] == weight:
                continue
        clean.append((ts, weight, target))
    return clean


class Command(BaseCommand):
    help = 'Outputs a .csv for measuring the inertia of the pump and the corresponding weights'

    def handle(self, *args, **options):
        pump = 9  # int(input('Enter a pump number for the tests: '))
        queue_len = int(input('Enter a queue length for the background thread: '))
        target_weight = float(input('Enter a target weight for this experience: '))
        exp_nb = int(input('Enter an experience number: '))

        self.setup(queue_len)
        for i in range(exp_nb):
            time.sleep(0.1)
            data = self.serve(pump, target_weight, extra_time=3)
            if data is False:
                return
            data = clean_data(data)
            filename = 'pump%i_queue%i_target%i_%s.csv' % (pump, queue_len, int(target_weight), str(i).zfill(3))

            with open(filename, 'w') as f:
                writer = csv.writer(f)
                writer.writerows(data)
            input('Exp %i done, press enter when ready')

    def setup(self, queue_len):
        self.interface = HardwareInterface.getInstance()
        #self.interface._cell._queue.stop()
        #time.sleep(0.1)
        #self.interface._cell._queue = GPIOQueue(self.interface._cell, queue_len=queue_len, sample_wait=0, partial=True)
        #self.interface._cell._queue.start()
        time.sleep(0.1)
        self.interface.cell_zero()

    def serve(self, pump, target_weight, extra_time):
        data = []
        start_counter = time.perf_counter()
        measured_weight = self.interface.cell_weight()
        if measured_weight is not False:
            try:
                self.interface.demux_start(pump)
                while measured_weight < target_weight:
                    measured_weight = self.interface.cell_weight()
                    print(measured_weight)
                    data.append((time.perf_counter() - start_counter, measured_weight, 0))
            finally:
                self.interface.demux_stop(pump)
            last_measured_weight = self.interface.cell_weight()
            finished_serving = time.perf_counter()
            while time.perf_counter() - finished_serving < extra_time:
                measured_weight = self.interface.cell_weight()
                data.append((time.perf_counter() - start_counter, measured_weight, last_measured_weight))
            return data
        return False
