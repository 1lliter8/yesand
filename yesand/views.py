from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views import View

from .models import AIModel, Dir, Prompt


def get_filesystem(parent: Dir = None, level: int = 0) -> list[dict]:
    """Extracts the filesystem structure from the database."""
    tree = []
    dirs = Dir.objects.filter(dir=parent)
    for _dir in dirs:
        # Create a dictionary for the current directory
        dir_data = {
            'type': 'dir',
            'display': _dir.display,
            'level': level,
            'id': _dir.id,
            'children': [],
        }
        dir_data['children'].extend(get_filesystem(parent=_dir, level=level + 1))

        # Add AIModels to the directory
        aimodels = AIModel.objects.filter(dir=_dir).order_by('display')
        for aimodel in aimodels:
            dir_data['children'].append(
                {
                    'type': 'aimodel',
                    'display': aimodel.display,
                    'dir': _dir.id,
                    'id': aimodel.id,
                    'level': level + 1,
                }
            )

        # Add Prompts to the directory
        prompts = Prompt.objects.filter(dir=_dir).order_by('display')
        for prompt in prompts:
            dir_data['children'].append(
                {
                    'type': 'prompt',
                    'display': prompt.display,
                    'dir': _dir.id,
                    'id': prompt.id,
                    'level': level + 1,
                }
            )

        tree.append(dir_data)
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


class RenderFilesystemMixin:
    """Mixin to render the filesystem view."""

    def render_filesystem(self, request: HttpRequest) -> HttpResponse:
        """Renders the filesystem view."""
        filesystem = get_filesystem()
        dirs = Dir.objects.all()
        html = render_to_string(
            'filesystem.html',
            {
                'filesystem': filesystem,
                'dirs': dirs,
                'level': 0,
            },
            request=request,
        )
        return HttpResponse(html)


