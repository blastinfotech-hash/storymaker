from django.urls import path

from . import views

app_name = "news"

urlpatterns = [
    path("feeds/", views.sources_panel, name="sources-panel"),
    path("feeds/<int:pk>/", views.sources_panel, name="sources-edit"),
    path("noticias/", views.articles_panel, name="articles-panel"),
]
