import base64
import hmac
import hashlib
import struct
import time
import secrets
import qrcode
from io import BytesIO
from django.conf import settings

# =========================
# CẤU HÌNH TOTP CHUẨN
# =========================
TOTP_TIME_STEP = 30          # mỗi mã sống 30 giây (RFC 6238)
TOTP_DIGITS = 6              # mã 6 số
TOTP_HASH = hashlib.sha1     # HMAC-SHA1 (chuẩn Google Authenticator)


def _int_to_bytes(value: int) -> bytes:
    """
    Chuyển counter (số nguyên) thành 8 byte big-endian.
    Chuẩn HOTP/TOTP yêu cầu như vậy.
    """
    return struct.pack(">Q", value)


def _truncate(hmac_bytes: bytes) -> int:
    """
    Dynamic Truncation theo RFC 4226:
    - Lấy 4 byte từ offset cuối của HMAC
    - Chuyển thành số 31-bit dương
    """
    offset = hmac_bytes[-1] & 0x0F
    four_bytes = hmac_bytes[offset:offset + 4]
    code_int = struct.unpack(">I", four_bytes)[0] & 0x7FFFFFFF
    return code_int


def generate_totp_code(secret_b32: str, for_time: int | None = None) -> str:
    """
    Tạo mã OTP 6 số dựa trên secret base32 và thời gian hiện tại.

    - secret_b32: chuỗi base32 (user.otp_secret trong DB)
    - for_time: cho phép truyền thời gian tùy ý (epoch seconds). Nếu None thì lấy time.time() hiện tại.

    B1. decode base32 secret -> raw key bytes
    B2. tính counter = floor(currentUnixTime / time_step)
    B3. HOTP = Truncate(HMAC-SHA1(key, counter_bytes))
    B4. OTP = HOTP % (10^digits), pad zero bên trái
    """
    if secret_b32 is None:
        raise ValueError("secret_b32 is None")

    # Chuẩn base32 dùng A-Z2-7 không có dấu '=' cuối -> cần padding để decode OK
    # base64.b32decode cho phép casefold=True để chấp nhận thường/hoa.
    key = base64.b32decode(secret_b32.upper() + "=" * ((8 - len(secret_b32) % 8) % 8), casefold=True)

    if for_time is None:
        for_time = int(time.time())

    counter = for_time // TOTP_TIME_STEP
    counter_bytes = _int_to_bytes(counter)

    hmac_bytes = hmac.new(key, counter_bytes, TOTP_HASH).digest()
    code_int = _truncate(hmac_bytes)

    otp_int = code_int % (10 ** TOTP_DIGITS)
    otp_str = str(otp_int).zfill(TOTP_DIGITS)
    return otp_str


def verify_totp(user, code: str, valid_window: int = 1) -> bool:
    """
    Kiểm tra mã OTP do user nhập có hợp lệ không.

    valid_window=1 nghĩa là chấp nhận lệch ±1 bước thời gian (mỗi bước 30s),
    để tránh lệch đồng hồ nhẹ.

    Thuật toán kiểm tra:
    - Lấy current_time = now
    - Sinh mã cho time windows: [now - 30s, now, now + 30s]
    - Nếu code khớp 1 trong các mã -> hợp lệ.
    """
    if not user.otp_secret:
        return False

    try:
        now = int(time.time())
        # duyệt qua các cửa sổ thời gian cho phép lệch
        for offset in range(-valid_window, valid_window + 1):
            test_time = now + (offset * TOTP_TIME_STEP)
            expected = generate_totp_code(user.otp_secret, for_time=test_time)
            if hmac.compare_digest(expected, code.strip()):
                return True
    except Exception:
        return False

    return False


def create_otp_secret() -> str:
    """
    Tạo secret base32 ngẫu nhiên để lưu cho mỗi user.
    - Ta tạo 20 byte random (160-bit), rồi base32 encode.
    - Bỏ dấu '=' padding cuối cho gọn giống Google Authenticator.
    """
    random_bytes = secrets.token_bytes(20)  # 160-bit
    b32 = base64.b32encode(random_bytes).decode("utf-8").strip("=")
    return b32


def build_totp_uri(user) -> str:
    """
    Tạo URI otpauth://totp/... dùng cho Google Authenticator quét QR.
    Format chuẩn:
    otpauth://totp/{ISSUER}:{USERNAME}?secret={SECRET}&issuer={ISSUER}&algorithm=SHA1&digits=6&period=30

    Google Authenticator hiểu format này theo chuẩn TOTP RFC 6238. :contentReference[oaicite:1]{index=1}
    """
    issuer = settings.SITE_NAME
    label = f"{issuer}:{user.username}"
    secret = user.otp_secret

    uri = (
        f"otpauth://totp/{label}"
        f"?secret={secret}"
        f"&issuer={issuer}"
        f"&algorithm=SHA1"
        f"&digits={TOTP_DIGITS}"
        f"&period={TOTP_TIME_STEP}"
    )
    return uri


def qr_code_base64(data: str) -> str:
    """
    Sinh QR code PNG base64 để nhúng vào <img src="data:image/png;base64, ...">
    trong trang enable_2fa.html.
    """
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")
