from django.contrib import admin
from django.urls import path

from yesand import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.ProjectView.as_view(), name='index'),
    path('dir/', views.DirView.as_view(), name='dir'),
    path('prompt/', views.PromptView.as_view(), name='prompt'),
    path('aimodel/', views.AIView.as_view(), name='aimodel'),
]
