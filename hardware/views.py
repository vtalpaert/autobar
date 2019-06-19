from django.views import View
from django.http import JsonResponse
from django.utils.log import logging
from django.conf import settings

from hardware.interfaces import HardwareInterface

logger = logging.getLogger('autobar')


class InterfaceView(View):
    def get(self, request, *args, **kwargs):
        interface = HardwareInterface.getInstance()
        return JsonResponse(
            {
                'state': interface.state,
                'state_verbose': settings.INTERFACE_STATES[interface.state],
            }
        )

class StopInterfaceView(View):
    def post(self, request, *args, **kwargs):
        interface = HardwareInterface.getInstance()
        response = {
            'previous_state': interface.state,
            'was_locked': interface.locked,
        }
        interface.state = 0
        interface.demux_stop()
        logger.info('Stopped interface')
        return JsonResponse(response)
