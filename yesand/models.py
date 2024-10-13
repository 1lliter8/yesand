from typing import Union

from django.db import models


class ItemMixin(models.Model):
    """A mixin for items that can be used with ItemView."""

    display = models.CharField(max_length=255)
    dir = models.ForeignKey(
        'Dir',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(class)ss',
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.display


class Dir(ItemMixin):
    """A directory in the file tree structure."""

    dir = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )

    class Meta:
        verbose_name = 'directory'
        verbose_name_plural = 'directories'

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

        descendants.extend(AIModel.objects.filter(dir=self))
        descendants.extend(Prompt.objects.filter(dir=self))

        children = Dir.objects.filter(dir=self)

        for child in children:
            descendants.extend(child.get_descendants(include_self=True))

        return descendants


class AIModel(ItemMixin):
    """A model that can be used to generate text."""

    class Meta:
        verbose_name = 'AI model'
        verbose_name_plural = 'AI models'


class Field(models.Model):
    """A field in the prompt template."""

    template = models.CharField(max_length=255)

    def __str__(self):
        return f'Field {self.template}'


class Prompt(ItemMixin):
    """A prompt for a text generation model."""

    text = models.TextField(blank=True)
    aimodels = models.ManyToManyField(AIModel, blank=True, related_name='prompts')
    fields = models.ManyToManyField(Field, blank=True, related_name='prompts')

    class Meta:
        verbose_name = 'prompt'
        verbose_name_plural = 'prompts'

    def __str__(self):
        return f'{self.display}: {self.text[:50]}...'
