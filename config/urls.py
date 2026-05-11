from django.contrib import admin
from django.urls import path

from core.views import protected_media
from stories.views import create_project, home, project_detail

urlpatterns = [
    path('', home, name='home'),
    path('projects/new/', create_project, name='create_project'),
    path('projects/<slug:slug>/', project_detail, name='project_detail'),
    path('admin/', admin.site.urls),
    path('media/<path:path>', protected_media, name='protected_media'),
]
