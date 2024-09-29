from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Dir, Prompt


def get_filesystem() -> list[dict]:
    """Extracts the filesystem structure from the database."""

    def get_tree(parent: Dir = None, level: int = 0) -> list[dict]:
        tree = []
        dirs = Dir.objects.filter(dir=parent)
        for _dir in dirs:
            dir_data = {
                'type': 'dir',
                'name': _dir.display,
                'level': level,
                'id': _dir.id,
                'children': get_tree(parent=_dir, level=level + 1),
            }
            prompts = Prompt.objects.filter(dir=_dir)
            for prompt in prompts:
                dir_data['children'].append(
                    {
                        'type': 'prompt',
                        'name': prompt.display,
                        'id': _dir.id,
                        'level': level + 1,
                    }
                )
            tree.append(dir_data)
        return tree

    root_dirs = Dir.objects.filter(dir__isnull=True)
    tree = []
    for root_dir in root_dirs:
        tree.append(
            {
                'type': 'dir',
                'name': root_dir.display,
                'level': 0,
                'id': root_dir.id,
                'children': get_tree(parent=root_dir, level=1),
            }
        )
    return tree


def index(request: HttpRequest) -> HttpResponse:
    filesystem = get_filesystem()
    return render(
        request=request,
        template_name='index.html',
        context={
            'filesystem': filesystem,
        },
    )


def load_prompts(request: HttpRequest, dir_id: int) -> HttpResponse:
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

    return render(
        request=request,
        template_name='index.html',
        context={
            'prompts': all_prompts,
            'dir_name': _dir.display,
            'filesystem': filesystem,
        },
    )


def add_dir(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        parent_id = request.POST.get('parent_dir_id')
        dir_name = request.POST.get('dir_name')
        parent_dir = Dir.objects.get(id=parent_id) if parent_id else None
        _ = Dir.objects.create(dir=parent_dir, display=dir_name)

        # Get the updated filesystem
        filesystem = get_filesystem()

        return render(
            request=request,
            template_name='index.html',
            context={
                'filesystem': filesystem,
            },
        )


def delete_dir(request: HttpRequest, dir_id: int) -> HttpResponse:
    if request.method == 'POST':
        _dir = get_object_or_404(Dir, id=dir_id)
        _dir.delete()

        # Get the updated filesystem
        filesystem = get_filesystem()

        return render(
            request=request,
            template_name='index.html',
            context={
                'filesystem': filesystem,
            },
        )


def rename_dir(request: HttpRequest, dir_id: int) -> HttpResponse:
    if request.method == 'POST':
        new_dir_name = request.POST.get('new_dir_name')
        _dir = get_object_or_404(Dir, id=dir_id)
        _dir.display = new_dir_name
        _dir.save()

        # Get the updated filesystem
        filesystem = get_filesystem()

        return render(
            request=request,
            template_name='index.html',
            context={
                'filesystem': filesystem,
            },
        )
