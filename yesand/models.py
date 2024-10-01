from typing import Union

from django.db import models


class Dir(models.Model):
    dir = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )
    display = models.CharField(max_length=255)

    def __str__(self):
        return self.display

    def get_ancestors(self) -> list['Dir']:
        """Return a list of all ancestors of this Dir."""
        ancestors = []
        current_dir = self.dir
        while current_dir:
            ancestors.insert(0, current_dir)
            current_dir = current_dir.dir
        return ancestors

    def get_descendants(
        self, include_self: bool = False
    ) -> list[Union['Dir', 'AIModel', 'Prompt']]:
        """Return a list of all descendants of this Dir."""
        if include_self:
            descendants = [self]
        else:
            descendants = []

        children = Dir.objects.filter(dir=self)

        for child in children:
            descendants.extend(child.get_descendants(include_self=True))

        return descendants


class AIModel(models.Model):
    display = models.CharField(max_length=255)
    dir = models.ForeignKey(Dir, on_delete=models.CASCADE, related_name='aimodels')

    def __str__(self):
        return self.display


class Field(models.Model):
    template = models.CharField(max_length=255)

    def __str__(self):
        return f'Field {self.template}'


class Prompt(models.Model):
    display = models.CharField(max_length=255)
    text = models.TextField()
    dir = models.ForeignKey(Dir, on_delete=models.CASCADE, related_name='prompts')
    aimodels = models.ManyToManyField(AIModel, blank=True, related_name='prompts')
    fields = models.ManyToManyField(Field, blank=True, related_name='prompts')

    def __str__(self):
        return f'{self.display}: {self.text[:50]}...'
