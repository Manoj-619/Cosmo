from django.urls import path
from stage_app.views import user, chat

urlpatterns = [
    path('org/create/', user.create_org, name='create_org'),
    path('user/sync/', user.sync_user, name='sync_user'),
    path('user/profile/', user.get_user_profile, name='user-profile'),  # Added 
    path('clear-cache/', user.clear_cache, name='clear-cache'),
    path('zavmo/chat/', chat.chat_view, name='chat-api'),  # Added trailing slash
    # path('user/reset/', reset_all, name='reset-all'),
]
