from django.contrib import admin

from .models import AIModel, Field, Folder, Prompt

admin.site.register(Folder)
admin.site.register(AIModel)
admin.site.register(Field)
admin.site.register(Prompt)
