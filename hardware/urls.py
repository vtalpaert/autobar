from django.urls import path

from .views import WhatIsArtistDoingView, EmergencyStopView

urlpatterns = [
    path('hardware/info', WhatIsArtistDoingView.as_view(), name='hardware_info'),
    path('hardware/emergencystop', EmergencyStopView.as_view(), name='emergency_stop'),
]
