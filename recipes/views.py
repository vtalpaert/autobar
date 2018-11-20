from django.views.generic.base import TemplateView


def get_or_none(dic, key):
    try:
        return dic[key]
    except KeyError:
        return None


class Mixes(TemplateView):

    template_name = 'recipes/mixes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sort_by = get_or_none(kwargs, 'sort_by')
        sorts = ['A-Z', 'Popularity']
        if sort_by not in sorts:
            sort_by = sorts[0]

        context['sorts'] = sorts
        context['sort_by'] = sort_by

        return context
