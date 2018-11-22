from collections import OrderedDict

from django.views.generic.base import TemplateView

from recipes.models import Mix


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
