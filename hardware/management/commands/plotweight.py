import time
from collections import deque

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style

import urllib.request, json 

from django.core.management.base import BaseCommand


class Plotter:
    def __init__(self, url, size):
        self.url = url
        self.ts = deque(maxlen=size)
        self.raw = deque(maxlen=size)
        self.weight = deque(maxlen=size)
        style.use('fivethirtyeight')
        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(1,1,1)

    def animate(self, i):
        with urllib.request.urlopen(self.url) as url:
            data = json.loads(url.read().decode())
            if data['converted_raw_value'] is not None:
                self.ts.append(time.time())
                self.raw.append(data['converted_raw_value'])
                self.weight.append(data['weight'])
            self.ax1.clear()
            plt.title('Weight plotting')
            plt.xlabel('timestamp [s]')
            plt.ylabel('weight [g]')
            self.ax1.plot(self.ts, self.raw)
            self.ax1.plot(self.ts, self.weight)


class Command(BaseCommand):
    help = 'Plot the weight live'

    def add_arguments(self, parser):
        parser.add_argument('url', default='http://raspberrypi:8000', help='Site url such as http://raspberrypi:8000 or http://localhost:8000')
        parser.add_argument('size', type=int, help='Number of values to remember')

    def handle(self, *args, **options):
        api_url = options['url'] + '/hardware/weightmeasure'
        p = Plotter(api_url, options['size'])
        ani = animation.FuncAnimation(p.fig, p.animate, interval=10)  # interval in [ms]
        plt.show()
