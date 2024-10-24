import os
from typing import Union

from cryptography.fernet import Fernet
from django.core.validators import URLValidator
from django.db import models
from django.db.models import JSONField, QuerySet


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

    endpoint = models.URLField(
        validators=[URLValidator()],
        help_text='The URL endpoint for the AI',
        blank=True,
    )
    encrypted_api_key = models.BinaryField(null=True, blank=True)
    parameters = JSONField(
        # default=dict,
        blank=True,
        help_text='Arbitrary key-value pairs for model parameters',
    )

    class Meta:
        verbose_name = 'AI model'
        verbose_name_plural = 'AI models'

    def __str__(self):
        return f'{self.display}'

    # def save(self, *args, **kwargs):
    #     # if isinstance(self.parameters, str):
    #     #     try:
    #     #         self.parameters = json.loads(self.parameters)
    #     #     except json.JSONDecodeError as e:
    #     #         raise ValidationError('Invalid JSON in parameters field') from e

    #     # if not self.parameters:
    #     #     self.parameters = {'temperature': 0.0}

    #     super().save(*args, **kwargs)

    @property
    def key(self) -> str:
        if self.encrypted_api_key:
            cipher_suite = Fernet(os.environ['ENCRYPTION_KEY'])
            return cipher_suite.decrypt(self.encrypted_api_key).decode()
        return ''

    @key.setter
    def key(self, value: str) -> None:
        if value:
            cipher_suite = Fernet(os.environ['ENCRYPTION_KEY'])
            self.encrypted_api_key = cipher_suite.encrypt(value.encode())
        else:
            self.encrypted_api_key = None


class Field(models.Model):
    """A field in the prompt template."""

    template = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f'Field {self.template}'


class Prompt(ItemMixin):
    """A prompt for a text generation model."""

    text = models.TextField(blank=True)
    aimodels = models.ManyToManyField(AIModel, blank=True, related_name='prompts')
    fields = models.ManyToManyField(Field, blank=True, related_name='prompts')

    class Meta:
        verbose_name = 'prompt'
        verbose_name_plural = 'prompts'

    def __str__(self) -> str:
        return f'{self.display}: {self.text[:50]}...'

    def save(self, *args, **kwargs) -> None:
        """Saves the model and updates the AI models."""
        super().save(*args, **kwargs)
        self._update_aimodels()

    def get_ancestor_aimodels(self) -> QuerySet[AIModel]:
        """Returns all AIModels in the ancestor directories."""
        return self.get_ancestor_aimodels_for_dir(self.dir_id)

    @staticmethod
    def get_ancestor_aimodels_for_dir(dir_id: int | None) -> QuerySet[AIModel]:
        """Returns all AIModels in the requested directory's ancestors.

        If dir_id is None, it returns all AIModels that don't have a directory.
        """
        if dir_id is None:
            return AIModel.objects.filter(dir__isnull=True)

        dir_instance = Dir.objects.get(id=dir_id)
        ancestors = dir_instance.get_ancestors()
        ancestors.append(dir_instance)

        return AIModel.objects.filter(dir__in=ancestors)

    def _update_aimodels(self) -> None:
        """Update AIModels so only those in the ancestor directories are included."""
        valid_aimodel_ids = set(
            self.get_ancestor_aimodels().values_list('id', flat=True)
        )
        aimodels_to_remove = self.aimodels.exclude(id__in=valid_aimodel_ids)

        self.aimodels.remove(*aimodels_to_remove)
