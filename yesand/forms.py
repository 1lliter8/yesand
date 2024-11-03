from django import forms
from django.forms import ModelForm
from django_json_widget.widgets import JSONEditorWidget

from .models import AIModel, DirNode, Prompt


class DisplayNameForm(ModelForm):
    """Base form for operations that need a display name."""

    class Meta:
        abstract = True
        fields = ['display']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['display'].widget.attrs.update(
            {'class': 'form-control', 'placeholder': 'Enter display name'}
        )


class TargetNodeForm(forms.Form):
    """Base form for operations that need a target directory."""

    target_id = forms.ChoiceField(
        required=False,
        widget=forms.Select(
            attrs={'class': 'form-select', 'aria-label': 'Select destination directory'}
        ),
    )

    def clean_target_id(self):
        """Convert empty string to None for the target_id field."""
        value = self.cleaned_data['target_id']
        if value == '':
            return None
        return value


class AddDirNodeForm(DisplayNameForm):
    parent_id = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = DirNode
        fields = ['display']

    def save(self):
        if parent_id := self.cleaned_data.get('parent_id'):
            parent = DirNode.objects.get(id=parent_id)
            return parent.add_child(display=self.cleaned_data['display'])
        return DirNode.add_root(display=self.cleaned_data['display'])


class AddAIModelForm(DisplayNameForm):
    parent_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    endpoint = forms.URLField(required=False)
    parameters = forms.JSONField(required=False, widget=JSONEditorWidget)
    api_key = forms.CharField(required=False, widget=forms.PasswordInput)

    class Meta:
        model = AIModel
        fields = ['display', 'endpoint', 'parameters']

    def save(self):
        instance = super().save(commit=False)
        if api_key := self.cleaned_data.get('api_key'):
            instance.key = api_key
        if parent_id := self.cleaned_data.get('parent_id'):
            instance.dirnode_id = parent_id
        instance.save()
        return instance


class AddPromptForm(DisplayNameForm):
    parent_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    text = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'rows': '3',
                'class': 'form-control auto-resize',
                'placeholder': 'Enter prompt text',
            }
        ),
    )

    class Meta:
        model = Prompt
        fields = ['display', 'text']

    def save(self):
        instance = super().save(commit=False)
        if parent_id := self.cleaned_data.get('parent_id'):
            instance.dirnode_id = parent_id
        instance.save()
        return instance


class RenameAIModelForm(DisplayNameForm):
    """Form for renaming AI Models."""

    class Meta(DisplayNameForm.Meta):
        model = AIModel
        fields = ['display']


class RenamePromptForm(DisplayNameForm):
    """Form for renaming Prompts."""

    class Meta(DisplayNameForm.Meta):
        model = Prompt
        fields = ['display']


class RenameDirNodeForm(DisplayNameForm):
    """Form for renaming Directories."""

    class Meta(DisplayNameForm.Meta):
        model = DirNode
        fields = ['display']


class MoveForm(TargetNodeForm):
    """Form for move operations."""

    pass


class CopyForm(TargetNodeForm):
    """Form for copy operations."""

    pass


class DeleteForm(forms.Form):
    """Form for delete operations."""

    pass
