from django.urls import path, include
from django.views.generic.base import RedirectView

from recipes import views

urlpatterns = [
    path('mixes/<slug:sort_by>/<slug:subsort_by>/', views.Mixes.as_view(), name='mixes_ss'),
    path('mixes/<slug:sort_by>/', views.Mixes.as_view(), name='mixes_s'),
    path('mixes/', views.Mixes.as_view(), name='mixes'),
    path('', RedirectView.as_view(url='mixes', permanent=False), name='index'),
]
