from django.contrib import admin
from django.urls import path

from yesand import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('sidebar/', views.SidebarView.as_view(), name='sidebar'),
    # path('folder/<int:pk>/', FolderDetailView.as_view(), name='folder_detail'),
]
