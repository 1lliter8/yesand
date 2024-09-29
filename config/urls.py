from django.contrib import admin
from django.urls import path

from yesand import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('prompts/<int:dir_id>/', views.load_prompts, name='load_prompts'),
    path('add-dir/', views.add_dir, name='add_dir'),
    path('delete_dir/<int:dir_id>/', views.delete_dir, name='delete_dir'),
]
