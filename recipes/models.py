import os

from django.db import models
from django.db.models import Q
from django.utils.text import get_valid_filename

from autobar import settings
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

    def is_available(self):
        return self.dispenser_set.filter(is_empty=False).exists()


def mix_upload_to(instance, filename):
    new_filename = get_valid_filename(instance.name)
    if len(filename.split('.')) > 1:  # keep extension
        new_filename += filename.split('.')[-1]
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
        height_field='height',
        width_field='width',
        upload_to=mix_upload_to,
        null=True,
    )

    def __str__(self):
        return self.name

    @property
    def doses(self):
        return Dose.objects.filter(mix=self)

    def ordered_doses(self):
        return self.doses.order_by('number')

    def serve(self):
        for dose in self.doses:
            dose.serve()

    @property
    def alcohol_percentage(self):
        q_and_p = self.doses.values_list('quantity', 'ingredient__alcohol_percentage')
        if not q_and_p.exists():
            return 0
        return sum(map(lambda qp: qp[0] * qp[1], q_and_p))/sum(map(lambda qp: qp[0], q_and_p))

    @property
    def volume(self):
        return sum(self.doses.values_list('quantity', flat=True))

    @property
    def weight(self):
        q_and_d = self.doses.values_list('quantity', 'ingredient__density')
        return sum(map(lambda qd: qd[0] * settings.UNIT_CONVERSION_VOLUME_SI * qd[1], q_and_d))

    def is_available(self):
        return all(dose.is_available() for dose in self.doses)


class Dose(models.Model):
    mix = models.ForeignKey(Mix, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField(
        help_text='In %s [%s]' % (settings.UNIT_VOLUME_VERBOSE, settings.UNIT_VOLUME)
    )
    number = models.PositiveSmallIntegerField(
        help_text='The number in which order the dose must be served'
    )
    required = models.BooleanField(default=True)

    def __str__(self):
        return '{} {} of {}'.format(self.quantity, settings.UNIT_VOLUME, self.ingredient)

    def save(self, *args, **kwargs):
        self.quantity = _cut(self.quantity, low=0)
        super(Dose, self).save(*args, **kwargs)

    def is_available(self):
        return self.ingredient.is_available() if self.required else True


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
        limit_choices_to={'added_separately': False},
    )
    is_empty = models.BooleanField()
