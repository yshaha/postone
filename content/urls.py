from django.urls import path
from . import api

urlpatterns = [
    path('channels/', api.channel_list, name='api_channels'),
    path('options/', api.option_list, name='api_options'),
    path('generate/', api.generate, name='api_generate'),
    path('generate-snippet/', api.generate_snippet, name='api_generate_snippet'),
    path('generate-base-prompt/', api.generate_base_prompt, name='api_generate_base_prompt'),
    path('compare-prompts/', api.compare_prompts, name='api_compare_prompts'),
    path('get-combined-prompt/', api.get_combined_prompt, name='api_get_combined_prompt'),
    path('user/<int:pk>/edit/', api.user_edit, name='api_user_edit'),
    path('user/<int:pk>/credit-grant/', api.user_credit_grant, name='api_user_credit_grant'),
    path('option-group/create/<int:channel_prompt_pk>/', api.option_group_create, name='api_option_group_create'),
    path('option/create/<int:group_pk>/', api.option_create, name='api_option_create'),
    path('menu-permission/<int:pk>/toggle/', api.menu_permission_toggle, name='api_menu_permission_toggle'),
    path('request/<int:pk>/', api.request_detail, name='api_request_detail'),
    path('channel/create/', api.channel_create, name='api_channel_create'),
    path('channel/<int:pk>/edit/', api.channel_edit, name='api_channel_edit'),
    path('content-type/create/', api.content_type_create, name='api_content_type_create'),
    path('content-type/<int:pk>/edit/', api.content_type_edit, name='api_content_type_edit'),
]