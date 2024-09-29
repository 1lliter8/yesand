from django.db import models


class Dir(models.Model):
    dir = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )
    display = models.CharField(max_length=255)

    def __str__(self):
        return self.display

    def get_ancestors(self) -> list['Dir']:
        ancestors = []
        current_dir = self.dir
        while current_dir:
            ancestors.insert(0, current_dir)
            current_dir = current_dir.dir
        return ancestors


class AIModel(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Field(models.Model):
    template = models.TextField()

    def __str__(self):
        return f'Field {self.id}'


class Prompt(models.Model):
    display = models.CharField(max_length=255)
    text = models.TextField()
    dir = models.ForeignKey(Dir, on_delete=models.CASCADE, related_name='prompts')
    aimodels = models.ManyToManyField(AIModel, blank=True, related_name='prompts')
    fields = models.ManyToManyField(Field, blank=True, related_name='prompts')

    def __str__(self):
        return f'{self.display}: {self.text[:50]}...'
