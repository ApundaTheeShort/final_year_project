import base64
import json
import logging
from datetime import datetime
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone


logger = logging.getLogger(__name__)


class DarajaError(Exception):
    pass


def validate_daraja_configuration():
    missing = [
        name
        for name in (
            "MPESA_CONSUMER_KEY",
            "MPESA_CONSUMER_SECRET",
            "MPESA_SHORTCODE",
            "MPESA_PASSKEY",
            "MPESA_CALLBACK_URL",
        )
        if not getattr(settings, name, "")
    ]
    if missing:
        raise DarajaError("Payment is not available right now. Please try again shortly.")

    callback = urlparse(settings.MPESA_CALLBACK_URL)
    if callback.scheme not in {"http", "https"} or not callback.netloc:
        raise DarajaError("Payment is not available right now. Please try again shortly.")
    if callback.hostname in {"localhost", "127.0.0.1", "0.0.0.0"}:
        raise DarajaError("Payment is not available right now. Please try again shortly.")


def suggested_public_callback_url():
    base_url = (settings.PUBLIC_BASE_URL or "").strip().rstrip("/")
    if not base_url:
        return ""
    return f"{base_url}/api/payments/mpesa/callback/"


def format_kenyan_phone_number(phone_number):
    digits = "".join(char for char in str(phone_number) if char.isdigit())
    if digits.startswith("254") and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 10:
        return f"254{digits[1:]}"
    if digits.startswith("7") and len(digits) == 9:
        return f"254{digits}"
    raise DarajaError("Enter a valid Safaricom phone number.")


def daraja_timestamp():
    return timezone.now().strftime("%Y%m%d%H%M%S")


def daraja_password(timestamp):
    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")


def daraja_base_url():
    if settings.MPESA_ENV == "production":
        return "https://api.safaricom.co.ke"
    return "https://sandbox.safaricom.co.ke"


def mpesa_auth_token():
    validate_daraja_configuration()
    credentials = f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    request = Request(
        f"{daraja_base_url()}/oauth/v1/generate?grant_type=client_credentials",
        headers={"Authorization": f"Basic {encoded}"},
    )
    try:
        with urlopen(request, timeout=settings.MPESA_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        logger.exception("Daraja token request failed")
        if isinstance(exc, HTTPError):
            body = exc.read().decode("utf-8", errors="ignore")
            try:
                error_payload = json.loads(body)
            except json.JSONDecodeError:
                error_payload = {}
            error_message = (
                error_payload.get("errorMessage")
                or error_payload.get("error_description")
                or error_payload.get("message")
            )
            if error_message:
                raise DarajaError("We could not connect to M-Pesa right now. Please try again shortly.") from exc
        raise DarajaError("We could not connect to M-Pesa right now. Please try again shortly.") from exc
    token = payload.get("access_token")
    if not token:
        raise DarajaError("We could not connect to M-Pesa right now. Please try again shortly.")
    return token


def post_daraja_json(path, payload):
    token = mpesa_auth_token()
    request = Request(
        f"{daraja_base_url()}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.MPESA_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        logger.exception("Daraja request failed: %s", body)
        try:
            error_payload = json.loads(body)
        except json.JSONDecodeError:
            error_payload = {}
        error_message = (
            error_payload.get("errorMessage")
            or error_payload.get("ResponseDescription")
            or error_payload.get("responseDescription")
            or error_payload.get("CustomerMessage")
            or error_payload.get("message")
        )
        if error_message:
            raise DarajaError("We could not send the M-Pesa payment prompt right now. Please try again.") from exc
        raise DarajaError("We could not send the M-Pesa payment prompt right now. Please try again.") from exc
    except (URLError, json.JSONDecodeError) as exc:
        logger.exception("Daraja request failed")
        raise DarajaError("We could not send the M-Pesa payment prompt right now. Please try again.") from exc


def parse_mpesa_transaction_date(raw_value):
    if not raw_value:
        return None
    value = str(raw_value)
    try:
        parsed = datetime.strptime(value, "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return timezone.make_aware(parsed, timezone.get_current_timezone())


def parse_callback_payload(payload):
    callback = ((payload or {}).get("Body") or {}).get("stkCallback") or {}
    metadata_items = (((callback.get("CallbackMetadata") or {}).get("Item")) or [])
    metadata = {}
    for item in metadata_items:
        name = item.get("Name")
        if name:
            metadata[name] = item.get("Value")
    return {
        "merchant_request_id": callback.get("MerchantRequestID", ""),
        "checkout_request_id": callback.get("CheckoutRequestID", ""),
        "result_code": callback.get("ResultCode"),
        "result_desc": callback.get("ResultDesc", ""),
        "amount": metadata.get("Amount"),
        "mpesa_receipt_number": metadata.get("MpesaReceiptNumber", ""),
        "transaction_date": parse_mpesa_transaction_date(metadata.get("TransactionDate")),
        "phone_number": str(metadata.get("PhoneNumber", "")) if metadata.get("PhoneNumber") is not None else "",
    }
