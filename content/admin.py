from django.contrib import admin
from .models import Channel, ContentType, ChannelPrompt, PromptOptionGroup, PromptOption, ContentRequest


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel_type', 'is_auto_publish', 'is_active', 'order']
    list_filter = ['channel_type', 'is_active']
    list_editable = ['order', 'is_active']


@admin.register(ContentType)
class ContentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active']


class PromptOptionInline(admin.TabularInline):
    model = PromptOption
    extra = 2


class PromptOptionGroupInline(admin.StackedInline):
    model = PromptOptionGroup
    extra = 1
    inlines = [PromptOptionInline]


@admin.register(ChannelPrompt)
class ChannelPromptAdmin(admin.ModelAdmin):
    list_display = ['content_type', 'channel', 'is_active', 'updated_at']
    list_filter = ['channel', 'is_active']
    inlines = [PromptOptionGroupInline]


@admin.register(PromptOptionGroup)
class PromptOptionGroupAdmin(admin.ModelAdmin):
    list_display = ['channel_prompt', 'label', 'order']
    inlines = [PromptOptionInline]


@admin.register(ContentRequest)
class ContentRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'content_type', 'channel', 'status', 'credit_used', 'created_at']
    list_filter = ['status', 'channel']
    readonly_fields = ['created_at']