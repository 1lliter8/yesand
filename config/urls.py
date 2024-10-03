from django.contrib import admin
from django.urls import path

from yesand import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.ProjectView.as_view(), name='index'),
    path(
        'prompts/<int:dir_id>/',
        views.LoadPromptsView.as_view(),
        name='load_prompts',
    ),
    path(
        'prompts/<int:dir_id>/<int:prompt_id>/',
        views.LoadPromptsView.as_view(),
        name='load_prompts_single',
    ),
    path('dir/', views.DirView.as_view(), name='dir'),
    path('prompt/', views.PromptView.as_view(), name='prompt'),
]
