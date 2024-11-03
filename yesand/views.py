import logging
from collections import namedtuple

from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView

from .forms import (
    AddAIModelForm,
    AddDirNodeForm,
    AddPromptForm,
    CopyForm,
    DeleteForm,
    EditAIModelForm,
    EditPromptForm,
    MoveForm,
    RenameAIModelForm,
    RenameDirNodeForm,
    RenamePromptForm,
)
from .models import AIModel, DirNode, Prompt

NodeType = namedtuple('NodeType', ['model', 'display_name'])
Action = namedtuple('Action', ['name', 'form'])


class ProjectsView(TemplateView):
    template_name = 'projects.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['root_nodes'] = DirNode.get_root_nodes()
        return context


class TreeView:
    """Handles tree structure display and navigation."""

    @staticmethod
    def get_filesystem(request):
        """Returns the complete filesystem as HTML"""
        root_nodes = DirNode.get_root_nodes()
        return render(
            request, 'filesystem.html', {'filesystem': root_nodes, 'level': 0}
        )

    @staticmethod
    def get_breadcrumb(request, node_type, node_id):
        """Returns breadcrumb HTML for any node type"""
        if node_type == 'dirnode':
            node = get_object_or_404(DirNode, id=node_id)
            ancestors = node.get_ancestors()
        else:
            model = AIModel if node_type == 'aimodel' else Prompt
            node = get_object_or_404(model, id=node_id)
            ancestors = node.dirnode.get_ancestors() if node.dirnode else []

        return render(
            request, 'breadcrumb.html', {'ancestors': ancestors, 'current_node': node}
        )

    @staticmethod
    def get_content(request, node_type, node_id):
        """Returns main content HTML for any node type"""
        # If this is a modal action, delegate to ModalView
        if action := request.GET.get('action'):
            return ModalView.handle_modal(request, node_type, node_id, action)

        # Otherwise, show the content
        if node_type == 'dirnode':
            node = get_object_or_404(DirNode, id=node_id)
            # Get all descendant directories
            all_dirs = [node] + list(node.get_descendants())

            # Get all AIModels and Prompts from the directory and all its descendants
            aimodels = AIModel.objects.filter(dirnode__in=all_dirs).order_by('display')
            prompts = Prompt.objects.filter(dirnode__in=all_dirs).order_by('display')

            return render(
                request,
                'dirnode/content.html',
                {'dirnode': node, 'aimodels': aimodels, 'prompts': prompts},
            )
        else:
            model = AIModel if node_type == 'aimodel' else Prompt
            node = get_object_or_404(model, id=node_id)
            template = f"{'ai' if node_type == 'aimodel' else 'prompt'}/card.html"
            return render(request, template, {node_type: node})

    @staticmethod
    def edit_node(request, node_type, node_id):
        """Handle both GET (show form) and POST (save changes) for editing."""
        if node_type == 'aimodel':
            model = AIModel
            form_class = EditAIModelForm
            template = 'ai/edit.html'
        elif node_type == 'prompt':
            model = Prompt
            form_class = EditPromptForm
            template = 'prompt/edit.html'
        else:
            raise Http404('Node type not supported for editing')

        node = get_object_or_404(model, id=node_id)

        if request.method == 'POST':
            form = form_class(request.POST, instance=node)
            if form.is_valid():
                form.save()
                template = f"{template.split('/')[0]}/card.html"
                return render(request, template, {node_type: node})
        else:
            form = form_class(instance=node)

        return render(request, template, {'form': form, node_type: node})


