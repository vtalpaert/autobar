from django.urls import path, include

from recipes import views

urlpatterns = [
    path('mixes/', views.Mixes.as_view(), name='mixes'),
]