class DirView(View, RenderFilesystemMixin):
    """View for directory operations."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handles GET requests."""
        action = request.GET.get('action')

        match action:
            case 'view':
                return self.view_dir(request)
            case 'add':
                return self.add_dir_form(request)
            case 'delete':
                return self.delete_dir_form(request)
            case 'rename':
                return self.rename_dir_form(request)
            case 'copy':
                return self.copy_dir_form(request)
            case 'move':
                return self.move_dir_form(request)
            case _:
                return HttpResponse('Invalid action', status=400)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handles POST requests."""
        action = request.POST.get('action')

        match action:
            case 'add':
                return self.add_dir(request)
            case 'delete':
                return self.delete_dir(request)
            case 'rename':
                return self.rename_dir(request)
            case 'copy':
                return self.copy_dir(request)
            case 'move':
                return self.move_dir(request)
            case _:
                return HttpResponse('Invalid action', status=400)

    def view_dir(self, request: HttpRequest) -> HttpResponse:
        dir_id = request.GET.get('dir_id')
        _dir = get_object_or_404(Dir, id=dir_id)
        prompts = Prompt.objects.filter(dir=_dir)
        aimodels = AIModel.objects.filter(dir=_dir)

        html = render_to_string(
            'dir/dir.html',
            {
                'dir': _dir,
                'prompts': prompts,
                'aimodels': aimodels,
            },
            request=request,
        )
        return HttpResponse(html)

    def add_dir_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to add a new directory."""
        parent_id = request.GET.get('parent_id', None)
        html = render_to_string(
            'dir/add.html', {'parent_id': parent_id}, request=request
        )
        return HttpResponse(html)

    def delete_dir_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to delete a directory."""
        dir_id = request.GET.get('dir_id')
        html = render_to_string('dir/delete.html', {'dir_id': dir_id}, request=request)
        return HttpResponse(html)

    def rename_dir_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to rename a directory."""
        dir_id = request.GET.get('dir_id')
        html = render_to_string('dir/rename.html', {'dir_id': dir_id}, request=request)
        return HttpResponse(html)

    def copy_dir_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to copy a directory."""
        dir_id = request.GET.get('dir_id')
        html = render_to_string('dir/copy.html', {'dir_id': dir_id}, request=request)
        return HttpResponse(html)

    def move_dir_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to move a directory."""
        dir_id = request.GET.get('dir_id')
        valid_dirs = Dir.objects.exclude(id=dir_id)
        html = render_to_string(
            'dir/move.html',
            {'dir_id': dir_id, 'valid_dirs': valid_dirs},
            request=request,
        )
        return HttpResponse(html)

    def add_dir(self, request: HttpRequest) -> HttpResponse:
        """Adds a new directory to the filesystem."""
        parent_id = request.POST.get('parent_dir_id')
        dir_name = request.POST.get('dir_name')

        if parent_id == 'None':
            parent_id = None

        parent_dir = Dir.objects.get(id=parent_id) if parent_id else None
        Dir.objects.create(dir=parent_dir, display=dir_name)
        return self.render_filesystem(request)

    def delete_dir(self, request: HttpRequest) -> HttpResponse:
        """Deletes a directory from the filesystem."""
        dir_id = request.POST.get('dir_id')
        _dir = get_object_or_404(Dir, id=dir_id)
        _dir.delete()
        return self.render_filesystem(request)

    def rename_dir(self, request: HttpRequest) -> HttpResponse:
        """Renames a directory in the filesystem."""
        dir_id = request.POST.get('dir_id')
        new_dir_name = request.POST.get('new_dir_name')
        _dir = get_object_or_404(Dir, id=dir_id)
        _dir.display = new_dir_name
        _dir.save()
        return self.render_filesystem(request)

    def copy_dir(self, request: HttpRequest) -> HttpResponse:
        """Copies a directory in the filesystem."""
        dir_id = request.POST.get('dir_id')
        original_dir = get_object_or_404(Dir, id=dir_id)
        parent_dir = original_dir.dir

        def _copy_dir(original: Dir, parent: Dir = None) -> Dir:
            new_dir = Dir.objects.create(dir=parent, display=original.display)
            for prompt in original.prompts.all():
                new_prompt = Prompt.objects.create(
                    display=prompt.display, text=prompt.text, dir=new_dir
                )
                new_prompt.aimodels.set(prompt.aimodels.all())
                new_prompt.fields.set(prompt.fields.all())
                new_prompt.save()
            for aimodel in original.aimodels.all():
                AIModel.objects.create(display=aimodel.display, dir=new_dir)
            for child in original.children.all():
                _copy_dir(child, new_dir)
            return new_dir

        _copy_dir(original_dir, parent_dir)
        return self.render_filesystem(request)

    def move_dir(self, request: HttpRequest) -> HttpResponse:
        """Moves a directory in the filesystem."""
        dir_id = request.POST.get('dir_id')
        new_parent_id = request.POST.get('new_parent_dir_id')
        new_parent_dir = (
            None
            if new_parent_id == 'None'
            else get_object_or_404(Dir, id=new_parent_id)
        )
        _dir = get_object_or_404(Dir, id=dir_id)
        _dir.dir = new_parent_dir
        _dir.save()
        return self.render_filesystem(request)


