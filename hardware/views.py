from django.views import View
from django.http import JsonResponse
from django.utils.log import logging

from recipes.models import Configuration
from hardware.serving import CocktailArtist

logger = logging.getLogger('autobar')


class EmergencyStopView(View):
    def post(self, request, *args, **kwargs):
        artist = CocktailArtist.getInstance()
        response = {
            'busy': artist.busy,
            'current_order': artist.current_order.id if artist.current_order is not None else None,
        }
        artist.emergency_stop()
        return JsonResponse(response)

class WeightMeasureView(View):
    def get(self, request, *args, **kwargs):
        artist = CocktailArtist.getInstance()
        wm = artist.weight_module
        if wm.dummy:
            weight = raw = converted = '-1'
            queue = []
        else:
            weight = wm.make_constant_weight_measure()
            raw = wm.get_value()
            converted = wm.convert_value_to_weight(raw) if raw else None
            queue = list(wm.queue)
        response = {
            'weight': weight,
            'raw_value': raw,
            'converted_raw_value': converted,
            'queue': queue,
        }
        return JsonResponse(response)
