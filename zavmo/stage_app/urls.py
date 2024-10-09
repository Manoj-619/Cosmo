from django.urls import path
from .views import create_org, get_user_profile, chat_view, sync_user

urlpatterns = [
    path('api/org/create/',create_org, name='create_org'),
    path('api/zavmo/chat/', chat_view, name='chat-api'),
    path('api/user/sync/', sync_user, name='sync_user'),
    path('api/user/profile', get_user_profile, name='user-profile'),
]
