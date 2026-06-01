from django.db import models
from accounts.models import User


class Channel(models.Model):
    CHANNEL_TYPE_CHOICES = [
        ('text', '텍스트'),
        ('video', '영상 자막'),
        ('image', '이미지 카드'),
    ]

    name = models.CharField(max_length=50, verbose_name='채널명')
    slug = models.SlugField(max_length=50, unique=True, verbose_name='슬러그')
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPE_CHOICES, verbose_name='채널 유형')
    description = models.TextField(blank=True, verbose_name='설명')
    is_auto_publish = models.BooleanField(default=False, verbose_name='자동발행 가능')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    order = models.IntegerField(default=0, verbose_name='정렬순서')

    class Meta:
        verbose_name = '채널'
        verbose_name_plural = '채널 목록'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class ContentType(models.Model):
    name = models.CharField(max_length=100, verbose_name='유형명')
    description = models.TextField(blank=True, verbose_name='설명')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '콘텐츠 유형'
        verbose_name_plural = '콘텐츠 유형 목록'

    def __str__(self):
        return self.name


class ChannelPrompt(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='channel_prompts')
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name='prompts')
    base_prompt = models.TextField(verbose_name='기본 프롬프트')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = '채널 프롬프트'
        verbose_name_plural = '채널 프롬프트 목록'
        unique_together = ['content_type', 'channel']

    def __str__(self):
        return f'{self.content_type.name} - {self.channel.name}'


class PromptOptionGroup(models.Model):
    channel_prompt = models.ForeignKey(ChannelPrompt, on_delete=models.CASCADE, related_name='option_groups')
    name = models.CharField(max_length=50, verbose_name='그룹명')
    label = models.CharField(max_length=50, verbose_name='화면표시명')
    order = models.IntegerField(default=0, verbose_name='정렬순서')

    class Meta:
        verbose_name = '옵션 그룹'
        verbose_name_plural = '옵션 그룹 목록'
        ordering = ['order']

    def __str__(self):
        return f'{self.channel_prompt} - {self.label}'


class PromptOption(models.Model):
    group = models.ForeignKey(PromptOptionGroup, on_delete=models.CASCADE, related_name='options')
    label = models.CharField(max_length=50, verbose_name='옵션명')
    snippet = models.TextField(verbose_name='프롬프트 조각')
    is_default = models.BooleanField(default=False, verbose_name='기본선택')
    order = models.IntegerField(default=0, verbose_name='정렬순서')

    class Meta:
        verbose_name = '프롬프트 옵션'
        verbose_name_plural = '프롬프트 옵션 목록'
        ordering = ['order']

    def __str__(self):
        return f'{self.group.label} - {self.label}'


class ContentRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', '생성중'),
        ('done', '완료'),
        ('failed', '실패'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='content_requests')
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    channel = models.ForeignKey(Channel, on_delete=models.SET_NULL, null=True)
    source_text = models.TextField(verbose_name='입력 소재')
    selected_options = models.JSONField(default=dict, verbose_name='선택된 옵션')
    result_text = models.TextField(blank=True, verbose_name='생성 결과')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    credit_used = models.IntegerField(default=1, verbose_name='사용 크레딧')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '콘텐츠 생성 이력'
        verbose_name_plural = '콘텐츠 생성 이력 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.channel} - {self.created_at:%Y-%m-%d}'