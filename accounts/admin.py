from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'company', 'is_active', 'created_at']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email', 'company']
    fieldsets = UserAdmin.fieldsets + (
        ('추가 정보', {'fields': ('role', 'phone', 'company', 'profile_image')}),
    )