# subtitles/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('languages/', views.get_languages_view, name='get_languages'),
    path('extract/', views.get_subtitles_view, name='get_subtitles'),
]