from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from api.api import api
from yesand import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
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
    # path('dirnode/', views.DirView.as_view(), name='dirnode'),
    # path('prompt/', views.PromptView.as_view(), name='prompt'),
    # path('aimodel/', views.AIView.as_view(), name='aimodel'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
