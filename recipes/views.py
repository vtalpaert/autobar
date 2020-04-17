from collections import OrderedDict

from django.views import View
from django.views.generic.base import TemplateView
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError, JsonResponse
from django.utils.log import logging
from django.shortcuts import get_object_or_404
from django.http import Http404

from bootstrap_modal_forms.generic import BSModalReadView

from .models import Mix, Order, Configuration


logger = logging.getLogger('autobar')


letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

order_by = OrderedDict((
    ('A-Z', OrderedDict((
        ('A-Z', 'name'),
        ('Z-A', '-name'),
    ))),
    ('Popularity', OrderedDict((
        ('Likes', '-likes'),
        ('Count', '-count'),
    ))),
    ('Recent', OrderedDict((
        ('Updated', '-updated_at'),
    ))),
))
filters = OrderedDict((  # TODO auto filters from available alcohol ?
    ('Alcohol', OrderedDict((
        ('Gin', {'ingredients__name__in': ['Gin', 'Sloe gin']}),
        ('Vodka', {'ingredients__name': 'Vodka'}),
        ('Tequila', {'ingredients__name': 'Tequila'}),
        ('Rum', {'ingredients__name__in': ['Light rum', 'Dark rum']}),
        ('Whiskey', {'ingredients__name': 'Whiskey'}),
    ))),
    ('Name', OrderedDict([(letter, {'name__startswith': letter}) for letter in letters])),
))


def get_or_none(dic, key):
    try:
        return dic[key]
    except KeyError:
        return None


class Mixes(TemplateView):

    template_name = 'recipes/mixes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = Configuration.get_solo()
        if config.ux_show_only_verified_mixes:
            mixes = Mix.objects.filter(verified=True)
        else:
            mixes = Mix.objects.all()

        sort_by = get_or_none(kwargs, 'sort_by')
        sorts = list(order_by.keys()) + list(filters.keys())
        if sort_by not in sorts:
            sort_by = sorts[0]
        subsort_by = get_or_none(kwargs, 'subsort_by')
        if sort_by in order_by:
            subsorts = list(order_by[sort_by].keys())
            if subsort_by not in subsorts:
                subsort_by = subsorts[0]
            mixes_sorted = mixes.order_by(order_by[sort_by][subsort_by])
        elif sort_by in filters:
            subsorts = list(filters[sort_by].keys())
            if subsort_by not in subsorts:
                subsort_by = subsorts[0]
            mixes_sorted = mixes.filter(**filters[sort_by][subsort_by])

        if config.ux_show_only_available_mixes:
            mixes_sorted = Mix.filter_by_available(mixes=mixes_sorted)

        context['sorts'] = sorts
        context['sort_by'] = sort_by
        context['subsorts'] = subsorts
        context['subsort_by'] = subsort_by
        context['mixes'] = mixes_sorted

        return context


class CreateOrderView(View):
    def post(self, request, mix_id, *args, **kwargs):
        mix = get_object_or_404(Mix, id=mix_id)
        order = Order(mix=mix)
        order.save()
        if order.accepted:
            mix.count += 1
            mix.save()
        return JsonResponse(
            {
                'order_id': order.pk,
                'accepted': order.accepted,
                'status': order.status,
                'mix_name': order.mix.name,
                'status_verbose': order.status_verbose(),
                'done': order.is_done() or not order.accepted,
            }
        )


class CheckOrderView(View):
    def get(self, request, order_id, *args, **kwargs):
        order = get_object_or_404(Order, id=order_id)
        return JsonResponse(
            {
                'accepted': order.accepted,
                'status': order.status,
                'mix_name': order.mix.name,
                'status_verbose': order.status_verbose(),
                'done': order.is_done() or not order.accepted,
            }
        )


class MixLikeView(View):
    def post(self, request, mix_id, *args, **kwargs):
        try:
            like_value = 1 if 'true' in request.POST['like'] else -1
            mix = Mix.objects.get(id=mix_id)
            mix.likes += like_value
            mix.save()
            logger.info('%i like for %s' % (like_value, mix))
            return HttpResponse(status=204)
        except (ValueError, KeyError) as e:
            print(e)
            return HttpResponseBadRequest()
        except Mix.DoesNotExist:
            return HttpResponseServerError()


class MixModalView(BSModalReadView):
    model = Mix
    template_name = 'recipes/modal_mix.html'
