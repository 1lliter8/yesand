from django.db import models


class Folder(models.Model):
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )
    display = models.CharField(max_length=255)

    def __str__(self):
        return self.display


class AIModel(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Field(models.Model):
    template = models.TextField()

    def __str__(self):
        return f'Field {self.id}'


class Prompt(models.Model):
    text = models.TextField()
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='prompts')
    aimodels = models.ManyToManyField(AIModel, blank=True, related_name='prompts')
    fields = models.ManyToManyField(Field, blank=True, related_name='prompts')

    def __str__(self):
        return f'Prompt {self.id}: {self.text[:50]}...'