class PromptView(View, RenderFilesystemMixin):
    """View for prompt operations."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handles GET requests."""
        action = request.GET.get('action')

        match action:
            case 'add':
                return self.add_prompt_form(request)
            case 'delete':
                return self.delete_prompt_form(request)
            case 'copy':
                return self.copy_prompt_form(request)
            case 'move':
                return self.move_prompt_form(request)
            case 'edit':
                return self.edit_prompt(request)
            case 'view':
                return self.view_prompt(request)
            case _:
                return HttpResponse('Invalid action', status=400)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handles POST requests."""
        action = request.POST.get('action')

        match action:
            case 'add':
                return self.add_prompt(request)
            case 'delete':
                return self.delete_prompt(request)
            case 'copy':
                return self.copy_prompt(request)
            case 'move':
                return self.move_prompt(request)
            case 'save':
                return self.save_prompt(request)
            case _:
                return HttpResponse('Invalid action', status=400)

    def view_prompt(self, request: HttpRequest) -> HttpResponse:
        """Renders the prompt card view."""
        prompt_id = request.GET.get('prompt_id')
        prompt = get_object_or_404(Prompt, id=prompt_id)
        html = render_to_string('prompt/card.html', {'prompt': prompt}, request=request)
        return HttpResponse(html)

    def add_prompt_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to add a new prompt."""
        dir_id = request.GET.get('dir_id')
        html = render_to_string('prompt/add.html', {'dir_id': dir_id}, request=request)
        return HttpResponse(html)

    def delete_prompt_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to delete a prompt."""
        prompt_id = request.GET.get('prompt_id')
        html = render_to_string(
            'prompt/delete.html', {'prompt_id': prompt_id}, request=request
        )
        return HttpResponse(html)

    def copy_prompt_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to copy a prompt."""
        prompt_id = request.GET.get('prompt_id')
        html = render_to_string(
            'prompt/copy.html', {'prompt_id': prompt_id}, request=request
        )
        return HttpResponse(html)

    def move_prompt_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to move a prompt."""
        prompt_id = request.GET.get('prompt_id')
        dirs = Dir.objects.all()
        html = render_to_string(
            'prompt/move.html',
            {'prompt_id': prompt_id, 'dirs': dirs},
            request=request,
        )
        return HttpResponse(html)

    def add_prompt(self, request: HttpRequest) -> HttpResponse:
        """Adds a new prompt to the filesystem."""
        display_name = request.POST.get('prompt_display')
        dir_id = request.POST.get('dir_id')
        _dir = get_object_or_404(Dir, id=dir_id)
        Prompt.objects.create(display=display_name, dir=_dir)
        return self.render_filesystem(request)

    def delete_prompt(self, request: HttpRequest) -> HttpResponse:
        """Deletes a prompt from the filesystem."""
        prompt_id = request.POST.get('prompt_id')
        prompt = get_object_or_404(Prompt, id=prompt_id)
        prompt.delete()
        return self.render_filesystem(request)

    def copy_prompt(self, request: HttpRequest) -> HttpResponse:
        """Copies a prompt in the filesystem."""
        prompt_id = request.POST.get('prompt_id')
        prompt = get_object_or_404(Prompt, id=prompt_id)
        prompt.pk = None
        prompt.save()
        return self.render_filesystem(request)

    def move_prompt(self, request: HttpRequest) -> HttpResponse:
        """Moves a prompt in the filesystem."""
        prompt_id = request.POST.get('prompt_id')
        new_dir_id = request.POST.get('new_dir_id')
        new_dir = get_object_or_404(Dir, id=new_dir_id)
        prompt = get_object_or_404(Prompt, id=prompt_id)
        prompt.dir = new_dir
        prompt.save()
        return self.render_filesystem(request)

    def edit_prompt(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to edit a prompt."""
        prompt_id = request.GET.get('prompt_id')
        prompt = get_object_or_404(Prompt, id=prompt_id)
        all_aimodels = AIModel.objects.all()
        html = render_to_string(
            'prompt/edit.html',
            {'prompt': prompt, 'all_aimodels': all_aimodels},
            request=request,
        )
        return HttpResponse(html)

    def save_prompt(self, request: HttpRequest) -> HttpResponse:
        """Saves changes to an existing prompt."""
        prompt_id = request.POST.get('prompt_id')
        prompt = get_object_or_404(Prompt, id=prompt_id)
        prompt.display = request.POST.get('display')
        prompt.text = request.POST.get('text')
        prompt.save()

        # Update AIModels
        selected_aimodels = request.POST.getlist('aimodels')
        prompt.aimodels.set(selected_aimodels)

        # Render the updated prompt card
        html = render_to_string('prompt/card.html', {'prompt': prompt}, request=request)
        return HttpResponse(html)