class ModalView:
    """Handle all modal-related operations."""

    NODES = {
        'dirnode': NodeType(DirNode, 'directory'),
        'aimodel': NodeType(AIModel, 'AI model'),
        'prompt': NodeType(Prompt, 'prompt'),
    }

    ACTIONS = {
        'add': Action(
            'Add',
            {
                'dirnode': AddDirNodeForm,
                'aimodel': AddAIModelForm,
                'prompt': AddPromptForm,
            },
        ),
        'rename': Action(
            'Rename',
            {
                'dirnode': RenameDirNodeForm,
                'aimodel': RenameAIModelForm,
                'prompt': RenamePromptForm,
            },
        ),
        'move': Action('Move', MoveForm),
        'copy': Action('Copy', CopyForm),
        'delete': Action('Delete', DeleteForm),
    }

    @classmethod
    def _get_form(cls, request, node_type, action, node_id=None):
        """Get a form instance, either from POST data or empty."""
        action_config = cls.ACTIONS[action]
        is_post = request.method == 'POST'
        data = request.POST if is_post else None

        if action == 'add':
            initial = {}
            if not is_post and (parent_id := request.GET.get('parent_id')):
                initial['parent_id'] = parent_id
            return action_config.form[node_type](data, initial=initial)
        elif action == 'rename':
            form_class = action_config.form[node_type]
            instance = get_object_or_404(cls.NODES[node_type].model, id=node_id)
            return form_class(data, instance=instance)
        elif action in ['move', 'copy']:
            form = action_config.form(data)

            excluded_ids = set()
            if node_id:
                if node_type == 'dirnode':
                    node = get_object_or_404(DirNode, id=node_id)
                    excluded_ids.add(node.id)
                    excluded_ids.update(child.id for child in node.get_descendants())
                else:
                    model = cls.NODES[node_type].model
                    node = get_object_or_404(model, id=node_id)
                    if node.dirnode:
                        excluded_ids.add(node.dirnode.id)

            choices = []
            if node_type == 'dirnode':
                choices.append(('', '(none - root level)'))

            choices.extend(
                (node.id, '—' * node.get_depth() + ' ' + node.display)
                for node in DirNode.get_tree()
                if node.id not in excluded_ids
            )
            form.fields['target_id'].choices = choices

            return form
        elif action == 'delete':
            return action_config.form(data)

        return None

    @staticmethod
    def _copy_directory_tree(node: DirNode, target_dir=None):
        """
        Recursively copy a directory and all its contents.

        Args:
            node (DirNode): The directory node to copy
            target_dir (DirNode, optional): The target parent directory

        Returns:
            DirNode: The new copy of the directory
        """
        if target_dir:
            new_dir = target_dir.add_child(display=node.display)
        else:
            new_dir = DirNode.add_root(display=node.display)

        for aimodel in node.aimodels.all():
            new_aimodel = AIModel.objects.get(id=aimodel.id)
            new_aimodel.pk = None
            new_aimodel.dirnode = new_dir
            new_aimodel.save()

        for prompt in node.prompts.all():
            new_prompt = Prompt.objects.get(id=prompt.id)
            new_prompt.pk = None
            new_prompt.dirnode = new_dir
            new_prompt.save()

        for child in node.get_children():
            ModalView._copy_directory_tree(child, new_dir)

        return new_dir

    @classmethod
    def _process_action(cls, request, node_type, action, node_id, form=None):
        """Process any modal action and return appropriate response."""
        model = cls.NODES[node_type].model
        node = get_object_or_404(model, id=node_id) if node_id else None

        # Get parent info before any action that might delete the node
        parent_type = parent_id = None
        if node:
            if node_type == 'dirnode':
                parent = node.get_parent()
                if parent:
                    parent_type = 'dirnode'
                    parent_id = parent.id
            elif hasattr(node, 'dirnode') and node.dirnode:
                parent_type = 'dirnode'
                parent_id = node.dirnode.id

        # Process the action
        if action in ['add', 'rename']:
            result = form.save()
            response = TreeView.get_content(request, node_type, result.id)

        elif action == 'delete':
            node.delete()
            if parent_type and parent_id:
                response = TreeView.get_content(request, parent_type, parent_id)
            else:
                response = render(request, 'welcome.html')

        elif action == 'move':
            target_id = form.cleaned_data['target_id']
            target_dir = get_object_or_404(DirNode, id=target_id) if target_id else None

            if node_type == 'dirnode':
                if target_dir:
                    node.move(target_dir, 'sorted-child')
                else:
                    if node.is_root():
                        node.move(None, 'sorted-sibling')
                    else:
                        root_nodes = DirNode.get_root_nodes()
                        if root_nodes:
                            node.move(root_nodes[0], 'sorted-sibling')
                        else:
                            node.move(None, 'sorted-child')
            else:
                node.dirnode = target_dir
                node.save()

            if target_dir:
                response = TreeView.get_content(request, 'dirnode', target_dir.id)
            else:
                response = render(request, 'welcome.html')

        elif action == 'copy':
            target_id = form.cleaned_data['target_id']
            target_dir = get_object_or_404(DirNode, id=target_id) if target_id else None

            if node_type == 'dirnode':
                new_dir = cls._copy_directory_tree(node, target_dir)
                result_id = new_dir.id
            else:
                new_instance = model.objects.get(id=node_id)
                new_instance.pk = None
                new_instance.dirnode = target_dir
                new_instance.save()
                result_id = new_instance.id

            if target_dir:
                response = TreeView.get_content(request, 'dirnode', target_dir.id)
            else:
                response = TreeView.get_content(request, node_type, result_id)

        response['HX-Trigger'] = 'filesystemChanged'
        return response

    @classmethod
    def handle_modal(cls, request, node_type, action, node_id=None):
        """Single entry point for all modal operations."""
        form = cls._get_form(request, node_type, action, node_id)
        context = {
            'form': form,
            'node_type': node_type,
            'node_id': node_id,
            'action': action,
            'title': f'{cls.ACTIONS[action].name} {cls.NODES[node_type].display_name}',
        }

        if request.method == 'POST':
            if form.is_valid():
                try:
                    return cls._process_action(
                        request, node_type, action, node_id, form
                    )
                except Exception as e:
                    logging.error(f'Error processing action: {e}', exc_info=True)
                    form.add_error(None, str(e))

        response = render(request, f'modal/{action}.html', context)
        if request.method == 'POST':
            response.status_code = 422
        return response
