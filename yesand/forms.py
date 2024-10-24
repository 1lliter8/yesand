from typing import Any

from django import forms
from django.db import models, transaction
from django.db.models import Model
from django.forms import ModelForm
from django_json_widget.widgets import JSONEditorWidget

from .models import AIModel, Dir, Prompt

# class PrettyJSONWidget(forms.Textarea):
#     """A widget for displaying JSON in a pretty format."""

#     def format_value(self, value):
#         try:
#             if isinstance(value, str):
#                 value = json.loads(value)
#             return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
#         except (TypeError, ValueError):
#             return super().format_value(value)

#     def value_from_datadict(self, data, files, name):
#         value = super().value_from_datadict(data, files, name)
#         try:
#             json.loads(value)
#             return value
#         except (TypeError, ValueError):
#             return super().format_value(value)


# class JSONFormField(forms.JSONField):
#     """A form field for JSON data with a pretty widget."""

#     widget = PrettyJSONWidget

#     def to_python(self, value):
#         if value in self.empty_values:
#             return None
#         try:
#             if isinstance(value, str):
#                 return json.loads(value)
#             else:
#                 return value
#         except ValueError as e:
#             raise ValidationError('Enter valid JSON') from e

#     def prepare_value(self, value):
#         if isinstance(value, (dict, list)):
#             return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)
#         return value


class AddEditForm(ModelForm):
    """Base form for adding or editing items."""

    dir_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    class Meta:
        abstract = True
        fields = ['display']
        widgets = {
            'display': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.initial_creation = kwargs.pop('initial_creation', False)
        dir_id = kwargs.pop('dir_id', None)
        super().__init__(*args, **kwargs)

        if dir_id is not None:
            self.fields['dir_id'].initial = dir_id
        elif self.instance and self.instance.pk:
            self.fields['dir_id'].initial = self.instance.dir_id

        if self.initial_creation:
            # Keep only required fields where blank and null are both False
            required_fields = ['display', 'dir_id']
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
        """Save the form and set the dir_id if it was passed in."""
        instance = super().save(commit=False)
        if self.cleaned_data.get('dir_id'):
            instance.dir_id = self.cleaned_data['dir_id']

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


class AddEditDirForm(AddEditForm):
    """Form for adding or editing directories."""

    class Meta(AddEditForm.Meta):
        model = Dir


class AddEditAIModelForm(AddEditForm):
    """Form for adding or editing AI models."""

    api_key = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False
    )
    # parameters = JSONFormField()

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

    # def clean_parameters(self):
    #     data = self.cleaned_data.get('parameters')
    #     if isinstance(data, str):
    #         try:
    #             return json.loads(data)
    #         except json.JSONDecodeError as e:
    #             raise forms.ValidationError('Invalid JSON in parameters field') from e
    #     return data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if api_key := self.cleaned_data.get('api_key'):
            instance.key = api_key

        # if parameters := self.cleaned_data.get('parameters'):
        #     instance.parameters = json.dumps(parameters, ensure_ascii=False)

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

        dir_id = None
        if self.instance.pk:
            dir_id = self.instance.dir_id
        else:
            dir_id = self.initial.get('dir_id') or self.data.get('dir_id')

        if aimodels := self.fields.get('aimodels'):
            aimodels.queryset = Prompt.get_ancestor_aimodels_for_dir(dir_id)

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

    new_dir = forms.ModelChoiceField(
        queryset=None, required=False, empty_label='Copy to root'
    )

    def __init__(self, *args, **kwargs):
        self.item = kwargs.pop('item')
        super().__init__(*args, **kwargs)
        self.fields['new_dir'].queryset = Dir.objects.all()

    def clean_new_dir(self) -> Dir:
        """Ensure the new directory is not the same as the current directory."""
        new_dir = self.cleaned_data['new_dir']
        return new_dir

    @transaction.atomic
    def save(self) -> Model:
        """Copy the item and all its children to the new directory."""
        new_parent = self.cleaned_data['new_dir']
        new_item = self._copy_item(self.item, new_parent)

        if isinstance(self.item, Dir):
            self._copy_children(self.item, new_item)

        return new_item

    def _copy_item(self, item: Model, new_parent: Dir) -> Model:
        """Copy an item to a new parent directory."""
        new_item = type(item).objects.get(id=item.id)
        new_item.pk = None
        new_item.dir = new_parent
        new_item.save()
        return new_item

    def _copy_children(self, original_dir: Dir, new_dir: Dir) -> None:
        """Copy all children of a directory to a new directory."""
        for child in Dir.objects.filter(dir=original_dir):
            new_child = self._copy_item(child, new_dir)
            self._copy_children(child, new_child)

        for model in [Prompt, AIModel]:
            for child in model.objects.filter(dir=original_dir):
                self._copy_item(child, new_dir)
