import os
import demjson
import certifi
import re
from pprint import pprint
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand

from recipes.models import *
from .scrap import URL, PoolManagerCounter, open_page


def get_mix_json_by_name(name):
    return URL + 'api/json/v1/1/search.php?s=' + str(name).replace(' ', '%20')


def get_description_by_id(drink_id):
    return URL + 'drink.php?c=' + str(drink_id)


def make_place_for_dose(number, mix):
    insert = False
    for dose in mix.ordered_doses():
        if dose.number < number:
            pass
        elif dose.number == number:
            insert = True
            dose.number = dose.number + 1
            dose.save()
        elif dose.number > number and insert:
            dose.number = dose.number + 1
            dose.save()


def drink_dialog(mix, hints):
    hints = hints[2:-2]
    hints = hints.replace('\\\\n', '')
    hints = hints.replace('\\\\t', '')
    hints = hints.replace('Serve:', '\n\nServe:')
    print('')
    print('')
    print('Verifying %s' % mix.name)
    print('I found online :')
    print(hints)
    print('')
    if not mix.image:
        print('Does not have an image')
    print('Dosage is:')
    for dose in mix.ordered_doses():
        print('   %s. %s' % (dose.number, dose), ' (%.1f oz)' % (dose.quantity * 0.3519503))

    while True:
        choice = input('Would you like to mark as verified, delete, pass or change something? (v/d/p/c) ')
        if choice == 'v':
            mix.verified = True
            mix.save()
            return
        elif choice == 'p':
            return
        elif choice == 'd':
            mix.delete()
            return
        elif choice == 'c':
            choice = input('Do you want to change dosage or add ingredient or delete one? (d/i/delete) ')
            if choice == 'd':
                number = int(input('What dosage number should be updated ? '))
                quantity = float(input('What quantity do you want ? '))
                dose = Dose.objects.get(mix=mix, number=number)
                dose.quantity = quantity
                dose.save()
            elif choice == 'delete':
                number = int(input('What dosage number do you want to delete ? '))
                dose = Dose.objects.get(mix=mix, number=number)
                dose.delete()
            elif choice == 'i':
                number = int(input('What dosage number should this ingredient have ? '))
                quantity = float(input('What quantity do you want ? '))
                ingredient = None
                while ingredient is None:
                    ingredient_name = input('Ingredient name ? ')
                    try:
                        ingredient = Ingredient.objects.get(name=ingredient_name)
                    except Ingredient.DoesNotExist:
                        print('Try again')
                make_place_for_dose(number, mix)
                Dose.objects.create(
                    ingredient=ingredient,
                    mix=mix,
                    number=number,
                    quantity=quantity
                )
            return drink_dialog(mix, hints)


class Command(BaseCommand):
    help = 'Verify DB integrity'

    def handle(self, *args, **options):
        pool_manager = PoolManagerCounter(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        for mix in Mix.objects.filter(verified=False).filter(ingredients__name='Gin'):
            json_url = get_mix_json_by_name(mix.name)
            json_text = open_page(json_url, pool_manager)
            drinks = demjson.decode(json_text, encoding="ascii")
            drink = drinks['drinks'][0]
            drink_id = drink['idDrink']
            description_url = get_description_by_id(drink_id)
            drink_html = open_page(description_url, pool_manager)
            lead = re.findall(r'<p class="lead">.*</p>', str(drink_html))
            soup = BeautifulSoup(str(lead), features='html.parser', from_encoding='utf-8')
            hints = soup.get_text()
            drink_dialog(mix, hints)
