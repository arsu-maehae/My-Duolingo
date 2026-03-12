from django.urls import path
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # API
    path('api/save-progress/', views.save_progress, name='save_progress'),
    path('api/reset-progress/', views.reset_progress, name='reset_progress'),

    # Feature A: Vocabulary Bank (หน้าเดียวจบ)
    path('vocab/', views.vocab_bank, name='vocab_bank'),

    # Feature B: Game / Testing
    path('play/', views.play_home, name='play_home'),
    path('play/<int:level_id>/', views.play_level, name='play_level'),
]