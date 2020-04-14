from django.views import View
from django.http import JsonResponse
from django.utils.log import logging
from django.conf import settings

from hardware.serving import CocktailArtist

logger = logging.getLogger('autobar')


class WhatIsArtistDoingView(View):
    def describe(self, artist):
        if not artist.busy or artist.current_order is None:
            return 'Ready to serve'
        else:
            if artist.current_order.status == 1:
                if settings.USE_GREEN_BUTTON_TO_START_SERVING:
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
