from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

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

        # Recursively get children directories
        dir_data['children'].extend(get_filesystem(parent=_dir, level=level + 1))

        # Add prompts as children
        prompts = Prompt.objects.filter(dir=_dir)
        for prompt in prompts:
            dir_data['children'].append(
                {
                    'type': 'prompt',
                    'display': prompt.display,
                    'id': prompt.id,  # Changed from _dir.id to prompt.id
                    'level': level + 1,
                }
            )
        tree.append(dir_data)

    return tree


def index(request: HttpRequest) -> HttpResponse:
    """Render the index page."""
    filesystem = get_filesystem()
    dirs = Dir.objects.all()

    return render(
        request=request,
        template_name='index.html',
        context={
            'filesystem': filesystem,
            'dirs': dirs,
        },
    )


def load_prompts(request: HttpRequest, dir_id: int) -> HttpResponse:
    """Load all prompts in a directory and its children."""
    _dir = get_object_or_404(Dir, id=dir_id)
    all_prompts = []

    def collect_prompts(_dir: Dir) -> QuerySet[Prompt]:
        children_dirs = Dir.objects.filter(dir=_dir)
        for child_dir in children_dirs:
            collect_prompts(child_dir)
        child_prompts = Prompt.objects.filter(dir=_dir)
        all_prompts.extend(child_prompts)

    collect_prompts(_dir)

    filesystem = get_filesystem()
    dirs = Dir.objects.all()

    return render(
        request=request,
        template_name='index.html',
        context={
            'prompts': all_prompts,
            'dir_name': _dir.display,
            'filesystem': filesystem,
            'dirs': dirs,
        },
    )


def add_prompt(request: HttpRequest) -> HttpResponse:
    """Add a prompt to a directory."""
    if request.method == 'POST':
        display_name = request.POST.get('prompt_display')
        dir_id = request.POST.get('dir_id')
        _dir = get_object_or_404(Dir, id=dir_id)
        _ = Prompt.objects.create(display=display_name, dir=_dir)

        # Get the updated filesystem
        filesystem = get_filesystem()
        dirs = Dir.objects.all()

        return render(
            request=request,
            template_name='index.html',
            context={
                'filesystem': filesystem,
                'dirs': dirs,
            },
        )

    return HttpResponse(status=405)


def add_dir(request: HttpRequest) -> HttpResponse:
    """Add a directory."""
    if request.method == 'POST':
        parent_id = request.POST.get('parent_dir_id')
        dir_name = request.POST.get('dir_name')
        parent_dir = Dir.objects.get(id=parent_id) if parent_id else None
        _ = Dir.objects.create(dir=parent_dir, display=dir_name)

        # Get the updated filesystem
        filesystem = get_filesystem()
        dirs = Dir.objects.all()

        return render(
            request=request,
            template_name='index.html',
            context={
                'filesystem': filesystem,
                'dirs': dirs,
            },
        )


def delete_dir(request: HttpRequest, dir_id: int) -> HttpResponse:
    """Delete a directory."""
    if request.method == 'POST':
        _dir = get_object_or_404(Dir, id=dir_id)
        _dir.delete()

        # Get the updated filesystem
        filesystem = get_filesystem()
        dirs = Dir.objects.all()

        return render(
            request=request,
            template_name='index.html',
            context={
                'filesystem': filesystem,
                'dirs': dirs,
            },
        )


def rename_dir(request: HttpRequest, dir_id: int) -> HttpResponse:
    """Rename a directory."""
    if request.method == 'POST':
        new_dir_name = request.POST.get('new_dir_name')
        _dir = get_object_or_404(Dir, id=dir_id)
        _dir.display = new_dir_name
        _dir.save()

        # Get the updated filesystem
        filesystem = get_filesystem()
        dirs = Dir.objects.all()

        return render(
            request=request,
            template_name='index.html',
            context={
                'filesystem': filesystem,
                'dirs': dirs,
            },
        )


def copy_dir(request: HttpRequest, dir_id: int) -> HttpResponse:
    """Copy a directory and its contents."""
    if request.method == 'POST':
        original_dir = get_object_or_404(Dir, id=dir_id)
        parent_dir = original_dir.dir

        def copy_directory(original: Dir, parent: Dir = None) -> Dir:
            new_dir = Dir.objects.create(dir=parent, display=original.display)

            # Copy Prompts
            for prompt in original.prompts.all():
                new_prompt = Prompt.objects.create(
                    display=prompt.display, text=prompt.text, dir=new_dir
                )
                new_prompt.aimodels.set(prompt.aimodels.all())
                new_prompt.fields.set(prompt.fields.all())
                new_prompt.save()

            # Copy AIModels
            for aimodel in original.aimodels.all():
                AIModel.objects.create(display=aimodel.display, dir=new_dir)

            # Recursively copy child directories
            for child in original.children.all():
                copy_directory(child, new_dir)

            return new_dir

        copy_directory(original_dir, parent_dir)

        # Get the updated filesystem
        filesystem = get_filesystem()
        dirs = Dir.objects.all()

        return render(
            request=request,
            template_name='index.html',
            context={
                'filesystem': filesystem,
                'dirs': dirs,
            },
        )


def move_dir(request: HttpRequest, dir_id: int) -> HttpResponse:
    """Move a directory to a new parent directory."""
    if request.method == 'POST':
        new_parent_id = request.POST.get('new_parent_dir_id')
        new_parent_dir = (
            None
            if new_parent_id == 'None'
            else get_object_or_404(Dir, id=new_parent_id)
        )

        _dir = get_object_or_404(Dir, id=dir_id)
        _dir.dir = new_parent_dir
        _dir.save()

        # Get the updated filesystem
        filesystem = get_filesystem()
        dirs = Dir.objects.all()

        return render(
            request=request,
            template_name='index.html',
            context={
                'filesystem': filesystem,
                'dirs': dirs,
            },
        )
