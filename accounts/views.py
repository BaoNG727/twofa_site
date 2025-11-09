from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from datetime import timedelta # Thêm import

from .models import User, SecurityPolicy, SecurityLog, SecurityConfig
# Sửa import: Thêm BackupCodeForm
from .forms import (
    RegisterForm, LoginForm, OTPForm, Enable2FAConfirmForm, 
    ChangePasswordForm, BackupCodeForm
)
from .tokens import email_verification_token
# Sửa import: Bỏ qr_code_base64 từ utils
from .otp_algo import (
    generate_base32_secret, provisioning_uri, verify_totp,
    qr_code_base64 # Lấy qr_code_base64 từ đây
)

# Thêm các import cần thiết
import time
import secrets
import hmac


def _log_event(user, event, request=None, note=""):
    # ... (giữ nguyên hàm _log_event) ...
    SecurityLog.objects.create(
        user=user,
        event=event,
        ip=(request.META.get("REMOTE_ADDR", "") if request else ""),
        note=note,
        created_at=timezone.now(),
    )

# --- Hàm trợ giúp cho session -----------------
def _set_session_expiry(request, remember_me: bool):
    """Đặt thời hạn session: 0 (đóng browser) hoặc 30 ngày."""
    if remember_me:
        # Lấy từ settings, nếu không có thì 30 ngày
        expiry_seconds = getattr(settings, "SESSION_COOKIE_AGE", 2592000)
        request.session.set_expiry(expiry_seconds)
        request.session['2fa_trusted'] = True
    else:
        request.session.set_expiry(0) # Hết hạn khi đóng browser
        request.session.pop('2fa_trusted', None)

def _perform_login(request, user, remember_me: bool):
    """
    Hàm trợ giúp: Đặt session expiry VÀ login user.
    """
    _set_session_expiry(request, remember_me)
    login(request, user)
    request.session.pop("pre_2fa_user_id", None)
    
    if user.must_setup_2fa and not user.is_2fa_enabled:
        return redirect("accounts:enable_2fa")
    if user.must_change_password:
        return redirect("accounts:change_password")
    return redirect("accounts:dashboard")
# -----------------------------------------------


def send_activation_email(request, user):
    # ... (giữ nguyên hàm send_activation_email) ...
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    domain = (getattr(settings, "SITE_DOMAIN", "") or "").rstrip("/") or f"http://{request.get_host()}"
    activate_url = f"{domain}{reverse('accounts:activate', kwargs={'uidb64': uidb64, 'token': token})}"

    subject = f"Kích hoạt tài khoản - {getattr(settings, 'SITE_NAME', 'TwoFA Demo')}"
    message = (
        f"Xin chào {user.username},\n\n"
        f"Bạn vừa đăng ký tài khoản. Hãy nhấp liên kết sau để kích hoạt:\n{activate_url}\n\n"
        f"Nếu không phải bạn, vui lòng bỏ qua email này."
    )
    send_mail(subject, message, getattr(settings, "DEFAULT_FROM_EMAIL", None), [user.email], fail_silently=False)


def activate_email_view(request, uidb64, token):
    # ... (giữ nguyên hàm activate_email_view) ...
    UserModel = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = UserModel.objects.get(pk=uid)
    except Exception:
        user = None

    if user and email_verification_token.check_token(user, token):
        user.is_active = True
        if hasattr(user, "email_verified"):
            user.email_verified = True
        user.save()
        messages.success(request, "Kích hoạt tài khoản thành công. Vui lòng đăng nhập.")
        return redirect("accounts:login")
    else:
        messages.error(request, "Liên kết kích hoạt không hợp lệ hoặc đã hết hạn.")
        return redirect("accounts:register")


