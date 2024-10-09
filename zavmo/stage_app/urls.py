from django.urls import path
from .views import create_org, create_user, UserProfileView, ChatAPI

urlpatterns = [
    path('api/create_org/',create_org, name='create_org'),
    path('api/create_user/',create_user,name='create_user'),
    path('api/user/profile/',UserProfileView.as_view(), name='user-profile'),
    path('api/zavmo/chat/', ChatAPI.as_view(), name='chat-api'),
]