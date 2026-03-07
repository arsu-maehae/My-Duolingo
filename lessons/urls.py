from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Feature A: Vocabulary Bank (หน้าเดียวจบ)
    path('vocab/', views.vocab_bank, name='vocab_bank'),

    # Feature B: Game / Testing
    path('play/', views.play_home, name='play_home'),
    path('play/<int:level_id>/', views.play_level, name='play_level'),
]