def register_view(request):
    # ... (giữ nguyên hàm register_view) ...
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email_verified = False
            user.role = "USER"
            user.is_active = False  # bắt buộc kích hoạt qua email

            # Áp dụng SecurityPolicy nếu có (không làm app crash nếu model/DB chưa sẵn)
            must_setup_2fa = True
            try:
                policy = SecurityPolicy.objects.first()
                if policy:
                    must_setup_2fa = bool(getattr(policy, "require_2fa_for_new_users", True))
            except Exception:
                pass
            user.must_setup_2fa = must_setup_2fa

            user.save()

            # Gửi email kích hoạt
            try:
                send_activation_email(request, user)
            except Exception as e:
                messages.warning(request, f"Đăng ký thành công, nhưng gửi mail kích hoạt lỗi: {e}")

            messages.success(request, "Đăng ký thành công! Vui lòng kiểm tra email để kích hoạt tài khoản.")
            return redirect("accounts:login")

        return render(request, "accounts/register.html", {"form": form})

    form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    """
    Bước 1: đăng nhập bằng mật khẩu.
    - Sửa đổi: Kiểm tra '2fa_trusted' session.
    """
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data["user"]

            config = SecurityPolicy.objects.first()
            enforce_all = bool(getattr(config, "enforce_2fa_all", False))
            if user.is_staff or user.is_superuser:
                enforce_all = True

            # KIỂM TRA 2FA
            if user.is_2fa_enabled:
                
                # SỬA ĐỔI: Kiểm tra "Tin cậy thiết bị"
                # Nếu session '2fa_trusted' = True, user đã xác thực 2FA trên
                # trình duyệt này và session chưa hết hạn. Bỏ qua bước OTP.
                if request.session.get('2fa_trusted', False):
                    # Phải login() lại để làm mới session, nhưng
                    # _set_session_expiry sẽ giữ nguyên expiry cũ
                    remember_me = True # Giữ nguyên tin cậy
                    _log_event(user, "LOGIN_SUCCESS", request=request, note="Login success (Trusted Device)")
                    return _perform_login(request, user, remember_me)

                # Nếu không tin cậy, chuyển sang bước OTP
                request.session["pre_2fa_user_id"] = user.id
                return redirect("accounts:otp_verify")

            # --- Login không 2FA ---
            # Login tạm nếu cần ép enable-2fa (remember_me=False)
            remember_me = False # Mặc định không tin cậy nếu không có 2FA
            _log_event(user, "LOGIN_SUCCESS", request=request, note="Login without 2FA yet")
            
            # _perform_login đã bao gồm login() và các redirect
            return _perform_login(request, user, remember_me)
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def otp_verify_view(request):
    """
    Bước 2: nhập OTP
    - Sửa đổi: Chấp nhận cả TOTP (app) và Email OTP (session).
    - Sửa đổi: Xử lý "Tin cậy thiết bị".
    - Sửa đổi: Đọc lockout_threshold từ SecurityConfig.
    """
    user_id = request.session.get("pre_2fa_user_id")
    if not user_id:
        return redirect("accounts:login")

    user = get_object_or_404(User, pk=user_id)
    config = SecurityConfig.get_solo()
    
    if user.otp_locked:
        _log_event(user, "OTP_LOCKED", request=request, note="User tried while locked")
        return render(
            request,
            "accounts/otp_verify.html",
            {
                "form": OTPForm(),
                "username": user.username,
                "locked": True,
                "error": f"Tài khoản đã bị khóa OTP do nhập sai quá {config.lockout_threshold} lần. Liên hệ admin."
            },
            status=403,
        )

    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["otp_code"].strip().replace(" ", "")
            remember_me = form.cleaned_data.get("remember_me", False)
            
            totp_ok = False
            email_ok = False

            # 1. Kiểm tra mã TOTP (từ app)
            if user.otp_secret:
                totp_ok = verify_totp(user.otp_secret, code, period=30, digits=6, algo="SHA1", window=1)

            # 2. Kiểm tra mã Email OTP (từ session)
            email_otp_code = request.session.get('email_otp_code')
            email_otp_expiry = request.session.get('email_otp_expiry', 0)
            
            if email_otp_code and hmac.compare_digest(code, email_otp_code) and time.time() < email_otp_expiry:
                email_ok = True
                # Xóa mã email OTP sau khi dùng
                request.session.pop('email_otp_code', None)
                request.session.pop('email_otp_expiry', None)

            # 3. Xử lý kết quả
            if totp_ok or email_ok:
                user.failed_otp_attempts = 0
                user.otp_locked = False
                user.save()

                note = "OTP (TOTP) ok" if totp_ok else "OTP (Email) ok"
                _log_event(user, "OTP_SUCCESS", request=request, note=f"{note}, full login")

                # Đăng nhập và xử lý session tin cậy
                return _perform_login(request, user, remember_me)
            else:
                # Cả 2 đều sai -> Thất bại
                user.failed_otp_attempts += 1
                note_msg = f"OTP failed attempt {user.failed_otp_attempts}"
                
                # SỬA ĐỔI: Dùng config.lockout_threshold
                if user.failed_otp_attempts >= config.lockout_threshold: 
                    user.otp_locked = True
                    note_msg += " -> LOCKED"
                user.save()
                _log_event(user, "OTP_FAIL", request=request, note=note_msg)
                form.add_error("otp_code", "Mã OTP không hợp lệ hoặc đã hết hạn.")
    else:
        form = OTPForm()

    return render(
        request, 
        "accounts/otp_verify.html", 
        {
            "form": form, 
            "username": user.username,
            "lockout_threshold": config.lockout_threshold
        }
    )

