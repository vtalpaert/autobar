from django.urls import path

from .views import EmergencyStopView, WeightMeasureView

urlpatterns = [
    path('hardware/emergencystop', EmergencyStopView.as_view(), name='emergency_stop'),
    path('hardware/weightmeasure', WeightMeasureView.as_view(), name='weight_measure'),
]
