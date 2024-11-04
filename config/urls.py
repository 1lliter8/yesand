from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView

from yesand import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', views.health_check, name='health'),
    path('graphql/', csrf_exempt(GraphQLView.as_view(graphiql=True)), name='api'),
    path('', views.ProjectsView.as_view(), name='projects'),
    path('filesystem/', views.TreeView.get_filesystem, name='get_filesystem'),
    path(
        'breadcrumb/<str:node_type>/<int:node_id>/',
        views.TreeView.get_breadcrumb,
        name='get_breadcrumb',
    ),
    path(
        'content/<str:node_type>/<int:node_id>/',
        views.TreeView.get_content,
        name='get_content',
    ),
    path(
        'modal/<str:node_type>/<str:action>/',
        views.ModalView.handle_modal,
        name='modal_no_node',
    ),
    path(
        'modal/<str:node_type>/<str:action>/<int:node_id>/',
        views.ModalView.handle_modal,
        name='modal_with_node',
    ),
    path(
        'edit/<str:node_type>/<int:node_id>/',
        views.TreeView.edit_node,
        name='edit_node',
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
