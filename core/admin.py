from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, AccountType, BankAccount, TransactionCategory, 
    Transaction, Beneficiary, Card, AuditLog
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'is_verified', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_verified', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')
    readonly_fields = ('date_joined', 'last_login', 'created_at', 'updated_at')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'date_of_birth', 'address', 'national_id', 'is_verified', 'two_factor_enabled')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(AccountType)
class AccountTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'minimum_balance', 'interest_rate', 'monthly_fee', 'transaction_limit_daily', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'user', 'account_type', 'balance', 'status', 'is_primary', 'created_at')
    list_filter = ('status', 'account_type', 'is_primary', 'created_at')
    search_fields = ('account_number', 'user__username', 'user__email')
    readonly_fields = ('id', 'account_number', 'created_at', 'updated_at')
    raw_id_fields = ('user',)


@admin.register(TransactionCategory)
class TransactionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'account', 'transaction_type', 'amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'category', 'created_at')
    search_fields = ('reference_number', 'account__account_number', 'description', 'recipient_account_number')
    readonly_fields = ('id', 'reference_number', 'created_at', 'updated_at')
    raw_id_fields = ('account',)
    date_hierarchy = 'created_at'


@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ('account_name', 'user', 'account_number', 'bank_name', 'is_active', 'created_at')
    list_filter = ('bank_name', 'is_active', 'created_at')
    search_fields = ('account_name', 'account_number', 'user__username', 'nickname')
    raw_id_fields = ('user',)


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('cardholder_name', 'card_type', 'status', 'expiry_date', 'daily_limit', 'created_at')
    list_filter = ('card_type', 'status', 'expiry_date', 'created_at')
    search_fields = ('cardholder_name', 'account__account_number', 'account__user__username')
    readonly_fields = ('id', 'card_number', 'cvv', 'pin', 'created_at', 'updated_at')
    raw_id_fields = ('account',)

    def masked_card_number(self, obj):
        return f"****{obj.card_number[-4:]}" if obj.card_number else "No card number"
    masked_card_number.short_description = "Card Number"

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj:  # Editing existing object
            readonly_fields.extend(['card_number', 'cvv', 'pin'])
        return readonly_fields


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_type', 'description', 'ip_address', 'created_at')
    list_filter = ('action_type', 'created_at')
    search_fields = ('user__username', 'description', 'ip_address')
    readonly_fields = ('id', 'created_at')
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False  # Audit logs should not be manually created

    def has_change_permission(self, request, obj=None):
        return False  # Audit logs should not be modified
