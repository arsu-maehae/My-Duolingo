from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('level/<int:level_id>/', views.play_level, name='play_level'),
]