import csv
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter


PLOT_OVERSHOOT_TO_RATE = False
PLOT_OVERSHOOT_TO_ESTIMATED = False

pump9_queue1_target10 = (
    '../pumptests/pump9_queue1_target10_1.csv',  # good
    '../pumptests/pump9_queue1_target10_2.csv',
    #'../pumptests/pump9_queue1_target10_3.csv',
    '../pumptests/pump9_queue1_target10_4.csv',  # good
    '../pumptests/pump9_queue1_target10_5.csv',  # good
    '../pumptests/pump9_queue1_target10_6.csv',  # good
    '../pumptests/pump9_queue1_target10_7.csv',
    '../pumptests/pump9_queue1_target10_8.csv',
)

pump9_queue1_target40 = (
    #'../pumptests/pump9_queue1_target40.csv',
    '../pumptests/pump9_queue1_target40_2.csv',
    '../pumptests/pump9_queue1_target40_3.csv',
)

pump9_queue10_target15 = ['../pumptests/pump9_queue10_target15_%s.csv' % str(i).zfill(3) for i in range(0, 39, 2)]

targets = {
    10: {'files': pump9_queue1_target10},
    40: {'files': pump9_queue1_target40},
    15: {'files': pump9_queue10_target15},
}


fitted_coeffs = {
    15: (0.45930872, 2.72208533),
    'all': (0.18955291, 6.5368912),
    'test': (0, 8),
}

def get_simple_data(filename):
    with open(filename, 'r') as f:
        data = []
        times = []
        reader = csv.reader(f, delimiter=",")
        for row in reader:
            ts, weight, target = list(map(float, row))
            if data:
                #if data[-1][1] == weight:
                #    continue
                #else:
                #    times.append(ts - data[-1][0])
                if ts - data[-1][0] < 0.01:
                    continue
                times.append(ts - data[-1][0])
            data.append((ts, weight, target))
        times = np.array(times)
        print('Period %s seconds, std %s' % (str(np.mean(times)), str(np.std(times))))
        return np.array(data)


def calculate_naive_rates():
    rates = []
    for target in [15]:
        for filename in targets[target]['files']:
            data = get_simple_data(filename)
            lin_data = []
            for x, y in zip(data[:, 0], data[:, 1]):
                if 10 < y < 20:
                    lin_data.append((x, y))
            lin_data = np.array(lin_data)
            coeffs = np.polyfit(lin_data[:, 0], lin_data[:, 1], 1)
            rates.append(coeffs)
    rates = np.array(rates)
    rates = np.concatenate((rates, np.reshape(np.divide(-rates[:, 1], rates[:, 0]), (-1, 1))), 1)
    print(np.mean(rates, 0), np.std(rates, 0))
    return rates


def estimate_overshoot(rates):
    rates = np.clip(rates, 10, 30)
    return [fitted_coeffs['test'][0]*np.mean(rates[max(i-3, 0):i])+fitted_coeffs['test'][1] for i in range(1, len(rates)+1)]


all_overshoots = []
all_rates_to_final = []
def plot_file_list(l, fixed_color=None):
    plt.figure(1)
    rate_to_final = []
    overshoots = []
    for i, (filename, color) in enumerate(zip(l, matplotlib.colors.cnames)):
        if fixed_color is not None:
            color = list(matplotlib.colors.cnames)[fixed_color]
        data = get_simple_data(filename)
        x, y = data[:, 0], data[:, 1]
        one_second = next((i for i, x in enumerate(x) if x > 1), None)
        reached_at_step = next((i for i, x in enumerate(data[:, 2]) if x), None)
        yhat = savgol_filter(y, 31, 2)
        der = savgol_filter(yhat, 5, 1, deriv=1)
        raw_der = (y[1:] - y[:-1]) / (x[1:] - x[:-1])
        der_hat = savgol_filter(y, 31, 1, deriv=1)
        #rate_over_8 = max(next((i for i, x in enumerate(der) if x > 5 and i > 3), None), one_second)
        #limited_to = der[reached_at_step - 4:reached_at_step + 2]
        #rate_at_reached = np.mean(limited_to)
        #err = np.std(limited_to)
        #final_overshoot = y[-1]-data[-1, 2]
        #rate_to_final.append((rate_at_reached, final_overshoot))
        #for i, t in enumerate(x):
        #    if i > rate_over_8 and i > one_second:
        #        o = estimate_overshoot(raw_der[i-3:i])[-1]
        #        if y[i] + o >= 15:
        #            stop_now = i
        #            #print('t', t, y[i] + o, 'error', o - final_overshoot)
        #            #print()
        #            overshoots.append((final_overshoot, o))
        #            break
        #plt.plot(x, y, color=color, label=str(i+1))
        plt.plot(x, der_hat)#, color=color, label=str(i+1))  # clean derivative
        #plt.plot(x, der_hat)#, color=color, linestyle=':')
        #plt.plot(x[reached_at_step - 4:reached_at_step + 2], yhat[reached_at_step - 4:reached_at_step + 2] - data[-1, 2], color=list(matplotlib.colors.cnames.keys())[int(err>5)])
        #plt.plot(x, data[:, 2], color=color)
        #plt.plot(x[rate_over_8:reached_at_step], estimate_overshoot(der[rate_over_8:reached_at_step]) - final_overshoot, color=color, linestyle='-.')
        #plt.plot(x[rate_over_8:reached_at_step], estimate_overshoot(raw_der[rate_over_8:reached_at_step]) - final_overshoot, color=color)


    if PLOT_OVERSHOOT_TO_RATE:
        plt.figure(2)
        all_rates_to_final.extend(rate_to_final)
        all_overshoots.extend(overshoots)
        rates, overshoot = zip(*rate_to_final)
        plt.scatter(rates, overshoot)
    if PLOT_OVERSHOOT_TO_ESTIMATED:
        plt.figure(3)
        overshoot, estimated = zip(*overshoots)
        plt.scatter(overshoot, estimated)


#plot_file_list(pump9_queue10_target15)
plot_file_list(pump9_queue1_target40)
#plot_file_list(pump9_queue1_target10)

if PLOT_OVERSHOOT_TO_RATE:
    plt.figure(2)
    plt.ylabel('Final overshoot [g]')
    plt.xlabel('Nominal serving rate [g/s]')
    rates, overshoot = zip(*all_rates_to_final)
    coeffs = np.polyfit(rates, overshoot, 1)
    x = np.linspace(0, 45)
    y = np.polyval(coeffs, x)
    plt.plot(x, y)
    plt.legend(['Fitting coefficients: %s' % str(coeffs)])
    plt.title('Linear relationship between overshoot and liquid level')

if PLOT_OVERSHOOT_TO_ESTIMATED:
    plt.figure(3)
    overshoot, estimated = zip(*all_overshoots)
    plt.title('Estimated overshoot according to real value')


plt.show()


class WeightAnticipator:
    frequency = 100
    rising_rate = 0.15

    def __init__(goal_weight):
        self.goal_weight = goal_weight
        self.measures = []
        if self.frequency != 100:
            raise NotImplementedError('Only 100 Hz data is tested')
    
    def update(self, measure):
        self.measures.append(measure)
    
    def current_rates(self):
        return savgol_filter(self.measures, 31, 1, deriv=1)


class NaiveAnticipator:
    naive_overshoot = 8

    def __init__(goal_weight):
        self.goal_weight = goal_weight
    
    def update(self, measure):
        self.last_measure = measure

    def must_stop():
        return self.last_measure + self.naive_overshoot > self.goal_weight
