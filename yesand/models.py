import os
from typing import List, Union

from cryptography.fernet import Fernet
from django.core.validators import URLValidator
from django.db import models
from django.db.models import JSONField, QuerySet
from treebeard.mp_tree import MP_Node


class ItemMixin(models.Model):
    """A mixin for items that can be used with ItemView."""

    display = models.CharField(max_length=255)
    type_order = models.IntegerField(editable=False)

    class Meta:
        abstract = True
        ordering = ['type_order', 'display']

    def __str__(self):
        return self.display

    def save(self, *args, **kwargs):
        """Ensure proper ordering after save."""
        super().save(*args, **kwargs)
        if hasattr(self, 'dirnode'):
            self.dirnode.fix_tree()


class DirNode(MP_Node, ItemMixin):
    """A directory in the file tree structure using treebeard."""

    node_order_by = ['type_order', 'display']

    type_order = models.IntegerField(default=1, editable=False)

    class Meta:
        verbose_name = 'directory'
        verbose_name_plural = 'directories'
        ordering = ['type_order', 'display']

    def save(self, *args, **kwargs):
        """Ensure tree is fixed after save."""
        super().save(*args, **kwargs)
        self.fix_tree()

    def get_descendants_by_type(
        self, model_class: type
    ) -> List[Union['AIModel', 'Prompt']]:
        """Get all descendants of a specific type."""
        return model_class.objects.filter(dirnode=self).order_by(
            'type_order', 'display'
        )

    def get_all_descendants(
        self, include_self: bool = False
    ) -> List[Union['DirNode', 'AIModel', 'Prompt']]:
        """Return a list of all descendants of this DirNode."""
        if include_self:
            descendants = [self]
        else:
            descendants = []

        # Get model instances associated with this node
        descendants.extend(
            AIModel.objects.filter(dirnode=self).order_by('type_order', 'display')
        )
        descendants.extend(
            Prompt.objects.filter(dirnode=self).order_by('type_order', 'display')
        )

        # Get child directories and their descendants
        for child in self.get_children().order_by('type_order', 'display'):
            descendants.extend(child.get_all_descendants(include_self=True))

        return descendants


class AIModel(ItemMixin):
    """A model that can be used to generate text."""

    type_order = models.IntegerField(default=2, editable=False)
    dirnode = models.ForeignKey(
        DirNode,
        on_delete=models.CASCADE,
        related_name='aimodels',
    )
    endpoint = models.URLField(
        validators=[URLValidator()],
        help_text='The URL endpoint for the AI',
        blank=True,
    )
    encrypted_api_key = models.BinaryField(null=True, blank=True)
    parameters = JSONField(
        null=True,
        blank=True,
        help_text='Arbitrary key-value pairs for model parameters',
    )

    class Meta:
        verbose_name = 'AI model'
        verbose_name_plural = 'AI models'
        ordering = ['type_order', 'display']

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

    type_order = models.IntegerField(default=3, editable=False)
    dirnode = models.ForeignKey(
        DirNode, on_delete=models.CASCADE, related_name='prompts'
    )
    text = models.TextField(blank=True)
    aimodels = models.ManyToManyField(AIModel, blank=True, related_name='prompts')
    fields = models.ManyToManyField(Field, blank=True, related_name='prompts')

    class Meta:
        verbose_name = 'prompt'
        verbose_name_plural = 'prompts'
        ordering = ['type_order', 'display']

    def __str__(self) -> str:
        return f'{self.display}: {self.text[:50]}...'

    def save(self, *args, **kwargs) -> None:
        """Saves the model and updates the AI models."""
        super().save(*args, **kwargs)
        self._update_aimodels()

    def get_ancestor_aimodels(self) -> QuerySet[AIModel]:
        """Returns all AIModels in the ancestor directories."""
        return self.get_ancestor_aimodels_for_dirnode(self.dirnode_id)

    @staticmethod
    def get_ancestor_aimodels_for_dirnode(dirnode_id: int | None) -> QuerySet[AIModel]:
        """Returns all AIModels in the requested directory's ancestors."""
        dirnode = DirNode.objects.get(id=dirnode_id)
        ancestors = dirnode.get_ancestors()
        ancestors = list(ancestors)
        ancestors.append(dirnode)

        return AIModel.objects.filter(dirnode__in=ancestors).order_by(
            'type_order', 'display'
        )

    def _update_aimodels(self) -> None:
        """Update AIModels so only those in the ancestor directories are included."""
        valid_aimodel_ids = set(
            self.get_ancestor_aimodels().values_list('id', flat=True)
        )
        aimodels_to_remove = self.aimodels.exclude(id__in=valid_aimodel_ids)
        self.aimodels.remove(*aimodels_to_remove)
