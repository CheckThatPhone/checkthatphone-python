"""Official Python client for the CheckThatPhone API.

https://checkthatphone.com/docs

Zero dependencies — standard library only. Python 3.9+.
"""

from __future__ import annotations

import json
import urllib.error
import warnings
import urllib.request
from typing import Any, Optional

__version__ = "0.2.0"
__all__ = ["CheckThatPhone", "CheckThatPhoneError", "LookupResult"]

_DEFAULT_BASE_URL = "https://api.checkthatphone.com"


class CheckThatPhoneError(Exception):
    """Raised for non-2xx API responses.

    Attributes:
        status: HTTP status (400 invalid input, 401 bad key, 402 quota,
            429 rate limit, 502 upstream).
        code: machine-readable error string from the API.
        detail: human-readable detail, when the API provides one.
    """

    def __init__(self, status: int, code: str, detail: Optional[str] = None):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.status = status
        self.code = code
        self.detail = detail

    @property
    def retryable(self) -> bool:
        """True when retrying the identical request may succeed."""
        return self.status == 429 or self.status >= 500


class LookupResult:
    """Envelope for one lookup.

    Attributes:
        success: whether the lookup succeeded.
        credits_used: credits this call drew from your plan.
        data: response fields (string-valued; add-on fields present only when
            the matching flag was sent). Full reference:
            https://checkthatphone.com/docs
    """

    def __init__(self, success: bool, credits_used: int, data: dict[str, Any]):
        self.success = success
        self.credits_used = credits_used
        self.data = data

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"LookupResult(success={self.success}, credits_used={self.credits_used}, "
            f"data_keys={sorted(self.data)!r})"
        )


class CheckThatPhone:
    """CheckThatPhone API client.

    Usage::

        from checkthatphone import CheckThatPhone

        client = CheckThatPhone(api_key="ctp_live_...")
        result = client.lookup("8182925409", litigator_filter=True, dnc_state=True)
        if result.data.get("litigator") == "true":
            ...
    """

    def __init__(self, api_key: str, *, base_url: str = _DEFAULT_BASE_URL, timeout: float = 15.0):
        if not api_key or not isinstance(api_key, str):
            raise ValueError(
                "api_key is required — create one at https://checkthatphone.com/dashboard/keys"
            )
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def lookup(
        self,
        phone: str,
        *,
        ip: Optional[str] = None,
        litigator_filter: bool = False,
        landline_sms_lookup: bool = False,
        dnc_state: bool = False,
        dnc_complainer: bool = False,
        dnc_other: bool = False,
    ) -> LookupResult:
        """Validate one US/Canada phone number.

        Args:
            phone: 10-digit number (11-digit with leading 1 also accepted);
                non-digits are ignored, so "(818) 292-5409" is fine.
            ip: IPv4/IPv6 of the number's owner — enables precise GeoIP
                and timezone data.
            litigator_filter: TCPA litigator scrub (+1 credit).
            landline_sms_lookup: landline SMS reachability (+1 credit,
                charged only when the number is a landline).
            dnc_state: state do-not-call registry check (free; 38 states
                plus DC). Adds ``dncStateChecked`` and ``dncStateResult``;
                both are absent for the 12 states with no registry data, so
                absent means not checked, never clear.
            dnc_complainer: national complainer-list check (free). Adds
                ``dncComplainerChecked`` and ``dncComplainerResult``.
            dnc_other: deprecated alias that turns on both DNC checks.

        Raises:
            CheckThatPhoneError: for any non-2xx API response.
        """
        body: dict[str, Any] = {"phone": phone}
        if ip:
            body["ip"] = ip
        if litigator_filter:
            body["litigatorFilter"] = True
        if landline_sms_lookup:
            body["landlineSmsLookup"] = True
        if dnc_other:
            warnings.warn(
                "dnc_other is deprecated; use dnc_state and dnc_complainer",
                DeprecationWarning,
                stacklevel=2,
            )
        if dnc_state or dnc_other:
            body["dncState"] = True
        if dnc_complainer or dnc_other:
            body["dncComplainer"] = True

        req = urllib.request.Request(
            f"{self._base_url}/v1/lookup",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"checkthatphone-python/{__version__}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as res:
                payload = json.loads(res.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read().decode() or "{}")
            except (ValueError, OSError):
                err = {}
            raise CheckThatPhoneError(
                e.code,
                err.get("error") or f"HTTP {e.code}",
                err.get("detail"),
            ) from None

        return LookupResult(
            success=payload.get("success") is True,
            credits_used=payload.get("credits_used") or 0,
            data=payload.get("data") or {},
        )
