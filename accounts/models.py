from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('master', '마스터'),
        ('admin', '관리자'),
        ('member', '멤버'),
        ('free', '무료회원'),
    ]

    PLAN_CHOICES = [
        ('free', '무료'),
        ('starter', '스타터'),
        ('pro', '프로'),
        ('business', '비즈니스'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='free')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=100, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자 목록'

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'

    @property
    def is_master(self):
        return self.role == 'master'

    @property
    def is_admin(self):
        return self.role in ['master', 'admin']

    @property
    def is_member(self):
        return self.role in ['member', 'free']


class MenuPermission(models.Model):
    ROLE_CHOICES = [
        ('admin', '관리자'),
        ('member', '멤버'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    menu_key = models.CharField(max_length=50, verbose_name='메뉴 키')
    menu_label = models.CharField(max_length=50, verbose_name='메뉴명')
    icon = models.CharField(max_length=50, verbose_name='아이콘', blank=True)
    is_visible = models.BooleanField(default=True, verbose_name='표시여부')
    order = models.IntegerField(default=0, verbose_name='정렬순서')

    class Meta:
        verbose_name = '메뉴 권한'
        verbose_name_plural = '메뉴 권한 목록'
        ordering = ['role', 'order']
        unique_together = ['role', 'menu_key']

    def __str__(self):
        return f'{self.get_role_display()} - {self.menu_label}'