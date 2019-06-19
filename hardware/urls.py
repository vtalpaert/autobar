from django.urls import path

from .views import InterfaceView, StopInterfaceView

urlpatterns = [
    path('hardware/interface', InterfaceView.as_view(), name='hardware_interface'),
    path('hardware/interface/stop', StopInterfaceView.as_view(), name='hardware_interface_stop'),
]
