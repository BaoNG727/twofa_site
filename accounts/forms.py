from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User


class RegisterForm(forms.ModelForm):
    # ... (giữ nguyên form RegisterForm) ...
    password1 = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Mật khẩu"
        })
    )
    password2 = forms.CharField(
        label="Nhập lại mật khẩu",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Nhập lại mật khẩu"
        })
    )

    class Meta:
        model = User
        fields = ["username", "email"]
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Tên đăng nhập"
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-input",
                "placeholder": "Email"
            }),
        }

    def clean_password2(self):
        pw1 = self.cleaned_data.get("password1")
        pw2 = self.cleaned_data.get("password2")
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError("Hai mật khẩu không khớp.")
        # validate độ mạnh mật khẩu (Django built-in rules)
        validate_password(pw1)
        return pw2
    
    # ... (giữ nguyên phần còn lại của RegisterForm) ...
    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data["password1"]
        user.set_password(pw)
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    # ... (giữ nguyên form LoginForm) ...
    username = forms.CharField(
        label="Tên đăng nhập",
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Username"
        })
    )
    password = forms.CharField(
        label="Mật khẩu",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Mật khẩu"
        })
    )

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get("username")
        password = cleaned.get("password")

        if not username or not password:
            return cleaned

        user = authenticate(username=username, password=password)
        if user is None:
            raise forms.ValidationError("Sai tài khoản hoặc mật khẩu.")

        # chặn đăng nhập nếu email chưa verify
        if not user.email_verified:
            raise forms.ValidationError("Email chưa được xác thực. Vui lòng kiểm tra hộp thư.")

        if not user.is_active:
            raise forms.ValidationError("Tài khoản đã bị vô hiệu hoá.")

        cleaned["user"] = user
        return cleaned


class OTPForm(forms.Form):
    """
    Form nhập mã OTP 6 số (từ app hoặc email)
    """
    otp_code = forms.CharField(
        label="Mã OTP",
        max_length=8, # Tăng lên 8 để chấp nhận cả mã khôi phục (nếu gộp)
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Nhập mã OTP 6 số"
        })
    )
    
    # THÊM TRƯỜNG MỚI
    remember_me = forms.BooleanField(
        label="Tin cậy thiết bị này trong 30 ngày",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )


class Enable2FAConfirmForm(forms.Form):
    # ... (giữ nguyên form Enable2FAConfirmForm) ...
    otp_code = forms.CharField(
        label="Mã OTP",
        max_length=6,
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "Nhập mã OTP từ ứng dụng Authenticator"
        })
    )


class ChangePasswordForm(forms.Form):
    # ... (giữ nguyên form ChangePasswordForm) ...
    old_password = forms.CharField(
        label="Mật khẩu hiện tại",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Mật khẩu hiện tại"
        })
    )
    new_password1 = forms.CharField(
        label="Mật khẩu mới",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Mật khẩu mới"
        })
    )
    new_password2 = forms.CharField(
        label="Nhập lại mật khẩu mới",
        widget=forms.PasswordInput(attrs={
            "class": "form-input",
            "placeholder": "Nhập lại mật khẩu mới"
        })
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_old_password(self):
        old = self.cleaned_data["old_password"]
        if not self.user.check_password(old):
            raise forms.ValidationError("Mật khẩu hiện tại không đúng.")
        return old

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get("new_password1")
        pw2 = cleaned.get("new_password2")

        if pw1 and pw2 and pw1 != pw2:
            self.add_error("new_password2", "Hai mật khẩu mới không khớp.")

        # kiểm tra độ mạnh mật khẩu mới
        if pw1:
            validate_password(pw1, user=self.user)

        return cleaned
        
    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Email đã tồn tại trong hệ thống.")
        return email

# ----------------------------------
# TẠO FORM MỚI CHO MÃ KHÔI PHỤC
# ----------------------------------
class BackupCodeForm(forms.Form):
    """
    Form nhập mã khôi phục (backup code)
    """
    code = forms.CharField(
        label="Mã khôi phục",
        widget=forms.TextInput(attrs={
            "class": "form-input",
            "placeholder": "VD: abcd-1234"
        })
    )
    
    remember_me = forms.BooleanField(
        label="Tin cậy thiết bị này trong 30 ngày",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )