# Stripe Migration Plan

## Overview

This document outlines the migration strategy from LemonSqueezy to Stripe as the primary billing provider for 1ai-social. The migration uses a feature flag system to enable gradual rollout and safe rollback.

## Timeline

- **Phase 1 (Week 1-2)**: Stripe provider stub implementation and testing infrastructure
- **Phase 2 (Week 3-4)**: Full Stripe API integration (create, update, cancel subscriptions)
- **Phase 3 (Week 5)**: Webhook handler implementation for Stripe events
- **Phase 4 (Week 6)**: Data migration and parallel running (both providers active)
- **Phase 5 (Week 7)**: Cutover to Stripe (feature flag switch)
- **Phase 6 (Week 8)**: Monitoring and cleanup

**Total Estimated Duration**: 8 weeks

## Architecture

### Provider Abstraction

The billing system uses an abstract `BillingProvider` interface that both LemonSqueezy and Stripe implement:

```python
class BillingProvider(ABC):
    def create_subscription(tenant_id, plan, customer_email) -> Dict
    def cancel_subscription(tenant_id) -> Dict
    def update_subscription(tenant_id, new_plan) -> Dict
    def get_subscription(tenant_id) -> Optional[Dict]
    def verify_webhook_signature(signature, body) -> bool
```

### Feature Flag

The active provider is controlled via the `BILLING_PROVIDER` environment variable:

```bash
# Use LemonSqueezy (default)
BILLING_PROVIDER=lemonsqueezy

# Use Stripe
BILLING_PROVIDER=stripe
```

The factory function `get_billing_provider()` returns the appropriate provider instance based on this setting.

## Data Mapping: LemonSqueezy → Stripe

### Subscription Fields

| LemonSqueezy | Stripe | Notes |
|---|---|---|
| `subscription_id` | `subscription.id` | Stripe subscription ID |
| `customer_id` | `customer.id` | Stripe customer ID |
| `plan` (starter/pro/enterprise) | `items[0].price.id` | Map to Stripe price IDs |
| `status` (active/cancelled/past_due) | `status` (active/past_due/canceled) | Direct mapping |
| `current_period_start` | `current_period_start` | Unix timestamp |
| `current_period_end` | `current_period_end` | Unix timestamp |
| `cancel_at_period_end` | `cancel_at_period_end` | Boolean flag |
| `created_at` | `created` | Unix timestamp |
| `updated_at` | N/A | Track separately in DB |

### Plan Mapping

Configure Stripe price IDs in environment variables:

```bash
STRIPE_PRICE_STARTER=price_xxxxx
STRIPE_PRICE_PRO=price_yyyyy
STRIPE_PRICE_ENTERPRISE=price_zzzzz
```

### Customer Mapping

LemonSqueezy customer IDs must be mapped to Stripe customer IDs. Create a migration table:

```sql
CREATE TABLE customer_provider_mapping (
    id INTEGER PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    lemonsqueezy_customer_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, lemonsqueezy_customer_id),
    UNIQUE(tenant_id, stripe_customer_id)
);
```

## Migration Process

### Phase 1: Preparation

1. **Create Stripe account** and configure products/prices
2. **Set up Stripe API keys** in environment
3. **Implement StripeProvider** stub (already done in `provider.py`)
4. **Create test suite** for provider switching

### Phase 2: Full Stripe Implementation

Implement in `1ai_social/billing/stripe.py`:

```python
class StripeProvider(BillingProvider):
    def __init__(self):
        import stripe
        stripe.api_key = os.getenv("STRIPE_API_KEY")
    
    def create_subscription(self, tenant_id, plan, customer_email):
        # 1. Get or create Stripe customer
        # 2. Create subscription with appropriate price
        # 3. Store mapping in customer_provider_mapping
        # 4. Return subscription details
        pass
    
    def cancel_subscription(self, tenant_id):
        # 1. Look up Stripe subscription ID
        # 2. Cancel subscription
        # 3. Update DB
        pass
    
    # ... other methods
```

### Phase 3: Webhook Handler

Implement Stripe webhook handler in `1ai_social/billing/stripe_webhooks.py`:

```python
class StripeWebhookHandler:
    def handle_webhook(self, payload):
        event_type = payload['type']
        
        if event_type == 'customer.subscription.created':
            # Handle subscription creation
        elif event_type == 'customer.subscription.updated':
            # Handle subscription update
        elif event_type == 'customer.subscription.deleted':
            # Handle subscription cancellation
        elif event_type == 'invoice.payment_succeeded':
            # Handle successful payment
        elif event_type == 'invoice.payment_failed':
            # Handle failed payment
```

### Phase 4: Data Migration

1. **Export LemonSqueezy subscriptions** from database
2. **Create Stripe customers** for each tenant
3. **Create Stripe subscriptions** matching LemonSqueezy data
4. **Populate customer_provider_mapping** table
5. **Verify data integrity** (subscription counts, plan distribution)

Migration script template:

```python
def migrate_subscriptions():
    """Migrate all active subscriptions from LemonSqueezy to Stripe."""
    from sqlalchemy.orm import Session
    from 1ai_social.billing.lemonsqueezy import Subscription
    from 1ai_social.billing.provider import StripeProvider
    
    db = Session()
    stripe_provider = StripeProvider()
    
    # Get all active subscriptions
    subscriptions = db.query(Subscription).filter_by(status='active').all()
    
    for sub in subscriptions:
        try:
            # Create Stripe subscription
            result = stripe_provider.create_subscription(
                tenant_id=sub.tenant_id,
                plan=sub.plan,
                customer_email=get_tenant_email(sub.tenant_id)
            )
            
            # Store mapping
            store_customer_mapping(
                tenant_id=sub.tenant_id,
                lemonsqueezy_customer_id=sub.lemonsqueezy_customer_id,
                stripe_customer_id=result['stripe_customer_id']
            )
            
            logger.info(f"Migrated subscription for tenant {sub.tenant_id}")
        except Exception as e:
            logger.error(f"Failed to migrate tenant {sub.tenant_id}: {e}")
            # Continue with next subscription
```

