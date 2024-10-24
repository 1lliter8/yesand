from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from api.api import api
from yesand import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
    path('', views.ProjectView.as_view(), name='index'),
    path('dir/', views.DirView.as_view(), name='dir'),
    path('prompt/', views.PromptView.as_view(), name='prompt'),
    path('aimodel/', views.AIView.as_view(), name='aimodel'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
