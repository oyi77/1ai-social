# Webhook Format Documentation

## Overview

The 1ai-social platform supports secure webhook verification using HMAC-SHA256 signatures with replay protection and idempotency handling.

## Webhook Request Format

```http
POST /webhooks/:provider
Content-Type: application/json
X-Webhook-Signature: sha256=<hmac_hex_digest>
X-Webhook-Timestamp: <unix_timestamp>
X-Webhook-ID: <unique_webhook_id>

{
  "event": "event_type",
  "data": { ... }
}
```

## Headers

### X-Webhook-Signature (Required)
- Format: `sha256=<hex_digest>`
- HMAC-SHA256 signature of the payload
- Computed as: `HMAC-SHA256(secret, timestamp + "." + body)`

### X-Webhook-Timestamp (Required)
- Format: Unix timestamp (seconds since epoch)
- Must be within 5 minutes of current time
- Prevents replay attacks

### X-Webhook-ID (Required)
- Format: Unique identifier string
- Used for idempotency (deduplication)
- Stored in Redis for 1 hour

## Security Features

### 1. HMAC-SHA256 Signature Verification
- Uses timing-safe comparison (`secrets.compare_digest`)
- Prevents timing attacks
- Rejects invalid signatures with 401 Unauthorized

### 2. Replay Protection
- Validates timestamp is within 5 minutes
- Allows 1 minute clock skew for future timestamps
- Rejects old webhooks with 401 Unauthorized

### 3. Idempotency
- Stores webhook IDs in Redis with 1-hour TTL
- Prevents duplicate processing
- Rejects duplicate webhooks with 401 Unauthorized

## Configuration

Set webhook secrets as environment variables:

```bash
WEBHOOK_SECRET_STRIPE=your_stripe_webhook_secret
WEBHOOK_SECRET_GITHUB=your_github_webhook_secret
WEBHOOK_SECRET_TWITTER=your_twitter_webhook_secret
```

Format: `WEBHOOK_SECRET_<PROVIDER_UPPERCASE>`

## Example: Computing Signature

```python
import hashlib
import hmac
import time

secret = "your_webhook_secret"
timestamp = str(int(time.time()))
body = '{"event": "test", "data": "hello"}'

# Construct signed payload
signed_payload = f"{timestamp}.{body}"

# Compute HMAC-SHA256
signature = hmac.new(
    secret.encode('utf-8'),
    signed_payload.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# Format for header
header_value = f"sha256={signature}"
```

## Example: Sending Webhook

```bash
curl -X POST https://api.1ai-social.com/webhooks/stripe \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: sha256=abc123..." \
  -H "X-Webhook-Timestamp: 1713262586" \
  -H "X-Webhook-ID: evt_unique_id_123" \
  -d '{"event": "payment.success", "amount": 1000}'
```

## Response Codes

- **200 OK**: Webhook verified and processed successfully
- **401 Unauthorized**: Signature verification failed, timestamp too old, or duplicate webhook
- **500 Internal Server Error**: Server error during processing

## Error Messages

### Invalid Signature
```json
{
  "status": "unauthorized",
  "message": "Invalid signature"
}
```

### Replay Attack (Old Timestamp)
```json
{
  "status": "unauthorized",
  "message": "Timestamp too old: 600s (max: 300s)"
}
```

### Duplicate Webhook
```json
{
  "status": "unauthorized",
  "message": "Webhook already processed: evt_123"
}
```

## Testing

Run the test suite:

```bash
python3 test_webhook.py
```

Tests cover:
- Valid signature acceptance
- Invalid signature rejection
- Old timestamp rejection (replay attack)
- Timing-safe comparison
- Signature format validation
- Missing signature/timestamp handling
