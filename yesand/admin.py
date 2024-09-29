from django.contrib import admin

from .models import AIModel, Dir, Field, Prompt

admin.site.register(Dir)
admin.site.register(AIModel)
admin.site.register(Field)
admin.site.register(Prompt)
