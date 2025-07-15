from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, AccountType, BankAccount, TransactionCategory, 
    Transaction
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Override default ordering (username removed)
    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'phone_number', 'nin', 'is_verified', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_verified', 'date_joined')
    search_fields = ('first_name', 'last_name', 'email', 'phone_number', 'nin')
    readonly_fields = ('date_joined', 'last_login', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "date_of_birth", "phone_number", "address", "occupation", "nin")}),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
        }),
        ("Security", {"fields": ("public_key", "transaction_pin_hash", "is_verified")}),
        ("Important dates", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "phone_number", "nin", "password", "password2"),
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
    search_fields = ('account_number', 'user__email')
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
