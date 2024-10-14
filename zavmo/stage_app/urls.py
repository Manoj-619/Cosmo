from django.urls import path
from .views import create_org, get_user_profile, chat_view, sync_user, reset_all

urlpatterns = [
    path('org/create/', create_org, name='create_org'),
    path('zavmo/chat/', chat_view, name='chat-api'),  # Added trailing slash
    path('user/sync/', sync_user, name='sync_user'),
    path('user/profile/', get_user_profile, name='user-profile'),  # Added 
    path('user/reset/', reset_all, name='reset-all'),
]
