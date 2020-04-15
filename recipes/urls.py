from django.urls import path, include
from django.views.generic.base import RedirectView

from recipes import views

urlpatterns = [
    path('mix-info/<int:pk>', views.MixModalView.as_view(), name='modal_mix'),
    path('order/create/<int:mix_id>', views.CreateOrderView.as_view(), name='create_order'),
    path('order/check/<int:order_id>', views.CheckOrderView.as_view(), name='check_order'),
    path('mix/like/<int:mix_id>', views.MixLikeView.as_view(), name='like'),
    path('mixes/<slug:sort_by>/<slug:subsort_by>/', views.Mixes.as_view(), name='mixes_ss'),
    path('mixes/<slug:sort_by>/', views.Mixes.as_view(), name='mixes_s'),
    path('mixes/', views.Mixes.as_view(), name='mixes'),
    path('', RedirectView.as_view(url='mixes', permanent=False), name='index'),
]
