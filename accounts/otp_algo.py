# accounts/otp_algo.py
# HOTP/TOTP thuần Python theo RFC 4226 & RFC 6238 (SHA-1, 6 digits, period=30)

import hmac, hashlib, struct, time, base64, secrets
from urllib.parse import quote

# Thêm 2 import này
import qrcode
from io import BytesIO

# ---- Secret (Base32) ----
def generate_base32_secret(nbytes: int = 20) -> str:
    # ... (giữ nguyên hàm) ...
    raw = secrets.token_bytes(nbytes)
    b32 = base64.b32encode(raw).decode("ascii")
    return b32.strip("=").upper()

def _b32decode(secret_b32: str) -> bytes:
    # ... (giữ nguyên hàm) ...
    s = secret_b32.strip().replace(" ", "").upper()
    pad = (-len(s)) % 8
    s += "=" * pad
    return base64.b32decode(s, casefold=True)

# ---- HOTP ----
def hotp(secret_b32: str, counter: int, digits: int = 6, algo: str = "SHA1") -> str:
    # ... (giữ nguyên hàm) ...
    key = _b32decode(secret_b32)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, getattr(hashlib, algo.lower())).digest()
    o = h[-1] & 0x0F
    code = ((h[o] & 0x7F) << 24) | (h[o+1] << 16) | (h[o+2] << 8) | (h[o+3])
    code = code % (10 ** digits)
    return str(code).zfill(digits)

# ---- TOTP ----
def totp(secret_b32: str, for_time: int | None = None,
         period: int = 30, digits: int = 6, algo: str = "SHA1") -> str:
    # ... (giữ nguyên hàm) ...
    if for_time is None:
        for_time = int(time.time())
    counter = int((for_time) // period)
    return hotp(secret_b32, counter, digits=digits, algo=algo)

def verify_totp(secret_b32: str, code_str: str, period: int = 30,
                digits: int = 6, algo: str = "SHA1", window: int = 1,
                now: int | None = None) -> bool:
    # ... (giữ nguyên hàm) ...
    code = (code_str or "").strip().replace(" ", "")
    if not (code.isdigit() and len(code) == digits):
        return False
    if now is None:
        now = int(time.time())
    t = now // period
    for w in range(-window, window + 1):
        if hotp(secret_b32, t + w, digits=digits, algo=algo) == code:
            return True
    return False

# ---- otpauth URI (để import vào Authenticator) ----
def provisioning_uri(account_name: str, issuer_name: str, secret_b32: str,
                     algo: str = "SHA1", digits: int = 6, period: int = 30) -> str:
    # ... (giữ nguyên hàm) ...
    label = f"{issuer_name}:{account_name}"
    params = (
        f"secret={secret_b32}"
        f"&issuer={quote(issuer_name)}"
        f"&algorithm={algo}"
        f"&digits={digits}"
        f"&period={period}"
    )
    return f"otpauth://totp/{quote(label)}?{params}"

# ----------------------------------
# THÊM HÀM MỚI TỪ UTILS.PY CŨ
# ----------------------------------
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