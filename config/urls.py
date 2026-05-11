from django.contrib import admin
from django.urls import path

from core.views import protected_media
from stories.views import create_project, home, home_status, project_detail, project_detail_status

urlpatterns = [
    path('', home, name='home'),
    path('status/home/', home_status, name='home_status'),
    path('projects/new/', create_project, name='create_project'),
    path('projects/<slug:slug>/', project_detail, name='project_detail'),
    path('projects/<slug:slug>/status/', project_detail_status, name='project_detail_status'),
    path('admin/', admin.site.urls),
    path('media/<path:path>', protected_media, name='protected_media'),
]
