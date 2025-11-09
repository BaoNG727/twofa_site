from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils import timezone

# Sửa import: Bỏ 'create_otp_secret' từ utils
from .models import User, SecurityPolicy, SecurityLog, BackupCode 
# Sửa import: Lấy 'create_otp_secret' từ 'otp_algo'
from .otp_algo import generate_base32_secret as create_otp_secret


def _log(request, user, event, note=""):
    # ... (giữ nguyên hàm _log) ...
    SecurityLog.objects.create(
        user=user,
        event=event,
        ip=request.META.get("REMOTE_ADDR", ""),
        note=note,
        created_at=timezone.now(),
    )

# ====== ACTIONS TRÊN USER (giữ nguyên) ======

@admin.action(description="Reset OTP secret & buộc bật lại 2FA + ép đổi mật khẩu")
def reset_otp_secret(modeladmin, request, queryset):
    # ... (giữ nguyên action reset_otp_secret) ...
    count = 0
    for user in queryset:
        user.otp_secret = create_otp_secret()
        user.is_2fa_enabled = False
        user.must_setup_2fa = True
        user.failed_otp_attempts = 0
        user.otp_locked = False
        user.must_change_password = True
        user.save()
        
        # Xóa luôn backup codes cũ khi reset OTP
        BackupCode.objects.filter(user=user).delete() 
        
        _log(request, user, "RESET_OTP", note="Admin reset OTP secret + force pw reset")
        count += 1
    messages.success(
        request,
        f"Đã reset OTP cho {count} user. Họ sẽ phải quét QR mới, đổi mật khẩu, và bật lại 2FA."
    )

# ... (giữ nguyên các actions khác: force_require_2fa, disable_require_2fa, disable_2fa, unlock_otp, ...) ...

@admin.action(description="Bật cờ 'bắt buộc 2FA' cho user được chọn (must_setup_2fa=True)")
def force_require_2fa(modeladmin, request, queryset):
    updated = queryset.update(must_setup_2fa=True)
    for u in queryset:
        _log(request, u, "FORCED_2FA", note="must_setup_2fa=True")
    messages.success(
        request,
        f"Đã bật ép buộc 2FA cho {updated} user được chọn."
    )


@admin.action(description="Tắt cờ 'bắt buộc 2FA' cho user được chọn (must_setup_2fa=False)")
def disable_require_2fa(modeladmin, request, queryset):
    updated = queryset.update(must_setup_2fa=False)
    messages.success(
        request,
        f"Đã tắt ép buộc 2FA cho {updated} user được chọn."
    )


@admin.action(description="Vô hiệu hoá 2FA hiện tại (is_2fa_enabled=False)")
def disable_2fa(modeladmin, request, queryset):
    updated = queryset.update(is_2fa_enabled=False)
    messages.success(
        request,
        f"Đã tắt 2FA cho {updated} user được chọn."
    )


@admin.action(description="Mở khoá OTP (otp_locked=False, failed_otp_attempts=0)")
def unlock_otp(modeladmin, request, queryset):
    updated = 0
    for user in queryset:
        user.otp_locked = False
        user.failed_otp_attempts = 0
        user.save()
        _log(request, user, "OTP_LOCKED", note="Admin unlocked OTP manually")
        updated += 1
    messages.success(
        request,
        f"Đã mở khoá OTP cho {updated} user."
    )


@admin.action(description="Ép đổi mật khẩu (must_change_password=True)")
def force_password_reset(modeladmin, request, queryset):
    updated = queryset.update(must_change_password=True)
    for u in queryset:
        _log(request, u, "FORCE_PW_RESET", note="Admin set must_change_password=True")
    messages.success(
        request,
        f"Đã ép {updated} user phải đổi mật khẩu ở lần đăng nhập kế tiếp."
    )


@admin.action(description="Bỏ ép đổi mật khẩu (must_change_password=False)")
def clear_password_reset_flag(modeladmin, request, queryset):
    updated = queryset.update(must_change_password=False)
    messages.success(
        request,
        f"Đã gỡ cờ ép đổi mật khẩu cho {updated} user."
    )


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    # ... (giữ nguyên fieldsets, list_display, list_filter, ...) ...
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Thông tin cá nhân", {"fields": ("first_name", "last_name", "email")}),
        ("Quyền hệ thống", {
            "fields": (
                "role",
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Trạng thái bảo mật / 2FA", {
            "fields": (
                "email_verified",
                "otp_secret",
                "is_2fa_enabled",
                "must_setup_2fa",
                "failed_otp_attempts",
                "otp_locked",
                "must_change_password",
            )
        }),
        ("Dấu thời gian", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "password1",
                "password2",
                "role",
                "is_staff",
                "is_superuser",
                "must_setup_2fa",
            ),
        }),
    )

    list_display = (
        "username",
        "email",
        "role",
        "email_verified",
        "is_2fa_enabled",
        "must_setup_2fa",
        "otp_locked",
        "must_change_password",
        "is_staff",
        "is_superuser",
    )

    list_filter = (
        "role",
        "email_verified",
        "is_2fa_enabled",
        "must_setup_2fa",
        "otp_locked",
        "must_change_password",
        "is_staff",
        "is_superuser",
        "is_active",
    )

    search_fields = ("username", "email")
    ordering = ("username",)

    actions = [
        reset_otp_secret,
        force_require_2fa,
        disable_require_2fa,
        disable_2fa,
        unlock_otp,
        force_password_reset,
        clear_password_reset_flag,
    ]

# ====== ADMIN CHO SECURITYPOLICY (giữ nguyên) ======

@admin.register(SecurityPolicy)
class SecurityPolicyAdmin(admin.ModelAdmin):
    # ... (giữ nguyên) ...
    list_display = ("require_2fa_for_new_users", "updated_at")

    actions = ["force_all_users_require_2fa", "disable_all_users_require_2fa"]

    @admin.action(description="Ép TOÀN BỘ user phải bật lại 2FA (must_setup_2fa=True)")
    def force_all_users_require_2fa(self, request, queryset):
        updated = User.objects.update(must_setup_2fa=True)
        for u in User.objects.all():
            _log(request, u, "FORCED_2FA", note="Global force via SecurityPolicy")
        messages.success(
            request,
            f"Đã ép {updated} user phải bật 2FA. Lần đăng nhập tới ai chưa bật sẽ bị bắt quét OTP."
        )

    @admin.action(description="Bỏ ép buộc 2FA cho TOÀN BỘ user (must_setup_2fa=False)")
    def disable_all_users_require_2fa(self, request, queryset):
        updated = User.objects.update(must_setup_2fa=False)
        messages.success(
            request,
            f"Đã bỏ ép buộc 2FA cho {updated} user."
        )

# ====== ADMIN CHO SECURITYLOG (read-only, giữ nguyên) ======

@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    # ... (giữ nguyên) ...
    list_display = ("created_at", "user", "event", "ip", "note")
    list_filter = ("event", "user")
    search_fields = ("user__username", "ip", "note")
    ordering = ("-created_at",)
    readonly_fields = ("user", "event", "ip", "note", "created_at")

    def has_add_permission(self, request):
        return False  # không cho tạo tay
    def has_change_permission(self, request, obj=None):
        return False  # không cho sửa tay

# ----------------------------------
# TẠO ADMIN MỚI CHO MÃ KHÔI PHỤC
# ----------------------------------
@admin.register(BackupCode)
class BackupCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "is_used", "created_at")
    list_filter = ("is_used", "user")
    search_fields = ("user__username",)
    ordering = ("-created_at",)
    readonly_fields = ("user", "code_hash", "is_used", "created_at")

    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False