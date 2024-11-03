# api/schema.py
import graphene
from django_filters import CharFilter, FilterSet
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from yesand.models import AIModel, DirNode, Field, Prompt


class DirNodeFilter(FilterSet):
    path_contains = CharFilter(field_name='path', lookup_expr='contains')
    parent_name = CharFilter(method='filter_by_parent_name')

    class Meta:
        model = DirNode
        fields = {
            'display': ['exact', 'icontains'],
            'depth': ['exact', 'lt', 'gt'],
            'path': ['exact', 'startswith'],
        }

    def filter_by_parent_name(self, queryset, name, value):
        """Filter directories by parent name based on display name pattern"""
        parent_paths = DirNode.objects.filter(display=value).values_list(
            'path', flat=True
        )
        return queryset.filter(path__startswith=tuple(parent_paths))


class AIModelFilter(FilterSet):
    directory = CharFilter(method='filter_by_directory')

    class Meta:
        model = AIModel
        fields = {
            'display': ['exact', 'icontains', 'istartswith'],
            'dirnode__display': ['exact', 'icontains'],
            'endpoint': ['exact', 'icontains'],
        }

    def filter_by_directory(self, queryset, name, value):
        """Filter AI models by directory based on display name pattern"""
        dirnodes = DirNode.objects.filter(display=value)
        valid_dirs = []
        for dirnode in dirnodes:
            valid_dirs.extend([d.id for d in dirnode.get_tree()])
        return queryset.filter(dirnode_id__in=valid_dirs)


class PromptFilter(FilterSet):
    ai_model = CharFilter(method='filter_by_ai_model')
    directory = CharFilter(method='filter_by_directory')
    prompt_type = CharFilter(method='filter_by_prompt_type')

    class Meta:
        model = Prompt
        fields = {
            'display': ['exact', 'icontains', 'istartswith'],
            'dirnode__display': ['exact', 'icontains'],
            'text': ['icontains'],
        }

    def filter_by_ai_model(self, queryset, name, value):
        """Filter prompts by AI model based on display name pattern"""
        return queryset.filter(aimodels__display=value)

    def filter_by_directory(self, queryset, name, value):
        """Filter prompts by directory based on display name pattern"""
        dirnodes = DirNode.objects.filter(display=value)
        valid_dirs = []
        for dirnode in dirnodes:
            valid_dirs.extend([d.id for d in dirnode.get_tree()])
        return queryset.filter(dirnode_id__in=valid_dirs)

    def filter_by_prompt_type(self, queryset, name, value):
        """Filter prompts by type based on display name pattern"""
        return queryset.filter(display__icontains=value)


class FieldType(DjangoObjectType):
    class Meta:
        model = Field
        interfaces = (graphene.relay.Node,)
        fields = ('id', 'template')


class AIModelType(DjangoObjectType):
    prompt_count = graphene.Int()
    api_key = graphene.String()

    class Meta:
        model = AIModel
        interfaces = (graphene.relay.Node,)
        filterset_class = AIModelFilter
        fields = ('id', 'display', 'dirnode', 'endpoint', 'parameters', 'prompts')

    def resolve_api_key(self, info):
        """Return the API key if the user is authenticated"""
        user = info.context.user
        if not user.is_authenticated:
            return None
        return self.key

    def resolve_prompt_count(self, info):
        return self.prompts.count()


class PromptType(DjangoObjectType):
    class Meta:
        model = Prompt
        interfaces = (graphene.relay.Node,)
        filterset_class = PromptFilter
        fields = ('id', 'display', 'text', 'dirnode', 'aimodels', 'fields')


class DirNodeType(DjangoObjectType):
    children = graphene.List(lambda: DirNodeType)
    aimodels = graphene.List(AIModelType)
    prompts = graphene.List(PromptType)

    class Meta:
        model = DirNode
        interfaces = (graphene.relay.Node,)
        filterset_class = DirNodeFilter
        fields = ('id', 'display', 'depth', 'path')

    def resolve_children(self, info):
        """Return the children of this directory"""
        return self.get_children()

    def resolve_aimodels(self, info):
        """Return the AI models in this directory"""
        return self.get_descendants_by_type(AIModel)

    def resolve_prompts(self, info):
        """Return the prompts in this directory"""
        return self.get_descendants_by_type(Prompt)


class Query(graphene.ObjectType):
    # Individual node queries
    dirnode = graphene.relay.Node.Field(DirNodeType)
    aimodel = graphene.relay.Node.Field(AIModelType)
    prompt = graphene.relay.Node.Field(PromptType)

    # List queries with filtering
    all_dirnodes = DjangoFilterConnectionField(DirNodeType)
    all_aimodels = DjangoFilterConnectionField(AIModelType)
    all_prompts = DjangoFilterConnectionField(PromptType)

    # Custom queries for specific use cases
    model_prompts = graphene.List(
        PromptType,
        model_name=graphene.String(required=True),
        directory=graphene.String(),
        prompt_type=graphene.String(),
        exact_name=graphene.String(),
    )

    def resolve_model_prompts(
        self, info, model_name, directory=None, prompt_type=None, exact_name=None
    ):
        """
        Fetch prompts for a specific model with optional filtering.

        Args:
            model_name: Name of the AI model
            directory: Optional directory name to filter by
            prompt_type: Optional prompt type (system, question, etc)
            exact_name: Optional exact prompt name to match
        """
        query = Prompt.objects.filter(aimodels__display=model_name)

        if exact_name:
            query = query.filter(display=exact_name)
        elif prompt_type:
            query = query.filter(display__icontains=prompt_type)

        if directory:
            query = query.filter(dirnode__display=directory)

        return query.distinct()


schema = graphene.Schema(query=Query)
