from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('chat/', views.chat_api, name='chat_api'), 
    path("chat_user_report/", views.chat_user_report, name="chat_user_report"),
]
