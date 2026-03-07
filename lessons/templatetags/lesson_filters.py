from django import template

register = template.Library()


@register.filter(name='first_word')
def first_word(value):
    """Return only the first meaning (text before the first comma)."""
    if not value:
        return value
    return value.split(',')[0].strip()
