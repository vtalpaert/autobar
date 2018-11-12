from collections import namedtuple
from itertools import count

from autobar import settings
from hardware.singletonmixin import Singleton
from hardware.demultiplexer import DeMultiplexerNBits


class GpioInterface(Singleton):
    def __init__(self):
        config_demux = settings.DEMUX
        self._demux = [
            DeMultiplexerNBits(c['outputs'], inh=c['inh'], **c['logic'])
            for c in config_demux
        ]
        self._outputs_mapping, offset = {}, 0
        for demux in self._demux:
            for demux_output in count():
                if demux_output < demux.n:
                    self._outputs_mapping[demux_output + offset] = (demux, demux_output)
                else:
                    offset += demux.n
                    break
        self.nb_outputs = offset

    def demux_write(self, output, inhibit=True):
        try:
            demux, demux_output = self._outputs_mapping[output]
        except KeyError:
            raise ValueError('%s is not a valid output number with your configuration' % output)
        demux.write(demux_output)
        demux.inhibit = inhibit

    def _demux_inhibit(self, output=None, inhibit=True):
        if output is None:
            for demux in self._demux:
                demux.inhibit = inhibit
        else:
            demux, _ = self._outputs_mapping[output]
            demux.inhibit = inhibit

    def demux_stop(self, output=None):
        self._demux_inhibit(output=output, inhibit=True)

    def demux_start(self, output):
        self.demux_write(output, inhibit=False)
