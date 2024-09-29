from django.contrib import admin
from django.urls import path

from yesand import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('prompts/<int:dir_id>/', views.load_prompts, name='load_prompts'),
]
