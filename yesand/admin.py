from django.contrib import admin
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget

from .models import AIModel, Dir, Field, Prompt

admin.site.register(Dir)
admin.site.register(Field)
admin.site.register(Prompt)


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }
