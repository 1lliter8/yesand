from django import template

register = template.Library()


@register.filter
def get_class_name(value: object) -> str:
    """Return the class name of the given value."""
    return value.__class__.__name__


@register.filter
def model_verbose_name(form):
    """Return the verbose name of the model from a form."""
    return form._meta.model._meta.verbose_name


@register.filter
def model_name(form):
    """Return the model name from a form."""
    return form._meta.model._meta.model_name
