from django.template.defaulttags import register

from recipes.models import Configuration


@register.inclusion_tag('recipes/ingredient_tags.html')
def ingredient_tags(mix):
    config = Configuration.get_solo()
    ingredients = mix.real_ingredients() if config.ux_show_only_real_ingredients else mix.ingredients.all()
    return {'ingredients': ingredients}
