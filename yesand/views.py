from django.shortcuts import render
from django.views.generic import TemplateView

from .models import Folder


def index(request):
    return render(request, 'index.html')


class SidebarView(TemplateView):
    template_name = 'sidebar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['folders'] = Folder.objects.all()
        return context
