from django.contrib import admin
from solo.admin import SingletonModelAdmin

from recipes.models import *
from django.conf import settings


def mark_as_separate(modeladmin, request, queryset):
    queryset.update(added_separately=True)
    mark_as_separate.short_description = "Mark as separate ingredient"


def reset_density_to_default(modeladmin, request, queryset):
    queryset.update(density=settings.UNIT_DENSITY_DEFAULT)


def combine_as_one(modeladmin, request, queryset):
    ingredients = list(queryset.all())
    main = ingredients[0]
    for ingredient in ingredients[1:]:
        doses = Dose.objects.filter(ingredient=ingredient)
        for dose in doses:
            dose.ingredient = main
            dose.save()
        ingredient.delete()


def delete_with_extreme_prejudice(modeladmin, request, queryset):
    mixes = Mix.objects.filter(ingredients__in=queryset.all()).delete()
    queryset.delete()


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
    actions = (
        mark_as_separate,
        reset_density_to_default,
        combine_as_one,
        delete_with_extreme_prejudice
    )


@admin.register(Dose)
class DoseAdmin(admin.ModelAdmin):
    list_display = (
        'mix',
        'ingredient',
        'quantity',
        'number',
        'required',
    )
    search_fields = ('mix__name',)
    ordering = ('mix', 'number')


class DoseInline(admin.TabularInline):
    model = Mix.ingredients.through


def set_volume_to_30cL(modeladmin, request, queryset):
    for mix in queryset:
        mix.calibrate_volume_to(30)


def set_volume_to_20cL(modeladmin, request, queryset):
    for mix in queryset:
        mix.calibrate_volume_to(20)


@admin.register(Mix)
class MixAdmin(admin.ModelAdmin):
    inlines = (
        DoseInline,
    )
    list_display = (
        'name',
        'verified',
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
        'verified',
        'updated_at',
        'ingredients',
    )
    search_fields = ('name',)
    actions = (
        set_volume_to_20cL,
        set_volume_to_30cL
    )

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
    ordering = ('number',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'updated_at',
        'status',
        'accepted',
        'mix',
    )
    list_filter = (
        'accepted',
        'status',
        'updated_at',
        'created_at',
    )


@admin.register(Configuration)
class ConfigurationAdmin(SingletonModelAdmin):
    pass
