from django.urls import path

from . import views

app_name = "stories"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("projetos/<int:pk>/", views.project_detail, name="project-detail"),
    path("versoes/<int:version_id>/download/", views.download_version_image, name="version-download"),
]
