from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Transaction
)



# @admin.register(AccountType)
# class AccountTypeAdmin(admin.ModelAdmin):
#     list_display = ('name', 'minimum_balance', 'interest_rate', 'monthly_fee', 'transaction_limit_daily', 'is_active')
#     list_filter = ('is_active', 'created_at')
#     search_fields = ('name', 'description')
#     readonly_fields = ('created_at',)


# @admin.register(BankAccount)
# class BankAccountAdmin(admin.ModelAdmin):
#     list_display = ('account_number', 'user', 'balance', 'status', 'is_primary', 'created_at')
#     list_filter = ('status',  'is_primary', 'created_at')
#     search_fields = ('account_number', 'user__email')
#     readonly_fields = ('id', 'account_number', 'created_at', 'updated_at')
#     raw_id_fields = ('user',)


# @admin.register(TransactionCategory)
# class TransactionCategoryAdmin(admin.ModelAdmin):
#     list_display = ('name', 'description', 'is_active', 'created_at')
#     list_filter = ('is_active', 'created_at')
#     search_fields = ('name', 'description')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'account', 'transaction_type', 'amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('reference_number', 'account__account_number', 'description', 'recipient_account_number')
    readonly_fields = ('id', 'reference_number', 'created_at', 'updated_at')
    raw_id_fields = ('account',)
    date_hierarchy = 'created_at'
