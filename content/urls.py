from django.urls import path
from . import api

urlpatterns = [
    path('channels/', api.channel_list, name='api_channels'),
    path('options/', api.option_list, name='api_options'),
    path('generate/', api.generate, name='api_generate'),
    path('generate-snippet/', api.generate_snippet, name='api_generate_snippet'),
    path('request/<int:pk>/', api.request_detail, name='api_request_detail'),
]