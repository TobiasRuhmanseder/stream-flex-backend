from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ("email", "is_staff", "is_active")
    list_filter  = ("is_staff", "is_active")
    ordering     = ("email",)
    search_fields = ("email",)

    fieldsets = (
        (None,               {"fields": ("email", "password")}),
        ("Permissions",      {"fields": ("is_staff", "is_active", "groups", "user_permissions")}),
        ("Important dates",  {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_active"),
        }),
    )
