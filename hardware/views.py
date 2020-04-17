from django.views import View
from django.http import JsonResponse
from django.utils.log import logging

from recipes.models import Configuration
from hardware.serving import CocktailArtist

logger = logging.getLogger('autobar')


class WhatIsArtistDoingView(View):
    def describe(self, artist):
        if not artist.busy or artist.current_order is None:
            return 'Ready to serve'
        else:
            if artist.current_order.status == 1:
                config = Configuration.get_solo()  # leverages cache, so no overload here
                if config.ux_use_green_button_to_start_serving:
                    return 'Presse button to start'
                else:
                    return 'Waiting for glass'
            elif artist.current_order.status == 2:
                return 'Mixing'  # TODO describe more
            elif artist.current_order.status == 3:
                return 'Done'
            elif artist.current_order.status == 4:
                return 'Abandon'
        return 'Unknown'
        
    def get(self, request, *args, **kwargs):
        artist = CocktailArtist.getInstance()
        return JsonResponse(
            {
                'busy': artist.busy,
                'current_order': artist.current_order.id if artist.current_order is not None else None,
                'status_verbose': self.describe(artist)
            }
        )

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
            queue = wm.queue
        response = {
            'weight': weight,
            'raw_value': raw,
            'converted_raw_value': converted,
            'queue': queue,
        }
        return JsonResponse(response)
