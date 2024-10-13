from typing import Callable

from django.forms import ModelForm
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views import View

from .forms import AddEditForm, CopyForm
from .models import AIModel, Dir, ItemMixin, Prompt


def get_filesystem(parent: 'Dir' = None, level: int = 0):
    """Extracts the filesystem structure from the database."""
    tree = []

    def create_item_dict(item: ItemMixin, item_type: str, level: int) -> dict:
        """Creates a dictionary representation of an item."""
        return {
            'type': item_type,
            'type_display': item_type.replace('_', ' '),
            'display': item.display,
            'dir': parent.id if parent else None,
            'id': item.id,
            'level': level,
        }

    def add_children(model: ItemMixin, item_type: str, parent_dir: 'Dir', level: int):
        """Adds children of a given type to the tree."""
        return [
            create_item_dict(item=item, item_type=item_type, level=level)
            for item in model.objects.filter(dir=parent_dir).order_by('display')
        ]

    dirs = Dir.objects.filter(dir=parent)
    for _dir in dirs:
        dir_data = create_item_dict(_dir, 'dir', level)
        dir_data['children'] = get_filesystem(parent=_dir, level=level + 1)
        tree.append(dir_data)

    tree.extend(add_children(AIModel, 'aimodel', parent, level + 1))
    tree.extend(add_children(Prompt, 'prompt', parent, level + 1))

    return tree


class ProjectView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        filesystem = get_filesystem()
        dirs = Dir.objects.all()
        return render(
            request,
            'projects.html',
            {
                'filesystem': filesystem,
                'dirs': dirs,
            },
        )


