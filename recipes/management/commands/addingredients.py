import os
import json

from django.core.management.base import BaseCommand

from recipes.models import *


class Command(BaseCommand):
    help = 'Read a JSON with ingredients'

    def add_arguments(self, parser):
        parser.add_argument('filepath', help='path to your json')

    def handle(self, *args, **options):
        filepath = options['filepath']
        with open(filepath, 'r') as myfile:
            content = json.load(myfile)
        ingredients = [drink['strIngredient1'] for drink in content['drinks']]
        for ingredient_name in ingredients:
            try:
                found = Ingredient.objects.get(name=ingredient_name)
            except Ingredient.DoesNotExist:
                Ingredient.objects.create(name=ingredient_name, alcohol_percentage=0)
                print('Added %s to DB' % ingredient_name)