# ----------------------------------
# TẠO VIEW MỚI
# ----------------------------------
def send_email_otp_view(request):
    """
    View này chỉ xử lý gửi Email OTP và redirect về 'otp_verify'.
    """
    user_id = request.session.get("pre_2fa_user_id")
    if not user_id:
        return redirect("accounts:login")
    
    user = get_object_or_404(User, pk=user_id)

    # Throttling: Chặn spam email, 60s 1 lần
    last_sent = request.session.get('last_email_otp_sent', 0)
    if time.time() - last_sent < 60:
        messages.warning(request, "Vui lòng đợi 60 giây trước khi gửi lại mã.")
        return redirect("accounts:otp_verify")

    # Tạo mã 6 số
    code = str(secrets.randbelow(900000) + 100000)
    
    # Lưu vào session (hết hạn 5 phút)
    request.session['email_otp_code'] = code
    request.session['email_otp_expiry'] = int(time.time()) + 300 # 5 phút
    request.session['last_email_otp_sent'] = int(time.time())

    # Gửi email
    try:
        subject = f"Mã xác thực 2FA - {getattr(settings, 'SITE_NAME', 'TwoFA Demo')}"
        message = (
            f"Mã xác thực 2FA của bạn là: {code}\n\n"
            f"Mã này có hiệu lực trong 5 phút.\n"
        )
        send_mail(subject, message, getattr(settings, "DEFAULT_FROM_EMAIL", None), [user.email], fail_silently=False)
        
        _log_event(user, "EMAIL_OTP_SENT", request=request)
        messages.success(request, f"Đã gửi mã OTP đến email {user.email}.")
    except Exception as e:
        messages.error(request, f"Lỗi khi gửi email: {e}")

    return redirect("accounts:otp_verify")

# ----------------------------------
# TẠO VIEW MỚI
# ----------------------------------
def backup_code_verify_view(request):
    """
    Bước 2 (thay thế): Đăng nhập bằng mã khôi phục.
    """
    user_id = request.session.get("pre_2fa_user_id")
    if not user_id:
        return redirect("accounts:login")

    user = get_object_or_404(User, pk=user_id)
    config = SecurityConfig.get_solo()

    if user.otp_locked:
        # Vẫn áp dụng khóa OTP chung
        return render(
            request, "accounts/backup_code_verify.html",
            {
                "form": BackupCodeForm(), "username": user.username, "locked": True,
                "error": f"Tài khoản đã bị khóa OTP do nhập sai quá {config.lockout_threshold} lần. Liên hệ admin."
            }, status=403,
        )

    if request.method == "POST":
        form = BackupCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()
            remember_me = form.cleaned_data.get("remember_me", False)

            # Kiểm tra mã khôi phục (hàm này tự động đánh dấu đã dùng)
            if user.verify_backup_code(code):
                # Thành công -> reset bộ đếm sai
                user.failed_otp_attempts = 0
                user.otp_locked = False
                user.save()
                
                _log_event(user, "BACKUP_CODE_USED", request=request, note="Login success (Backup Code)")

                # Đăng nhập và xử lý session tin cậy
                return _perform_login(request, user, remember_me)
            else:
                # Thất bại -> Tăng bộ đếm sai
                user.failed_otp_attempts += 1
                note_msg = f"Backup code failed attempt {user.failed_otp_attempts}"
                
                if user.failed_otp_attempts >= config.lockout_threshold:
                    user.otp_locked = True
                    note_msg += " -> LOCKED"
                user.save()
                _log_event(user, "OTP_FAIL", request=request, note=note_msg)
                form.add_error("code", "Mã khôi phục không hợp lệ hoặc đã được sử dụng.")
    else:
        form = BackupCodeForm()

    return render(
        request, 
        "accounts/backup_code_verify.html", 
        {"form": form, "username": user.username}
    )