class ItemView(View):
    """Base view for item operations."""

    model: type[ItemMixin]
    template_prefix: str
    view_name: str
    get_actions: dict[str, Callable]
    post_actions: dict[str, Callable]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_actions = {
            'add': self.add_form,
            'copy': self.copy_form,
            'move': self.move_form,
            'delete': self.delete_form,
            'rename': self.rename_form,
        }
        self.post_actions = {
            'add': self.add,
            'copy': self.copy,
            'move': self.move,
            'delete': self.delete,
            'rename': self.rename,
        }

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handles GET requests."""

        action = request.GET.get('action')
        handler = self.get_actions.get(action)
        if handler:
            return handler(request)
        return HttpResponse('Invalid action', status=400)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handles POST requests."""

        action = request.POST.get('action')
        handler = self.post_actions.get(action)
        if handler:
            return handler(request)
        return HttpResponse('Invalid action', status=400)

    def add_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form for adding a new item."""
        form_class = AddEditForm.get_form_class(self.model)
        form = form_class(
            initial={'dir_id': request.GET.get('dir_id')}, initial_creation=True
        )
        return self.render_form(request, form, 'add')

    def add(self, request: HttpRequest) -> HttpResponse:
        """Adds a new item to the database."""
        form_class = AddEditForm.get_form_class(self.model)
        form = form_class(request.POST, initial_creation=True)
        return self.process_form(request, form, 'add')

    def copy_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form for copying an existing item."""
        item = get_object_or_404(
            self.model, id=request.GET.get(f'{self.model._meta.model_name}_id')
        )
        form = CopyForm(item=item)
        return self.render_form(request, form, 'copy', {'item': item})

    def copy(self, request: HttpRequest) -> HttpResponse:
        """Copies an existing item to a new directory, including all children."""
        item = get_object_or_404(
            self.model, id=request.POST.get(f'{self.model._meta.model_name}_id')
        )
        form = CopyForm(request.POST, item=item)
        if form.is_valid():
            form.save()
            return self.render_filesystem(request)
        return self.render_form(request, form, 'copy', {'item': item})

    def move_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form for moving an existing item."""
        item = get_object_or_404(
            self.model, id=request.GET.get(f'{self.model._meta.model_name}_id')
        )
        dirs = Dir.objects.exclude(id=item.dir.id if item.dir else None)
        return self.render_form(request, None, 'move', {'item': item, 'dirs': dirs})

    def move(self, request: HttpRequest) -> HttpResponse:
        """Moves an existing item to a new directory."""
        item = get_object_or_404(
            self.model, id=request.POST.get(f'{self.model._meta.model_name}_id')
        )
        new_dir_id = request.POST.get('new_dir')

        if new_dir_id == 'None':
            item.dir = None
        elif new_dir_id:
            item.dir = get_object_or_404(Dir, id=new_dir_id)
        else:
            return HttpResponseBadRequest('No directory selected')

        item.save()
        return self.render_filesystem(request)

    def delete_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form for deleting an item."""
        item = get_object_or_404(
            self.model, id=request.GET.get(f'{self.model._meta.model_name}_id')
        )
        return self.render_form(request, None, 'delete', {'item': item})

    def delete(self, request: HttpRequest) -> HttpResponse:
        """Deletes an item from the database."""
        item = get_object_or_404(
            self.model, id=request.POST.get(f'{self.model._meta.model_name}_id')
        )
        item.delete()
        return self.render_filesystem(request)

    def rename_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form for renaming an existing item."""
        item = get_object_or_404(
            self.model, id=request.GET.get(f'{self.model._meta.model_name}_id')
        )
        return self.render_form(request, None, 'rename', {'item': item})

    def rename(self, request: HttpRequest) -> HttpResponse:
        """Renames an existing item."""
        item = get_object_or_404(
            self.model, id=request.POST.get(f'{self.model._meta.model_name}_id')
        )
        new_name = request.POST.get('name')
        if new_name:
            item.display = new_name
            item.save()
            return self.render_filesystem(request)
        return self.render_form(
            request, None, 'rename', {'item': item, 'error': 'Name cannot be empty'}
        )

    def render_form(
        self,
        request: HttpRequest,
        form: ModelForm,
        action: str,
        extra_context: dict = None,
    ) -> HttpResponse:
        """Renders a form with the given context."""
        context = {
            'form': form,
            'item_type': self.model._meta.model_name,
            'item_verbose_name': self.model._meta.verbose_name,
            'view_name': self.view_name,
            'action': action,
        }
        if extra_context:
            context.update(extra_context)
        return render(request, f'modal/{action}.html', context)

    def process_form(
        self, request: HttpRequest, form: ModelForm, action: str
    ) -> HttpResponse:
        """Processes a form submission."""
        if form.is_valid():
            form.save()
            return self.render_filesystem(request)
        return self.render_form(request, form, action)

    def render_filesystem(self, request: HttpRequest) -> HttpResponse:
        """Renders the filesystem structure."""
        filesystem = get_filesystem()
        dirs = Dir.objects.all()
        return render(
            request,
            'filesystem.html',
            {
                'filesystem': filesystem,
                'dirs': dirs,
                'level': 0,
            },
        )


class ViewCardMixin:
    """Mixin to provide view card functionality for item views."""

    model: type[ItemMixin]
    template_prefix: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_actions['view'] = self.view

    def view(self, request: HttpRequest) -> HttpResponse:
        """Renders the card for an item."""
        item_id = request.GET.get('id')
        if not item_id:
            return HttpResponseBadRequest('No item ID provided')
        print(item_id)
        print(self.model)
        item = get_object_or_404(self.model, id=item_id)
        print(item)
        return render(
            request,
            f'{self.template_prefix}/card.html',
            {self.model._meta.model_name: item},
        )


class EditMixin:
    """Mixin to provide edit functionality for item views."""

    model: type[ItemMixin]
    template_prefix: str
    view_name: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_actions['edit'] = self.edit_form
        self.post_actions['edit'] = self.edit

    def edit_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form for editing an existing item."""
        item = get_object_or_404(
            self.model, id=request.GET.get(f'{self.model._meta.model_name}_id')
        )
        form_class = AddEditForm.get_form_class(self.model)
        form = form_class(instance=item)
        return render(
            request,
            f'{self.template_prefix}/edit.html',
            {
                'form': form,
                'item_type': self.model._meta.model_name,
                'item_verbose_name': self.model._meta.verbose_name,
                'view_name': self.view_name,
                'action': 'edit',
                self.model._meta.model_name: item,
            },
        )

    def edit(self, request: HttpRequest) -> HttpResponse:
        """Saves changes to an existing item."""
        item = get_object_or_404(
            self.model, id=request.POST.get(f'{self.model._meta.model_name}_id')
        )
        form_class = AddEditForm.get_form_class(self.model)
        form = form_class(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return self.render_filesystem(request)
        return self.edit_form(request)


class SaveMixin:
    """Mixin to provide save functionality for item views."""

    model: type[ItemMixin]
    template_prefix: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.post_actions['save'] = self.save

    def save(self, request: HttpRequest) -> HttpResponse:
        """Saves changes to an existing item."""
        item_id = request.POST.get(f'{self.model._meta.model_name}_id')
        item = get_object_or_404(self.model, id=item_id)
        form = AddEditForm.get_form_class(self.model)(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return render(
                request,
                f'{self.template_prefix}/card.html',
                {self.model._meta.model_name: item},
            )
        else:
            return HttpResponseBadRequest('Invalid form data')


class DirView(ItemView):
    """View for directory operations."""

    model = Dir
    template_prefix = 'dir'
    view_name = 'dir'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_actions['view'] = self.view

    def view(self, request: HttpRequest) -> HttpResponse:
        dir_id = request.GET.get('id')
        _dir = get_object_or_404(Dir, id=dir_id)
        prompts = Prompt.objects.filter(dir=_dir)
        aimodels = AIModel.objects.filter(dir=_dir)

        return render(
            request,
            'dir/dir.html',
            {
                'dir': _dir,
                'prompts': prompts,
                'aimodels': aimodels,
            },
        )


class PromptView(ViewCardMixin, SaveMixin, EditMixin, ItemView):
    """View for prompt operations."""

    model = Prompt
    template_prefix = 'prompt'
    view_name = 'prompt'


class AIView(ViewCardMixin, SaveMixin, EditMixin, ItemView):
    """View for AI model operations."""

    model = AIModel
    template_prefix = 'ai'
    view_name = 'aimodel'
