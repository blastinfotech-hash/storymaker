from django.urls import path

from . import views

app_name = "stories"

urlpatterns = [
    path("", views.home, name="dashboard"),
    path("projetos/novo/", views.create_project, name="project-create"),
    path("projetos/<slug:slug>/", views.project_detail, name="project-detail"),
]
