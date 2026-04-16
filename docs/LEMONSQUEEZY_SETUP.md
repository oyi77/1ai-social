# LemonSqueezy Integration Setup

## Overview

LemonSqueezy payment provider integration with webhook handling for subscription events.

## Features

- HMAC-SHA256 webhook signature verification
- Subscription lifecycle management (created, updated, cancelled)
- Payment event handling (success, failed)
- Idempotency with Redis to prevent duplicate processing
- Multi-tenant subscription storage

## Database Schema

### subscriptions table

```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    lemonsqueezy_subscription_id VARCHAR(255) UNIQUE NOT NULL,
    lemonsqueezy_customer_id VARCHAR(255),
    plan VARCHAR(50) NOT NULL,  -- starter/pro/enterprise
    status VARCHAR(50) NOT NULL,  -- active/cancelled/past_due
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

## Environment Variables

```bash
# Required
LEMONSQUEEZY_WEBHOOK_SECRET=your_webhook_signing_secret

# Optional
LEMONSQUEEZY_API_KEY=your_api_key
LEMONSQUEEZY_VARIANT_STARTER=variant_id_for_starter_plan
LEMONSQUEEZY_VARIANT_PRO=variant_id_for_pro_plan
LEMONSQUEEZY_VARIANT_ENTERPRISE=variant_id_for_enterprise_plan

# Redis for idempotency
REDIS_URL=redis://localhost:6379/0
```

## Webhook Configuration

### 1. Create Webhook in LemonSqueezy Dashboard

1. Go to Settings → Webhooks
2. Click "Create Webhook"
3. Set URL: `https://your-domain.com/webhooks/lemonsqueezy`
4. Set signing secret (save to `LEMONSQUEEZY_WEBHOOK_SECRET`)
5. Select events:
   - `subscription_created`
   - `subscription_updated`
   - `subscription_cancelled`
   - `subscription_payment_success`
   - `subscription_payment_failed`

### 2. Webhook Endpoint

**Endpoint:** `POST /webhooks/lemonsqueezy`

**Headers:**
- `X-Signature`: HMAC-SHA256 signature of request body
- `Content-Type`: application/json

**Request Body:** LemonSqueezy webhook payload (JSON)

## Supported Events

### subscription_created
New subscription created. Creates subscription record in database.

### subscription_updated
Subscription details changed (plan, renewal date, etc.). Updates existing record.

### subscription_cancelled
Subscription cancelled. Sets status to "cancelled".

### subscription_payment_success
Payment succeeded. Sets status to "active".

### subscription_payment_failed
Payment failed. Sets status to "past_due".

## Testing

### Run Migration

```bash
alembic upgrade head
```

### Test Webhook Locally

```bash
# Set environment variable
export LEMONSQUEEZY_WEBHOOK_SECRET=test_secret_key

# Generate test payloads
python tests/test_lemonsqueezy_webhook.py

# Use the generated curl commands to test
```

### Example Test Request

```bash
curl -X POST http://localhost:8000/webhooks/lemonsqueezy \
  -H "X-Signature: 9ede49aa69203849e4a36e53519ef93617b7774acac8e575bc64ef6f55b09780" \
  -H "Content-Type: application/json" \
  -d '{
    "meta": {
      "event_name": "subscription_created",
      "webhook_id": "webhook-001"
    },
    "data": {
      "id": "sub_12345",
      "attributes": {
        "customer_id": "cust_67890",
        "status": "active",
        "variant_id": "variant_starter",
        "renews_at": "2026-05-16T00:00:00Z"
      }
    }
  }'
```

## Security

- **Signature Verification**: All webhooks verified using HMAC-SHA256
- **Idempotency**: Duplicate webhooks detected and skipped using Redis
- **Row-Level Security**: Subscriptions isolated by tenant_id
- **No Card Storage**: Payment details never stored locally

## Plan Mapping

Configure variant-to-plan mapping via environment variables:

```bash
LEMONSQUEEZY_VARIANT_STARTER=123456
LEMONSQUEEZY_VARIANT_PRO=123457
LEMONSQUEEZY_VARIANT_ENTERPRISE=123458
```

Default: All variants map to "starter" plan.

## Troubleshooting

### Webhook Signature Verification Failed

- Check `LEMONSQUEEZY_WEBHOOK_SECRET` matches LemonSqueezy dashboard
- Ensure raw request body is used (not parsed JSON)
- Verify X-Signature header is present

### Duplicate Webhook Errors

- Normal behavior - webhooks are idempotent
- Check Redis is running and accessible
- Webhook IDs stored for 24 hours

### Subscription Not Found

- Ensure `subscription_created` event processed first
- Check `lemonsqueezy_subscription_id` matches
- Verify tenant_id mapping is correct

## Files Created

- `1ai_social/billing/__init__.py` - Billing module
- `1ai_social/billing/lemonsqueezy.py` - LemonSqueezy integration
- `migrations/versions/006_subscriptions.py` - Database migration
- `tests/test_lemonsqueezy_webhook.py` - Test utilities
- `docs/LEMONSQUEEZY_SETUP.md` - This documentation

## Next Steps

1. Configure LemonSqueezy webhook in dashboard
2. Set environment variables
3. Run database migration
4. Test with mock webhooks
5. Monitor webhook logs in production

## Quick Start Commands

# 1. Run migration
alembic upgrade head

# 2. Set environment variable
export LEMONSQUEEZY_WEBHOOK_SECRET=your_secret_here

# 3. Test with mock webhook
python tests/test_lemonsqueezy_webhook.py

# 4. Configure webhook in LemonSqueezy dashboard
# URL: https://your-domain.com/webhooks/lemonsqueezy
# Events: subscription_created, subscription_updated, subscription_cancelled, 
#         subscription_payment_success, subscription_payment_failed

