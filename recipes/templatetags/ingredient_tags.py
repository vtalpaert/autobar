from django.template.defaulttags import register
from django.conf import settings


@register.inclusion_tag('recipes/ingredient_tags.html')
def ingredient_tags(mix):
    ingredients = mix.real_ingredients() if settings.UI_SHOW_ONLY_REAL_INGREDIENTS else mix.ingredients.all()
    return {'ingredients': ingredients}
