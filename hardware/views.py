from django.views import View
from django.http import JsonResponse
from django.utils.log import logging
from django.conf import settings

from hardware.serving import CocktailArtist

logger = logging.getLogger('autobar')


class WhatIsArtistDoingView(View):
    def get(self, request, *args, **kwargs):
        artist = CocktailArtist.getInstance()
        return JsonResponse(
            {
                'busy': artist.busy,
                'current_order': artist.current_order
            }
        )

class EmergencyStopView(View):
    def post(self, request, *args, **kwargs):
        artist = CocktailArtist.getInstance()
        response = {
            'busy': artist.busy,
            'current_order': artist.current_order,
        }
        artist.emergency_stop()
        return JsonResponse(response)
