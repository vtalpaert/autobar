from django.urls import path, include
from django.views.generic.base import RedirectView

from recipes import views

urlpatterns = [
    path('mix-info/<int:pk>', views.MixModalView.as_view(), name='modal_mix'),
    path('mix/like/<int:mix_id>', views.MixLikeView.as_view(), name='like'),
    path('order/<int:mix_id>', views.OrderView.as_view(), name='post_order'),
    path('mixes/<slug:sort_by>/<slug:subsort_by>/', views.Mixes.as_view(), name='mixes_ss'),
    path('mixes/<slug:sort_by>/', views.Mixes.as_view(), name='mixes_s'),
    path('mixes/', views.Mixes.as_view(), name='mixes'),
    path('', RedirectView.as_view(url='mixes', permanent=False), name='index'),
]
