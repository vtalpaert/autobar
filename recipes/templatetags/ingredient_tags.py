from django.template.defaulttags import register


@register.inclusion_tag('recipes/ingredient_tags.html')
def ingredient_tags(mix):
    return {'ingredients': mix.ingredients.all()}
