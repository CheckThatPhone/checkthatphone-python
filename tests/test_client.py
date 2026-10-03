import io
import json
import unittest
import urllib.error
from unittest import mock

from checkthatphone import CheckThatPhone, CheckThatPhoneError


def _fake_response(body: dict):
    res = mock.MagicMock()
    res.read.return_value = json.dumps(body).encode()
    res.__enter__ = mock.MagicMock(return_value=res)
    res.__exit__ = mock.MagicMock(return_value=False)
    return res


class LookupTests(unittest.TestCase):
    def test_sends_flags_and_parses_envelope(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode())
            captured["auth"] = req.get_header("Authorization")
            return _fake_response(
                {"success": True, "credits_used": 2, "data": {"nanpType": "mobile"}}
            )

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client = CheckThatPhone("ctp_live_test")
            result = client.lookup("(818) 292-5409", litigator_filter=True, dnc_state=True, dnc_complainer=True)

        self.assertEqual(captured["url"], "https://api.checkthatphone.com/v1/lookup")
        self.assertEqual(
            captured["body"],
            {"phone": "(818) 292-5409", "litigatorFilter": True, "dncState": True, "dncComplainer": True},
        )
        self.assertEqual(captured["auth"], "Bearer ctp_live_test")
        self.assertTrue(result.success)
        self.assertEqual(result.credits_used, 2)
        self.assertEqual(result.data["nanpType"], "mobile")

    def test_deprecated_dnc_other_sends_both_new_flags(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_response({"success": True, "credits_used": 1, "data": {}})

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertWarns(DeprecationWarning):
                CheckThatPhone("k").lookup("8182925409", dnc_other=True)
        self.assertEqual(captured["body"], {"phone": "8182925409", "dncState": True, "dncComplainer": True})

    def test_sends_only_the_requested_dnc_check(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_response({"success": True, "credits_used": 1, "data": {}})

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            CheckThatPhone("k").lookup("8182925409", dnc_complainer=True)
        self.assertEqual(captured["body"], {"phone": "8182925409", "dncComplainer": True})

    def test_http_error_becomes_typed_exception(self):
        err = urllib.error.HTTPError(
            url="x",
            code=400,
            msg="Bad Request",
            hdrs=None,
            fp=io.BytesIO(
                json.dumps({"error": "Invalid request", "detail": "phone must be 10-11 digits"}).encode()
            ),
        )
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(CheckThatPhoneError) as ctx:
                CheckThatPhone("k").lookup("123")
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("10-11 digits", ctx.exception.detail)
        self.assertFalse(ctx.exception.retryable)

    def test_429_is_retryable(self):
        err = urllib.error.HTTPError("x", 429, "Too Many", None, io.BytesIO(b"{}"))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(CheckThatPhoneError) as ctx:
                CheckThatPhone("k").lookup("8182925409")
        self.assertTrue(ctx.exception.retryable)

    def test_requires_api_key(self):
        with self.assertRaises(ValueError):
            CheckThatPhone("")


if __name__ == "__main__":
    unittest.main()
