from django.db import models

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

    def save(self, *args, **kwargs):
        self.alcohol_percentage = _cut(self.alcohol_percentage, low=0, high=100)
        self.density = _cut(self.density, low=0)
        super(Ingredient, self).save(*args, **kwargs)


class Mix(models.Model):
    updated_at = models.DateTimeField(auto_now=True)
    name = models.CharField(unique=True, max_length=50)
    ingredients = models.ManyToManyField(
        Ingredient,
        through='Dose',
        related_name='in_mixes',
    )
    likes = models.PositiveSmallIntegerField(default=0)
    mixed = models.PositiveSmallIntegerField(default=0)

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
        return sum(map(lambda q, p: q * p, q_and_p))/sum(map(lambda q, p: q, q_and_p))

    @property
    def volume(self):
        return sum(self.doses.values_list('quantity', flat=True))

    @property
    def weight(self):
        q_and_d = self.doses.values_list('quantity', 'ingredient__density')
        return sum(map(lambda q, d: q * settings.UNIT_CONVERSION_VOLUME_SI * d, q_and_d))

    def is_available(self):
        return all(self.ingredients.dispenser_set.filter(is_empty=False))


class Dose(models.Model):
    mix = models.ForeignKey(Mix, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField(
        help_text='In milliliter [%s]' % settings.UNIT_VOLUME
    )
    number = models.PositiveSmallIntegerField(
        help_text='The number in which order the dose must be served'
    )

    def save(self, *args, **kwargs):
        self.quantity = _cut(self.quantity, low=0)
        super(Dose, self).save(*args, **kwargs)

    def is_available(self):
        return self.ingredient.dispenser_set.filter(is_empty=False).exists()


class Dispenser(models.Model):
    updated_at = models.DateTimeField(auto_now=True)
    number = models.PositiveSmallIntegerField(
        unique=True,
        choices=DISPENSER_CHOICES
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.SET_NULL,
        null=True
    )
    is_empty = models.BooleanField()