class AIView(View, RenderFilesystemMixin):
    """View for AI model operations."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handles GET requests."""
        action = request.GET.get('action')

        match action:
            case 'view':
                return self.view_aimodel(request)
            case 'add':
                return self.add_aimodel_form(request)
            case 'edit':
                return self.edit_aimodel(request)
            case 'copy':
                return self.copy_aimodel_form(request)
            case 'move':
                return self.move_aimodel_form(request)
            case 'delete':
                return self.delete_aimodel_form(request)
            case _:
                return HttpResponse('Invalid action', status=400)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handles POST requests."""
        action = request.POST.get('action')

        match action:
            case 'add':
                return self.add_aimodel(request)
            case 'save':
                return self.save_aimodel(request)
            case 'copy':
                return self.copy_aimodel(request)
            case 'move':
                return self.move_aimodel(request)
            case 'delete':
                return self.delete_aimodel(request)
            case _:
                return HttpResponse('Invalid action', status=400)

    def view_aimodel(self, request: HttpRequest) -> HttpResponse:
        """Renders the AI model card view."""
        aimodel_id = request.GET.get('aimodel_id')
        aimodel = get_object_or_404(AIModel, id=aimodel_id)
        html = render_to_string('ai/card.html', {'aimodel': aimodel}, request=request)
        return HttpResponse(html)

    def add_aimodel_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to add a new AI model."""
        dir_id = request.GET.get('dir_id')
        html = render_to_string('ai/add.html', {'dir_id': dir_id}, request=request)
        return HttpResponse(html)

    def edit_aimodel(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to edit an AI model."""
        aimodel_id = request.GET.get('aimodel_id')
        aimodel = get_object_or_404(AIModel, id=aimodel_id)
        html = render_to_string('ai/edit.html', {'aimodel': aimodel}, request=request)
        return HttpResponse(html)

    def add_aimodel(self, request: HttpRequest) -> HttpResponse:
        """Adds a new AI model to the filesystem."""
        display_name = request.POST.get('aimodel_display')
        dir_id = request.POST.get('dir_id')
        _dir = get_object_or_404(Dir, id=dir_id)
        AIModel.objects.create(display=display_name, dir=_dir)
        return self.render_filesystem(request)

    def save_aimodel(self, request: HttpRequest) -> HttpResponse:
        """Saves changes to an existing AI model."""
        aimodel_id = request.POST.get('aimodel_id')
        aimodel = get_object_or_404(AIModel, id=aimodel_id)
        aimodel.display = request.POST.get('display')
        aimodel.save()
        html = render_to_string('ai/card.html', {'aimodel': aimodel}, request=request)
        return HttpResponse(html)

    def copy_aimodel_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to copy an AI model."""
        aimodel_id = request.GET.get('aimodel_id')
        aimodel = get_object_or_404(AIModel, id=aimodel_id)
        html = render_to_string('ai/copy.html', {'aimodel': aimodel}, request=request)
        return HttpResponse(html)

    def move_aimodel_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to move an AI model."""
        aimodel_id = request.GET.get('aimodel_id')
        aimodel = get_object_or_404(AIModel, id=aimodel_id)
        dirs = Dir.objects.exclude(id=aimodel.dir.id)
        html = render_to_string(
            'ai/move.html', {'aimodel': aimodel, 'dirs': dirs}, request=request
        )
        return HttpResponse(html)

    def delete_aimodel_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to delete an AI model."""
        aimodel_id = request.GET.get('aimodel_id')
        aimodel = get_object_or_404(AIModel, id=aimodel_id)
        html = render_to_string('ai/delete.html', {'aimodel': aimodel}, request=request)
        return HttpResponse(html)

    def copy_aimodel(self, request: HttpRequest) -> HttpResponse:
        """Copies an AI model."""
        aimodel_id = request.POST.get('aimodel_id')
        aimodel = get_object_or_404(AIModel, id=aimodel_id)
        aimodel.pk = None
        aimodel.save()
        return self.render_filesystem(request)

    def move_aimodel(self, request: HttpRequest) -> HttpResponse:
        """Moves an AI model to a different directory."""
        aimodel_id = request.POST.get('aimodel_id')
        new_dir_id = request.POST.get('new_dir_id')
        aimodel = get_object_or_404(AIModel, id=aimodel_id)
        new_dir = get_object_or_404(Dir, id=new_dir_id)
        aimodel.dir = new_dir
        aimodel.save()
        return self.render_filesystem(request)

    def delete_aimodel(self, request: HttpRequest) -> HttpResponse:
        """Deletes an AI model."""
        aimodel_id = request.POST.get('aimodel_id')
        aimodel = get_object_or_404(AIModel, id=aimodel_id)
        aimodel.delete()
        return self.render_filesystem(request)
