from django import template

register = template.Library()

@register.filter(name="add_class")
def add_class(field, css):
    # сохраняем уже заданные классы виджета
    base = field.field.widget.attrs.get("class", "")
    new_class = (base + " " + css).strip()
    return field.as_widget(attrs={**field.field.widget.attrs, "class": new_class})