### Phase 5: Parallel Running

1. **Set BILLING_PROVIDER=lemonsqueezy** (default, no change)
2. **Monitor Stripe integration** in staging environment
3. **Run both providers** in production for 1-2 weeks:
   - New subscriptions: Create in both providers
   - Existing subscriptions: Continue with LemonSqueezy
   - Webhooks: Process from both providers
4. **Validate data consistency** between providers

### Phase 6: Cutover

1. **Set BILLING_PROVIDER=stripe** in production
2. **Monitor for issues** (24/7 on-call)
3. **Redirect webhooks** from LemonSqueezy to Stripe
4. **Keep LemonSqueezy** running for 30 days (fallback)

## Rollback Plan

If issues occur during cutover:

### Immediate Rollback (< 1 hour)

1. Set `BILLING_PROVIDER=lemonsqueezy`
2. Restart application servers
3. Redirect webhooks back to LemonSqueezy
4. Notify support team

### Data Consistency Check

```python
def verify_migration_consistency():
    """Verify subscription data consistency between providers."""
    db = Session()
    
    # Check for orphaned subscriptions
    orphaned = db.query(Subscription).filter(
        ~Subscription.tenant_id.in_(
            db.query(CustomerProviderMapping.tenant_id)
        )
    ).all()
    
    if orphaned:
        logger.error(f"Found {len(orphaned)} orphaned subscriptions")
        return False
    
    # Check for duplicate subscriptions
    duplicates = db.query(Subscription.tenant_id).group_by(
        Subscription.tenant_id
    ).having(func.count() > 1).all()
    
    if duplicates:
        logger.error(f"Found {len(duplicates)} tenants with duplicate subscriptions")
        return False
    
    return True
```

### Full Rollback (> 1 hour)

1. Restore database from pre-migration backup
2. Set `BILLING_PROVIDER=lemonsqueezy`
3. Restart application
4. Investigate root cause
5. Plan retry for next week

## Testing Strategy

### Unit Tests

```python
def test_provider_factory():
    """Test that get_billing_provider returns correct provider."""
    os.environ['BILLING_PROVIDER'] = 'lemonsqueezy'
    provider = get_billing_provider()
    assert isinstance(provider, LemonSqueezyProvider)
    
    os.environ['BILLING_PROVIDER'] = 'stripe'
    provider = get_billing_provider()
    assert isinstance(provider, StripeProvider)

def test_provider_switching():
    """Test that provider can be switched at runtime."""
    # Create subscription with LemonSqueezy
    os.environ['BILLING_PROVIDER'] = 'lemonsqueezy'
    ls_provider = get_billing_provider()
    result1 = ls_provider.create_subscription('tenant1', 'pro', 'user@example.com')
    
    # Switch to Stripe
    os.environ['BILLING_PROVIDER'] = 'stripe'
    stripe_provider = get_billing_provider()
    result2 = stripe_provider.create_subscription('tenant1', 'pro', 'user@example.com')
    
    assert result1['provider'] == 'lemonsqueezy'
    assert result2['provider'] == 'stripe'
```

### Integration Tests

- Test webhook signature verification for both providers
- Test subscription lifecycle (create → update → cancel)
- Test error handling and retries
- Test concurrent requests

### Staging Environment

- Run full migration in staging first
- Test with real Stripe sandbox account
- Verify webhook delivery
- Load test with production-like data volume

## Monitoring & Alerts

### Key Metrics

- Subscription creation success rate (target: > 99.9%)
- Webhook processing latency (target: < 5s)
- Provider error rate (target: < 0.1%)
- Data consistency checks (target: 100% match)

### Alerts

- Provider error rate > 1%
- Webhook processing latency > 30s
- Data consistency check failure
- Stripe API rate limit exceeded

### Dashboards

Create Grafana dashboard with:
- Subscriptions by provider
- Webhook processing times
- Error rates by provider
- Data migration progress

## Cutover Checklist

- [ ] Stripe account fully configured
- [ ] All Stripe API keys in production secrets
- [ ] StripeProvider fully implemented and tested
- [ ] Stripe webhook handler implemented
- [ ] Migration script tested in staging
- [ ] Data migration completed
- [ ] Parallel running verified (1-2 weeks)
- [ ] Rollback plan documented and tested
- [ ] On-call team briefed
- [ ] Customer communication sent
- [ ] Monitoring and alerts configured
- [ ] Cutover window scheduled (low-traffic time)

## Post-Migration

### Week 1 After Cutover

- Daily data consistency checks
- Monitor error rates and latency
- Review webhook processing logs
- Check customer support tickets

### Week 2-4 After Cutover

- Weekly data consistency checks
- Reduce monitoring frequency
- Archive LemonSqueezy data
- Plan LemonSqueezy account closure

### Cleanup

- Remove LemonSqueezy provider code (after 30-day retention)
- Remove feature flag logic (make Stripe default)
- Update documentation
- Archive migration scripts

## References

- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe Webhooks](https://stripe.com/docs/webhooks)
- [LemonSqueezy API Documentation](https://docs.lemonsqueezy.com/)
- [Provider Pattern](https://refactoring.guru/design-patterns/strategy)
