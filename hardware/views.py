from django.views import View
from django.http import JsonResponse

from django.conf import settings
from hardware.interfaces import HardwareInterface


class InterfaceView(View):
    def get(self, request, *args, **kwargs):
        interface = HardwareInterface.getInstance()
        return JsonResponse(
            {
                'state': interface.state,
                'state_verbose': settings.INTERFACE_STATES[interface.state],
            }
        )
