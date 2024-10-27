from typing import Any

from django import forms
from django.db import models, transaction
from django.db.models import Model
from django.forms import ModelForm
from django_json_widget.widgets import JSONEditorWidget

from .models import AIModel, DirNode, Prompt


class AddEditForm(ModelForm):
    """Base form for adding or editing items."""

    dirnode_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    class Meta:
        abstract = True
        fields = ['display']
        widgets = {
            'display': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.initial_creation = kwargs.pop('initial_creation', False)
        dirnode_id = kwargs.pop('dirnode_id', None)
        super().__init__(*args, **kwargs)

        if dirnode_id is not None:
            self.fields['dirnode_id'].initial = dirnode_id
        elif self.instance and self.instance.pk:
            self.fields['dirnode_id'].initial = self.instance.dirnode_id

        if self.initial_creation:
            # Keep only required fields where blank and null are both False
            required_fields = ['display', 'dirnode_id']
            for field_name in list(self.fields.keys()):
                if field_name in self.Meta.model._meta.fields:
                    model_field = self.Meta.model._meta.get_field(field_name)
                    if not model_field.blank and not model_field.null:
                        required_fields.append(field_name)
                if field_name not in required_fields:
                    del self.fields[field_name]

        # Set up M2M fields
        for field_name in list(self.fields.keys()):
            if field_name in self.Meta.model._meta.fields:
                model_field = self.Meta.model._meta.get_field(field_name)
                if isinstance(model_field, models.ManyToManyField):
                    self.fields[
                        field_name
                    ].queryset = model_field.related_model.objects.all()

    def save(self, commit: bool = True) -> Any:
        """Save the form and set the dirnode_id if it was passed in."""
        instance = super().save(commit=False)
        if self.cleaned_data.get('dirnode_id'):
            instance.dirnode_id = self.cleaned_data['dirnode_id']

        if commit:
            instance.save()
            self._save_m2m()

        return instance

    def _save_m2m(self):
        """Save many-to-many relationships."""
        for field_name in self.fields.keys():
            if field_name in self.Meta.model._meta.fields:
                model_field = self.Meta.model._meta.get_field(field_name)
                if isinstance(model_field, models.ManyToManyField):
                    getattr(self.instance, field_name).set(
                        self.cleaned_data.get(field_name, [])
                    )

    @classmethod
    def get_form_class(cls, model: type[Model]) -> type['AddEditForm'] | None:
        """Class method to get the appropriate form class for a given model."""
        for subclass in cls.__subclasses__():
            if subclass._meta.model == model:
                return subclass
        return None


class AddEditDirNodeForm(AddEditForm):
    """Form for adding or editing directories."""

    position = forms.ChoiceField(
        choices=[
            ('first-child', 'First Child'),
            ('last-child', 'Last Child'),
            ('left', 'Left Sibling'),
            ('right', 'Right Sibling'),
        ],
        initial='last-child',
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta(AddEditForm.Meta):
        model = DirNode
        fields = ['display']

    def save(self, commit: bool = True) -> DirNode:
        """Save the directory node using treebeard's node creation methods."""
        instance = self.instance
        dirnode_id = self.cleaned_data.get('dirnode_id')
        position = self.cleaned_data.get('position', 'last-child')

        if not instance.pk:  # Creating new node
            if dirnode_id:
                parent = DirNode.objects.get(id=dirnode_id)
                instance = parent.add_child(display=self.cleaned_data['display'])
            else:
                instance = DirNode.add_root(display=self.cleaned_data['display'])
        else:  # Updating existing node
            instance.display = self.cleaned_data['display']
            if dirnode_id and instance.dirnode_id != dirnode_id:
                new_parent = DirNode.objects.get(id=dirnode_id)
                instance.move(new_parent, pos=position)
            instance.save()

        return instance


class AddEditAIModelForm(AddEditForm):
    """Form for adding or editing AI models."""

    api_key = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False
    )

    class Meta(AddEditForm.Meta):
        model = AIModel
        fields = ['display', 'endpoint', 'parameters']
        widgets = {
            'display': forms.TextInput(attrs={'class': 'form-control'}),
            'endpoint': forms.TextInput(attrs={'class': 'form-control'}),
            'parameters': JSONEditorWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['api_key'].widget.attrs['placeholder'] = 'API key'

    def save(self, commit=True):
        instance = super().save(commit=False)

        if api_key := self.cleaned_data.get('api_key'):
            instance.key = api_key

        if commit:
            instance.save()

        return instance


class AddEditPromptForm(AddEditForm):
    """Form for adding or editing prompts."""

    class Meta(AddEditForm.Meta):
        model = Prompt
        fields = ['display', 'text', 'aimodels']
        widgets = {
            'display': forms.TextInput(attrs={'class': 'form-control'}),
            'text': forms.Textarea(
                attrs={'class': 'form-control auto-resize', 'rows': '3'}
            ),
            'aimodels': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dirnode_id = None
        if self.instance.pk:
            dirnode_id = self.instance.dirnode_id
        else:
            dirnode_id = self.initial.get('dirnode_id') or self.data.get('dirnode_id')

        if aimodels := self.fields.get('aimodels'):
            aimodels.queryset = Prompt.get_ancestor_aimodels_for_dirnode(dirnode_id)

    def clean(self):
        cleaned_data = super().clean()
        aimodels = cleaned_data.get('aimodels')

        if aimodels:
            # Ensure all selected AI models are permissible
            permissible_ais = set(self.instance.get_ancestor_aimodels())
            selected_ais = set(aimodels)

            if not selected_ais.issubset(permissible_ais):
                self.add_error(
                    'aimodels',
                    (
                        "Some selected AI models are not in this prompt's "
                        'ancestor directories.'
                    ),
                )

        return cleaned_data


class CopyForm(forms.Form):
    """Form for copying an item to a new directory."""

    new_dirnode = forms.ModelChoiceField(
        queryset=None, required=False, empty_label='Copy to root'
    )

    def __init__(self, *args, **kwargs):
        self.item = kwargs.pop('item')
        super().__init__(*args, **kwargs)
        self.fields['new_dirnode'].queryset = DirNode.objects.all()

    def clean_new_dirnode(self) -> DirNode:
        """Ensure the new directory is not the same as the current directory."""
        new_dirnode = self.cleaned_data['new_dirnode']
        return new_dirnode

    @transaction.atomic
    def save(self) -> Model:
        """Copy the item and all its descendants to the new directory."""
        new_parent = self.cleaned_data['new_dirnode']
        new_item = self._copy_item(self.item, new_parent)

        if isinstance(self.item, DirNode):
            self._copy_descendants(self.item, new_item)

        return new_item

    def _copy_item(self, item: Model, new_parent: DirNode) -> Model:
        """Copy an item to a new parent directory."""
        new_item = type(item).objects.get(id=item.id)
        new_item.pk = None

        if isinstance(item, DirNode):
            if new_parent:
                new_item = new_parent.add_child(display=item.display)
            else:
                new_item = DirNode.add_root(display=item.display)
        else:
            new_item.dirnode = new_parent
            new_item.save()

        return new_item

    def _copy_descendants(self, original_dir: DirNode, new_dir: DirNode) -> None:
        """Copy all descendants of a directory to a new directory."""
        # Copy child directories
        for child in original_dir.get_children():
            new_child = self._copy_item(child, new_dir)
            self._copy_descendants(child, new_child)

        # Copy AIModels and Prompts
        for model in [AIModel, Prompt]:
            for item in model.objects.filter(dirnode=original_dir):
                self._copy_item(item, new_dir)
