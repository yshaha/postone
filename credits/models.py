from django.db import models
from accounts.models import User


class CreditPackage(models.Model):
    PLAN_CHOICES = [
        ('free', '무료'),
        ('starter', '스타터'),
        ('pro', '프로'),
        ('business', '비즈니스'),
    ]

    name = models.CharField(max_length=50, verbose_name='패키지명')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='starter')
    credits = models.IntegerField(verbose_name='크레딧 수')
    price = models.IntegerField(verbose_name='가격(원)')
    is_auto_publish = models.BooleanField(default=False, verbose_name='자동발행 가능')
    is_analytics = models.BooleanField(default=False, verbose_name='분석데이터 가능')
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name = '크레딧 패키지'
        verbose_name_plural = '크레딧 패키지 목록'
        ordering = ['order']

    def __str__(self):
        return f'{self.name} ({self.credits}개 / {self.price:,}원)'

    @property
    def price_per_credit(self):
        return round(self.price / self.credits)


class UserCredit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='credit')
    balance = models.IntegerField(default=0, verbose_name='잔여 크레딧')
    free_used_this_month = models.IntegerField(default=0, verbose_name='이번달 무료 사용')
    free_reset_date = models.DateField(null=True, blank=True, verbose_name='무료 초기화일')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '사용자 크레딧'

    def __str__(self):
        return f'{self.user.username} - {self.balance}개'


class CreditTransaction(models.Model):
    TYPE_CHOICES = [
        ('charge', '충전'),
        ('use', '사용'),
        ('free', '무료사용'),
        ('admin_grant', '관리자지급'),
        ('refund', '환불'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_transactions')
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.IntegerField(verbose_name='크레딧 수량')
    balance_after = models.IntegerField(verbose_name='거래 후 잔액')
    description = models.CharField(max_length=200, blank=True)
    related_request = models.ForeignKey(
        'content.ContentRequest', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '크레딧 거래내역'
        verbose_name_plural = '크레딧 거래내역 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.get_transaction_type_display()} {self.amount}개'


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', '결제대기'),
        ('paid', '결제완료'),
        ('failed', '결제실패'),
        ('refunded', '환불'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    package = models.ForeignKey(CreditPackage, on_delete=models.SET_NULL, null=True)
    order_id = models.CharField(max_length=100, unique=True, verbose_name='주문번호')
    amount = models.IntegerField(verbose_name='결제금액')
    credits = models.IntegerField(verbose_name='충전 크레딧')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    portone_payment_id = models.CharField(max_length=200, blank=True, verbose_name='포트원 결제ID')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = '결제내역'
        verbose_name_plural = '결제내역 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.amount:,}원 - {self.get_status_display()}'