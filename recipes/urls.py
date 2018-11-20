from django.urls import path, include

from recipes import views

urlpatterns = [
    path('mixes/<slug:sort_by>/', views.Mixes.as_view(), name='mixes_s'),
    path('mixes/', views.Mixes.as_view(), name='mixes'),
]
