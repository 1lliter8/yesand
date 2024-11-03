from django.contrib import admin
from django.db.models import JSONField
from django_json_widget.widgets import JSONEditorWidget
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from .models import AIModel, DirNode, Field, Prompt


class DirNodeAdmin(TreeAdmin):
    form = movenodeform_factory(DirNode)


admin.site.register(DirNode, DirNodeAdmin)
admin.site.register(Field)
admin.site.register(Prompt)


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget},
    }
