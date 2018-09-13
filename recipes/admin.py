from django.contrib import admin

from recipes.models import *
from autobar import settings


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'alcohol_percentage',
        'density',
        'added_separately',
    )
    list_filter = (
        'added_separately',
    )
    search_fields = ('name',)


@admin.register(Dose)
class DoseAdmin(admin.ModelAdmin):
    list_display = (
        'mix',
        'ingredient',
        'quantity',
        'number',
        'required',
    )


class DoseInline(admin.TabularInline):
    model = Mix.ingredients.through


@admin.register(Mix)
class MixAdmin(admin.ModelAdmin):
    inlines = (
        DoseInline,
    )
    list_display = (
        'name',
        'is_available',
        'likes',
        'count',
        'updated_at',
        'alcohol_percentage',
        'volume',
        #'weight',
        'ordered_doses',
        'image',
    )
    list_filter = (
        'updated_at',
    )
    search_fields = ('name',)

    def volume(self, obj):
        return obj.volume
    volume.short_description = 'Volume [%s]' % settings.UNIT_VOLUME

    def weight(self, obj):
        return obj.weight
    weight.short_description = 'Weight [%s]' % settings.UNIT_MASS


@admin.register(Dispenser)
class DispenserAdmin(admin.ModelAdmin):
    list_display = (
        'number',
        'ingredient',
        'is_empty',
        'updated_at',
    )
