from django.db.models import QuerySet
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
        dir_data = {
            'type': 'dir',
            'display': _dir.display,
            'level': level,
            'id': _dir.id,
            'children': [],
        }
        dir_data['children'].extend(get_filesystem(parent=_dir, level=level + 1))
        prompts = Prompt.objects.filter(dir=_dir)
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


class LoadPromptsView(View):
    def get(
        self, request: HttpRequest, dir_id: int, prompt_id: int | None = None
    ) -> HttpResponse:
        _dir = get_object_or_404(Dir, id=dir_id)
        all_prompts = self.get_all_prompts(_dir)

        if prompt_id:
            selected_prompts = all_prompts.filter(id=prompt_id)
        else:
            selected_prompts = all_prompts

        return render(
            request,
            'prompt/prompt.html',
            {
                'prompts': selected_prompts,
                'dir_name': _dir.display,
            },
        )

    def get_all_prompts(self, _dir: Dir) -> QuerySet[Prompt]:
        return Prompt.objects.filter(
            dir__in=Dir.objects.get(id=_dir.id).get_descendants(include_self=True)
        )


class DirView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        action = request.GET.get('action')
        if action == 'add':
            return self.add_dir_form(request)
        elif action == 'delete':
            return self.delete_dir_form(request)
        elif action == 'rename':
            return self.rename_dir_form(request)
        elif action == 'copy':
            return self.copy_dir_form(request)
        elif action == 'move':
            return self.move_dir_form(request)
        else:
            return HttpResponse('Invalid action', status=400)

    def post(self, request: HttpRequest) -> HttpResponse:
        action = request.POST.get('action')
        if action == 'add':
            return self.add_dir(request)
        elif action == 'delete':
            return self.delete_dir(request)
        elif action == 'rename':
            return self.rename_dir(request)
        elif action == 'copy':
            return self.copy_dir(request)
        elif action == 'move':
            return self.move_dir(request)
        else:
            return HttpResponse('Invalid action', status=400)

    def add_dir_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to add a new directory."""
        parent_id = request.GET.get('parent_id', None)
        html = render_to_string(
            'modals/add_dir.html', {'parent_id': parent_id}, request=request
        )
        return HttpResponse(html)

    def delete_dir_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to delete a directory."""
        dir_id = request.GET.get('dir_id')
        html = render_to_string(
            'modals/delete_dir.html', {'dir_id': dir_id}, request=request
        )
        return HttpResponse(html)

    def rename_dir_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to rename a directory."""
        dir_id = request.GET.get('dir_id')
        html = render_to_string(
            'modals/rename_dir.html', {'dir_id': dir_id}, request=request
        )
        return HttpResponse(html)

    def copy_dir_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to copy a directory."""
        dir_id = request.GET.get('dir_id')
        html = render_to_string(
            'modals/copy_dir.html', {'dir_id': dir_id}, request=request
        )
        return HttpResponse(html)

    def move_dir_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to move a directory."""
        dir_id = request.GET.get('dir_id')
        valid_dirs = Dir.objects.exclude(id=dir_id)
        html = render_to_string(
            'modals/move_dir.html',
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


class PromptView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        action = request.GET.get('action')
        if action == 'add':
            return self.add_prompt_form(request)
        elif action == 'delete':
            return self.delete_prompt_form(request)
        elif action == 'copy':
            return self.copy_prompt_form(request)
        elif action == 'move':
            return self.move_prompt_form(request)
        elif action == 'edit':
            return self.edit_prompt(request)
        elif action == 'view':
            return self.view_prompt(request)
        else:
            return HttpResponse('Invalid action', status=400)

    def post(self, request: HttpRequest) -> HttpResponse:
        action = request.POST.get('action')
        if action == 'add':
            return self.add_prompt(request)
        elif action == 'delete':
            return self.delete_prompt(request)
        elif action == 'copy':
            return self.copy_prompt(request)
        elif action == 'move':
            return self.move_prompt(request)
        elif action == 'save':
            return self.save_prompt(request)
        else:
            return HttpResponse('Invalid action', status=400)

    def add_prompt_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to add a new prompt."""
        dir_id = request.GET.get('dir_id')
        html = render_to_string(
            'modals/add_prompt.html', {'dir_id': dir_id}, request=request
        )
        return HttpResponse(html)

    def delete_prompt_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to delete a prompt."""
        prompt_id = request.GET.get('prompt_id')
        html = render_to_string(
            'modals/delete_prompt.html', {'prompt_id': prompt_id}, request=request
        )
        return HttpResponse(html)

    def copy_prompt_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to copy a prompt."""
        prompt_id = request.GET.get('prompt_id')
        html = render_to_string(
            'modals/copy_prompt.html', {'prompt_id': prompt_id}, request=request
        )
        return HttpResponse(html)

    def move_prompt_form(self, request: HttpRequest) -> HttpResponse:
        """Renders the form to move a prompt."""
        prompt_id = request.GET.get('prompt_id')
        dirs = Dir.objects.all()
        html = render_to_string(
            'modals/move_prompt.html',
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

    def view_prompt(self, request: HttpRequest) -> HttpResponse:
        """Renders the prompt card view."""
        prompt_id = request.GET.get('prompt_id')
        prompt = get_object_or_404(Prompt, id=prompt_id)
        html = render_to_string('prompt/card.html', {'prompt': prompt}, request=request)
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
