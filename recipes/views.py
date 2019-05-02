from collections import OrderedDict

from django.views import View
from django.views.generic.base import TemplateView
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError, JsonResponse

from recipes.models import Mix, Order


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
        ('Gin', {'ingredients__name': 'Gin'}),
        ('Vodka', {'ingredients__name': 'Vodka'}),
    ))),
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
        mixes = Mix.objects.filter(verified=True)  # TODO filter for availables

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

        context['sorts'] = sorts
        context['sort_by'] = sort_by
        context['subsorts'] = subsorts
        context['subsort_by'] = subsort_by
        context['mixes'] = mixes_sorted

        return context


class OrderView(View):
    def post(self, request, *args, **kwargs):
        try:
            mix_id = request.POST['mix_id']
            mix = Mix.objects.get(id=int(mix_id))
            order = Order(mix=mix)
            order.save()
            if order.accepted:
                mix.count += 1
                mix.save()
            return HttpResponse(status=204)
        except (ValueError, KeyError):
            return HttpResponseBadRequest()
        except Mix.DoesNotExist:
            return HttpResponseServerError()

    def get(self, request, *args, **kwargs):
        try:
            last_order = Order.objects.latest('created_at')
            return JsonResponse(
                {
                    'accepted': last_order.accepted,
                    'status': last_order.status,
                    'mix_name': last_order.mix.name,
                }
            )
        except Order.DoesNotExist:
            return HttpResponseServerError()


class MixView(View):
    def post(self, request, *args, **kwargs):
        try:
            mix_id = int(request.POST['mix_id'])
            like_value = 1 if 'true' in request.POST['like'] else -1
            mix = Mix.objects.get(id=mix_id)
            mix.likes += like_value
            mix.save()
            print(like_value, 'like for', mix)
            return HttpResponse(status=204)
        except (ValueError, KeyError) as e:
            print(e)
            return HttpResponseBadRequest()
        except Mix.DoesNotExist:
            return HttpResponseServerError()

