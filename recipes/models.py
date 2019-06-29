import os
from math import ceil

from django.db import models
import solo.models
from django.utils.text import get_valid_filename

from django.conf import settings
DISPENSER_CHOICES = [(i, i) for i in range(settings.PUMPS_NB)]


def _cut(value, low=None, high=None):
    if low:
        value = max(low, value)
    if high:
        value = min(high, value)
    return value


class Ingredient(models.Model):
    name = models.CharField(unique=True, max_length=50)
    alcohol_percentage = models.FloatField(
        help_text='Should be between 0 and 100'
    )
    density = models.FloatField(
        help_text='In grams per liter [%s]' % settings.UNIT_DENSITY,
        default=settings.UNIT_DENSITY_DEFAULT
    )
    added_separately = models.BooleanField(
        default=False,
    )

    def save(self, *args, **kwargs):
        self.alcohol_percentage = _cut(self.alcohol_percentage, low=0, high=100)
        self.density = _cut(self.density, low=0)
        super(Ingredient, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    def dispensers(self, filter_out_empty):
        dispensers = self.dispenser_set.all()
        if filter_out_empty:
            dispensers = dispensers.filter(is_empty=False)
        return dispensers

    def is_available(self):
        return self.added_separately or self.dispensers(filter_out_empty=settings.EMPTY_DISPENSER_MAKES_MIX_NOT_AVAILABLE).exists()

    @staticmethod
    def available_ingredients(ingredients_in_dispensers=None, include_added_separately=False):
        if ingredients_in_dispensers is None:
            ingredients_in_dispensers = Dispenser.ingredients_in_dispensers(filter_out_empty=settings.EMPTY_DISPENSER_MAKES_MIX_NOT_AVAILABLE)
        ingredients = Ingredient.objects.filter(pk__in=ingredients_in_dispensers)
        if include_added_separately:
            return ingredients.union(Ingredient.objects.filter(added_separately=True))
        else:
            return ingredients

    @staticmethod
    def alcohols():
        return Ingredient.objects.exclude(alcohol_percentage=0)

    @staticmethod
    def available_alcohols(ingredients_in_dispensers=None):
        if ingredients_in_dispensers is None:
            ingredients_in_dispensers = Dispenser.ingredients_in_dispensers(filter_out_empty=settings.EMPTY_DISPENSER_MAKES_MIX_NOT_AVAILABLE)
        return Ingredient.alcohols().filter(id__in=ingredients_in_dispensers)


def mix_upload_to(instance, filename):
    new_filename = get_valid_filename(instance.name)
    if len(filename.split('.')) > 1:  # keep extension
        new_filename += '.' + filename.split('.')[-1]
    return os.path.join(settings.UPLOAD_FOR_MIX, new_filename)


class Mix(models.Model):

    class Meta:
        verbose_name_plural = 'Mixes'

    updated_at = models.DateTimeField(auto_now=True)
    name = models.CharField(unique=True, max_length=50)
    ingredients = models.ManyToManyField(
        Ingredient,
        through='Dose',
        related_name='in_mixes',
    )
    likes = models.PositiveSmallIntegerField(default=0)
    count = models.PositiveSmallIntegerField(default=0)
    image = models.ImageField(
        max_length=200,
        height_field='image_height',
        width_field='image_width',
        upload_to=mix_upload_to,
        null=True,
        blank=True,
    )
    image_height = models.PositiveIntegerField(null=True)
    image_width = models.PositiveIntegerField(null=True)
    description = models.TextField(
        blank=True,
    )
    verified = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        for dose in self.doses:
            dose.set_quantity_to_zero_if_not_required()
        super(Mix, self).save(*args, **kwargs)

    @property
    def doses(self):
        return Dose.objects.filter(mix=self)

    def ordered_doses(self):
        return self.doses.order_by('number')

    def real_ingredients(self):
        return self.ingredients.filter(added_separately=False)

    @property
    def alcohol_percentage(self):
        q_and_p = self.doses.values_list('quantity', 'ingredient__alcohol_percentage')
        if len(q_and_p) == 0:
            return 0
        try:
            percentage = sum(map(lambda qp: qp[0] * qp[1], q_and_p))/sum(map(lambda qp: qp[0], q_and_p))
            return ceil(10 * percentage) / 10
        except ZeroDivisionError:
            return 0

    @property
    def volume(self):
        return sum(self.doses.values_list('quantity', flat=True))

    @property
    def weight(self):
        q_and_d = self.doses.values_list('quantity', 'ingredient__density')
        return sum(map(lambda qd: qd[0] * settings.UNIT_CONVERSION_VOLUME_SI * qd[1], q_and_d))

    def is_available(self):
        return all(ingredient.is_available() for ingredient in self.ingredients.all())

    def calibrate_volume_to(self, desired_total):
        """Look out you respect the correct units"""
        volume = self.volume
        for dose in self.doses:
            dose.quantity = dose.quantity * desired_total / volume
            dose.save()

    @staticmethod
    def filter_by_available(mixes=None):
        available_ingredients_in_dispenser = Ingredient.available_ingredients(include_added_separately=False)
        mixes = mixes if mixes is not None else Mix.objects.all()
        mixes_with_at_least_one_ingredient = mixes.filter(
            ingredients__in=available_ingredients_in_dispenser
        ).distinct()
        return filter(
            lambda mix: all(
                ingredient in available_ingredients_in_dispenser
                for ingredient in mix.real_ingredients()
            ),
            mixes_with_at_least_one_ingredient
        )

    @staticmethod
    def naive_available(mixes=None):
        mixes = mixes if mixes is not None else Mix.objects.all()
        available = []
        for mix in mixes:
            if mix.is_available():
                available.append(mix)
        return available


class Dose(models.Model):
    mix = models.ForeignKey(Mix, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField(
        help_text='In %s [%s]' % (settings.UNIT_VOLUME_VERBOSE, settings.UNIT_VOLUME)
    )
    number = models.PositiveSmallIntegerField(
        help_text='The number in which order the dose must be served'
    )

    @property
    def weight(self):
        return self.ingredient.density * (self.quantity * settings.UNIT_CONVERSION_VOLUME_SI)

    def __str__(self):
        if self.ingredient.added_separately:
            return str(self.ingredient)
        else:
            return '{} {} of {}'.format(self.quantity, settings.UNIT_VOLUME, self.ingredient)

    def save(self, *args, **kwargs):
        self.quantity = _cut(self.quantity, low=0)
        super(Dose, self).save(*args, **kwargs)

    def is_available(self):
        return self.ingredient.is_available()  # if self.required else True

    def set_quantity_to_zero_if_not_required(self):
        if self.ingredient.added_separately:
            self.quantity = 0
            self.save()

    @property
    def required(self):
        return not self.ingredient.added_separately


class Dispenser(models.Model):
    updated_at = models.DateTimeField(auto_now=True)
    number = models.PositiveSmallIntegerField(
        unique=True,
        choices=DISPENSER_CHOICES
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'added_separately': False},
    )
    is_empty = models.BooleanField()

    def __str__(self):
        return 'Dispenser {} with {}'.format(self.number, self.ingredient)

    def save(self, *args, **kwargs):
        if not self.ingredient:
            self.is_empty = True
        super(Dispenser, self).save(*args, **kwargs)

    @staticmethod
    def ingredients_in_dispensers(filter_out_empty):
        dispensers = Dispenser.objects.all()
        if filter_out_empty:
            dispensers = dispensers.filter(is_empty=False)
        return dispensers.values_list('ingredient', flat=True)


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    mix = models.ForeignKey(
        Mix,
        on_delete=models.SET_NULL,  # keep command in history even in mix is deleted
        null=True,
        blank=True,
    )
    status = models.PositiveSmallIntegerField(choices=settings.SERVING_STATES_CHOICES, default=0)
    accepted = models.BooleanField(default=False)

    def __str__(self):
        if self.mix:
            return 'Order of one {}'.format(self.mix)
        else:
            return 'Empty order'

    def status_verbose(self):
        return settings.SERVING_STATES_CHOICES[self.status][1]


class Configuration(solo.models.SingletonModel):
    updated_at = models.DateTimeField(auto_now=True)
    show_only_available_mixes = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Configuration"

    def __str__(self):
        return 'Configuration'