@login_required
def enable_2fa_view(request):
    user = request.user

    if not user.otp_secret:
        user.otp_secret = generate_base32_secret()
        user.save()

    otp_uri = provisioning_uri(
        # ... (giữ nguyên logic tạo otp_uri) ...
        account_name=user.username,
        issuer_name=getattr(settings, "SITE_NAME", "TwoFA Demo"),
        secret_b32=user.otp_secret,
        algo="SHA1",
        digits=6,
        period=30,
    )
    qr_b64 = qr_code_base64(otp_uri)

    if request.method == "POST":
        form = OTPForm(request.POST) # Dùng OTPForm (không cần remember_me ở đây)
        if form.is_valid():
            code = form.cleaned_data["otp_code"]
            ok = verify_totp(user.otp_secret, code, period=30, digits=6, algo="SHA1", window=1)
            
            if ok:
                user.is_2fa_enabled = True
                user.failed_otp_attempts = 0
                user.otp_locked = False
                user.must_setup_2fa = False
                user.save()
                
                # TẠO MÃ KHÔI PHỤC
                plaintext_codes = user.generate_backup_codes()
                # Lưu mã vào session để trang kế tiếp hiển thị
                request.session['backup_codes'] = plaintext_codes 

                return redirect("accounts:enable_2fa_complete") # Chuyển đến trang hiển thị mã
            else:
                form.add_error("otp_code", "Mã OTP không hợp lệ.")
    else:
        form = OTPForm()

    return render(
        request,
        "accounts/enable_2fa.html",
        {
            # ... (giữ nguyên context) ...
            "form": form,
            "qr_b64": qr_b64,
            "otp_uri": otp_uri,
            "is_enabled": user.is_2fa_enabled,
            "secret_key": user.otp_secret,
            "issuer": getattr(settings, "SITE_NAME", "TwoFA Demo"),
            "account_name": user.username,
            "digits": 6,
            "period": 30,
            "algo": "SHA1",
        },
    )

# ----------------------------------
# TẠO VIEW MỚI
# ----------------------------------
@login_required
def enable_2fa_complete_view(request):
    """
    Hiển thị mã khôi phục 1 LẦN DUY NHẤT sau khi bật 2FA.
    """
    backup_codes = request.session.pop('backup_codes', None)
    if not backup_codes:
        # Nếu user F5 lại trang hoặc vào thẳng, chỉ redirect
        return redirect("accounts:dashboard")
    
    return render(
        request, 
        "accounts/enable_2fa_complete.html",
        {"backup_codes": backup_codes}
    )


@login_required
def change_password_view(request):
    # ... (giữ nguyên hàm change_password_view) ...
    user = request.user
    if request.method == "POST":
        form = ChangePasswordForm(user, request.POST)
        if form.is_valid():
            new_pw = form.cleaned_data["new_password1"]
            user.set_password(new_pw)
            user.must_change_password = False
            user.save()
            login(request, user) # Đăng nhập lại để session mới
            return redirect("accounts:dashboard")
    else:
        form = ChangePasswordForm(user)
    return render(request, "accounts/change_password.html", {"form": form})


@login_required
def dashboard_view(request):
    # ... (giữ nguyên hàm dashboard_view) ...
    u = request.user
    if u.must_setup_2fa and not u.is_2fa_enabled:
        return redirect("accounts:enable_2fa")
    if u.must_change_password:
        return redirect("accounts:change_password")

    security_info = {
        "email_verified": u.email_verified,
        "is_2fa_enabled": u.is_2fa_enabled,
        "must_setup_2fa": u.must_setup_2fa,
        "otp_locked": u.otp_locked,
        "failed_otp_attempts": u.failed_otp_attempts,
        "must_change_password": u.must_change_password,
        "last_login": u.last_login,
    }
    return render(request, "accounts/dashboard.html", {"security_info": security_info})


def logout_view(request):
    # SỬA ĐỔI: Xóa session tin cậy khi logout
    request.session.pop('2fa_trusted', None)
    logout(request)
    return redirect("forum:home")


@login_required
def staff_only_view(request):
    # ... (giữ nguyên hàm staff_only_view) ...
    if not request.user.is_staff_role():
        return HttpResponseForbidden("Bạn không có quyền STAFF.")
    return render(request, "accounts/dashboard.html", {"staff": True})