from django.shortcuts import render
from django.views.generic.base import TemplateView


class Mixes(TemplateView):

    template_name = 'recipes/mixes.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
