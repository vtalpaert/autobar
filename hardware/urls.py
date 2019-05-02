from django.urls import path

from .views import InterfaceView

urlpatterns = [
    path('hardware/interface', InterfaceView.as_view(), name='hardware_interface'),
]
