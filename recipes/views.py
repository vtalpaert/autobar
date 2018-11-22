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

        print(order_by)
        sort_by = get_or_none(kwargs, 'sort_by')
        sorts = list(order_by.keys())
        if sort_by not in sorts:
            sort_by = sorts[0]
        subsort_by = get_or_none(kwargs, 'subsort_by')
        subsorts = list(order_by[sort_by].keys())
        if subsort_by not in subsorts:
            subsort_by = subsorts[0]

        context['sorts'] = sorts
        context['sort_by'] = sort_by
        context['subsorts'] = subsorts
        context['subsort_by'] = subsort_by

        return context
