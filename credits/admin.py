from django.contrib import admin
from .models import CreditPackage, UserCredit, CreditTransaction, Payment


@admin.register(CreditPackage)
class CreditPackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'credits', 'price', 'price_per_credit', 'is_active', 'order']
    list_editable = ['is_active', 'order']


@admin.register(UserCredit)
class UserCreditAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'free_used_this_month', 'updated_at']
    search_fields = ['user__username']


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'amount', 'balance_after', 'created_at']
    list_filter = ['transaction_type']
    readonly_fields = ['created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'package', 'amount', 'credits', 'status', 'created_at']
    list_filter = ['status']
    readonly_fields = ['created_at', 'paid_at']