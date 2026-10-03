# checkthatphone

[![PyPI version](https://img.shields.io/pypi/v/checkthatphone)](https://pypi.org/project/checkthatphone/) [![CI](https://github.com/CheckThatPhone/checkthatphone-python/actions/workflows/ci.yml/badge.svg)](https://github.com/CheckThatPhone/checkthatphone-python/actions/workflows/ci.yml) [![python >= 3.9](https://img.shields.io/pypi/pyversions/checkthatphone)](https://pypi.org/project/checkthatphone/)

Official Python client for the [CheckThatPhone](https://checkthatphone.com) phone validation API. Validate US and Canadian phone numbers in real time: carrier and line type from live carrier data, portability and deliverability, GeoIP and timezone, plus optional TCPA litigator screening and free state do-not-call and complainer scrubs — one call, one credit.

Zero dependencies (standard library only). Python 3.9+.

## Install

```bash
pip install checkthatphone
```

## Quick start

```python
import os
from checkthatphone import CheckThatPhone

client = CheckThatPhone(api_key=os.environ["CHECKTHATPHONE_API_KEY"])

result = client.lookup("8182925409")
print(result.data["nanpType"])     # "mobile"
print(result.data["dipCarrier"])   # "AT&T"
print(result.data["deliverable"])  # "true"
print(result.credits_used)         # 1
```

Get an API key at [checkthatphone.com](https://checkthatphone.com) — the free tier includes 500 lookups per month.

## TCPA litigator screening

Flag known serial TCPA plaintiffs before you call or text (+1 credit):

```python
result = client.lookup("8182925409", litigator_filter=True)
if result.data.get("litigator") == "true":
    # result.data["litigator_type"]: "litigator" | "plaintiff" | "agitator"
    suppress(result.data["subscriber"])
```

## State DNC and complainer scrub (free)

Screen state do-not-call registries (38 states plus DC) and a national complainer list at no extra credit. Each check is its own flag:

```python
result = client.lookup("8182925409", dnc_state=True, dnc_complainer=True)
result.data.get("dncStateChecked")      # "true" when the state check ran; absent for the 12 states with no registry data
result.data.get("dncStateResult")       # "STATE DNC" on a match, "" otherwise (only when dncStateChecked is "true")
result.data.get("dncComplainerChecked") # "true" when the complainer check ran
result.data.get("dncComplainerResult")  # "DNC COMPLAINER" on a match, "" otherwise
```

Read `dncStateChecked` before `dncStateResult`: a number in an uncovered state comes back with neither field, which means not checked, not clear. `"error"` means the check could not complete; treat it as unavailable.

`dnc_other=True` still works as a shorthand for both checks, but it is deprecated.

## Landline SMS reachability

Some landlines can receive texts. Detect them instead of dropping them (+1 credit, charged only when the number is a landline):

```python
result = client.lookup("5551234567", landline_sms_lookup=True)
if result.data.get("dipMessagingEnabled") == "true":
    send_sms(...)
```

## GeoIP and timezone

Pass the contact's IP for city-level location and the IANA timezone (no extra charge) — useful for TCPA calling-hours compliance:

```python
result = client.lookup("8182925409", ip="136.38.145.14")
result.data["timezone"]  # "America/Los_Angeles"
```

## Errors

Non-2xx responses raise `CheckThatPhoneError` with `status`, `code`, `detail`, and a `retryable` hint. Failed and invalid requests are billed 0 credits.

```python
from checkthatphone import CheckThatPhoneError

try:
    client.lookup("not-a-number")
except CheckThatPhoneError as err:
    if err.retryable:
        retry_later()
```

## Full field reference

Every response field (carrier DIP, portability/LRN, deactivation, blacklist, and more) is documented at [checkthatphone.com/docs](https://checkthatphone.com/docs).

## License

MIT
