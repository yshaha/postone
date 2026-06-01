from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('generate/', views.generate, name='generate'),
    path('history/', views.history, name='history'),
    path('content-types/', views.content_type_list, name='content_type_list'),
    path('content-types/create/', views.content_type_create, name='content_type_create'),
    path('content-types/<int:pk>/', views.content_type_detail, name='content_type_detail'),
    path('content-types/<int:pk>/edit/', views.content_type_edit, name='content_type_edit'),
    path('content-types/<int:pk>/delete/', views.content_type_delete, name='content_type_delete'),
    path('content-types/<int:content_type_pk>/prompts/create/', views.channel_prompt_create, name='channel_prompt_create'),
    path('prompts/<int:pk>/edit/', views.channel_prompt_edit, name='channel_prompt_edit'),
    path('channels/', views.channel_list, name='channel_list'),
    path('channels/create/', views.channel_create, name='channel_create'),
    path('channels/<int:pk>/edit/', views.channel_edit, name='channel_edit'),
    path('channels/<int:pk>/delete/', views.channel_delete, name='channel_delete'),
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/credit-grant/', views.user_credit_grant, name='user_credit_grant'),
    path('credits/', views.credit_list, name='credit_list'),
    path('credits/charge/', views.credit_charge, name='credit_charge'),
    path('stats/', views.stats, name='stats'),
    path('prompts/<int:channel_prompt_pk>/options/', views.prompt_option_manage, name='prompt_option_manage'),
    path('prompts/<int:channel_prompt_pk>/options/group/create/', views.option_group_create, name='option_group_create'),
    path('prompts/options/group/<int:pk>/delete/', views.option_group_delete, name='option_group_delete'),
    path('prompts/options/group/<int:group_pk>/option/create/', views.option_create, name='option_create'),
    path('prompts/options/<int:pk>/delete/', views.option_delete, name='option_delete'),
]