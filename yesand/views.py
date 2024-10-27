from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView

from .forms import AddEditForm
from .models import AIModel, DirNode, Prompt


class ProjectsView(TemplateView):
    template_name = 'projects.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['root_nodes'] = DirNode.get_root_nodes()
        return context


class TreeView:
    TEMPLATE_PATHS = {
        'aimodel': 'ai/card.html',
        'prompt': 'prompt/card.html',
        'dirnode': 'dirnode/content.html',
    }

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
        action = request.GET.get('action')

        if action in ['add', 'rename', 'move', 'copy', 'delete']:
            return TreeView._handle_form_action(request, node_type, node_id, action)

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
            template = TreeView.TEMPLATE_PATHS[node_type]
            model = AIModel if node_type == 'aimodel' else Prompt
            node = get_object_or_404(model, id=node_id)
            context = {model._meta.model_name: node}
            return render(request, template, context)

    @staticmethod
    def _handle_form_action(request, node_type, node_id, action):
        """Handle form-related actions"""
        model = {'dirnode': DirNode, 'aimodel': AIModel, 'prompt': Prompt}[node_type]

        context = {
            'action': action,
            'node_type': node_type,
            'form_class': AddEditForm.get_form_class(model),
        }

        if node_id != 0:
            context['item'] = get_object_or_404(model, id=node_id)

        if action == 'add':
            context['form'] = context['form_class'](initial_creation=True)
        elif action == 'delete':
            template = 'modal/confirm_delete.html'
        else:
            context['form'] = context['form_class'](instance=context['item'])

        template = f'modal/{action}.html'
        return render(request, template, context)
