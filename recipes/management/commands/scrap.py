import os
import demjson
import urllib3
import certifi
from Levenshtein import distance
import re
from pprint import pprint

from django.core.management.base import BaseCommand

from recipes.models import Ingredient
import recipes


URL = 'https://www.thecocktaildb.com/'

GLASS_BASE = 30

CONVERSIONS = {  # to cL approximately
    'oz': 3,
    'tsp': 0.6,
    'shot': 3,
    'part': 3,  # TODO
    'parts': 3,  # TODO
    'shots': 3,
    'twist of': 1,
    'tblsp': 1.5,
    'gr': 0.1,
    'ml': 0.1,
    'cl': 1,
    'dash': 1.5,  # TODO
    'dashes': 1.5,  # TODO
    'twist': 1.5,
    'fifth': GLASS_BASE/5,
    'cup': 30,
    'cups': 30,
    'drop': 0.6,
    'drops': 0.6,
}

REPLACING = (
    ('1/2', '0.5'),
    ('3/4', '0.75'),
    ('1/8', '0.125'),
    ('1/4', '0.25'),
    ('2/3', '0.66'),
    ('1/3', '0.33'),
    ('3-4', '3.5'),
    ('1-3', '2'),
)


class PoolManagerCounter(urllib3.PoolManager):
    def __init__(self, num_pools=10, headers=None, **connection_pool_kw):
        self.counter = 0
        urllib3.PoolManager.__init__(self, num_pools=num_pools, headers=headers, **connection_pool_kw)

    def urlopen(self, method, url, redirect=True, **kw):
        self.counter += 1
        return urllib3.PoolManager.urlopen(self, method, url, redirect=redirect, **kw)
# PoolManagerCounter(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())


def open_page(url, pool_manager):
    r = pool_manager.request('GET', url)
    return r.data


def get_browse_url_by_letter(letter):
    return URL + 'browse.php?b=' + str(letter)


def get_lookup_url_by_id(drink_id):
    return URL + 'api/json/v1/1/lookup.php?i=' + str(drink_id)


def make_json_keys_list():
    ingredient, measure = 'strIngredient', 'strMeasure'
    l = []
    for i in range(1, 16):
        l.append(
            (
                ingredient + str(i),
                measure + str(i)
            )
        )
    return l


INGREDIENT_KEYS = make_json_keys_list()


def get_closest_ingredient(name):
    ingredients = Ingredient.objects.values_list('name', flat=True)
    distances = [distance(name, known_name) for known_name in ingredients]
    min_index, min_value = min(enumerate(distances), key=lambda p: p[1])
    return Ingredient.objects.get(name=ingredients[min_index])


def get_clean_measure(measure, ingredient=None):
    measure = measure.lower()
    for match, replacement in REPLACING:
        measure = measure.replace(match, replacement)
    for unit in CONVERSIONS:
        if unit in measure:
            try:
                value = float(measure.split()[0]) * CONVERSIONS[unit]
                #print('recognized %s [cL]' % value)
                return value
            except ValueError:
                if measure.split()[0] in CONVERSIONS:
                    value = CONVERSIONS[measure.split()[0]]
                    return value
                print('PASSED', measure, ingredient)
    print('TODO', measure, ingredient)
    return measure


class Command(BaseCommand):
    help = 'Scraps all cocktails from thecocktaildb.com'

    def handle(self, *args, **options):
        pool_manager = PoolManagerCounter(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        for letter in 'a':
            url = get_browse_url_by_letter(letter)
            html_letter = open_page(url, pool_manager)
            ids = re.findall(r'drink.php\?c=\d+', str(html_letter))
            ids = map(lambda s: s[len("drink.php?c="):], ids)
            ids = list(map(int, ids))
            for drink_id in ids:
                json_url = get_lookup_url_by_id(drink_id)
                json_text = open_page(json_url, pool_manager)
                drinks = demjson.decode(json_text, encoding="ascii")
                drink = drinks['drinks'][0]
                name = drink['strDrink']
                image_url = drink['strDrinkThumb']
                description = drink['strInstructions']
                for ingredient_key, measure_key in INGREDIENT_KEYS:
                    ingredient_name = drink[ingredient_key]
                    measure = drink[measure_key]
                    ingredient_name = ingredient_name.strip() if ingredient_name is not None else ingredient_name
                    measure = measure.strip() if measure is not None else measure
                    if ingredient_name and measure:
                        try:
                            ingredient = Ingredient.objects.get(name=ingredient_name)
                        except Ingredient.DoesNotExist:
                            ingredient = get_closest_ingredient(ingredient_name)
                            #input('%s does not exist, would you like to create a new or use %s? (n/u) '
                            #      % (ingredient_name, ingredient.name))
                        measure_clean = get_clean_measure(measure, ingredient_name)
