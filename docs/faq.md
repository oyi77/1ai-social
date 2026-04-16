# Frequently Asked Questions

## Getting Started

### How do I connect my social media accounts?

1. Log in to your 1AI Social dashboard
2. Navigate to **Settings** → **Connected Accounts**
3. Click **Connect Account** and select your platform
4. Follow the OAuth authorization flow
5. Grant the necessary permissions
6. You'll be redirected back with a success message

Each platform requires different permissions. We only request what's needed to post and read analytics.

### What platforms are supported?

Currently supported:
- **X (Twitter)**: Full support for posts, threads, media
- **Instagram**: Feed posts, Stories, Reels, carousels
- **TikTok**: Video posts with captions
- **LinkedIn**: Personal and company page posts

Coming soon:
- Facebook
- YouTube

### How do I schedule posts?

1. Create your post content
2. Click **Schedule** instead of **Post Now**
3. Select date and time using the picker
4. Choose your timezone
5. Click **Schedule Post**

The post will automatically publish at the scheduled time. You can edit or cancel scheduled posts anytime before they go live.

### Can I post to multiple platforms at once?

Yes! When creating a post:
1. Check the boxes for all platforms you want to post to
2. Preview how the post looks on each platform
3. Customize content per platform if needed
4. Click **Post Now** or **Schedule**

The same content will be published to all selected platforms simultaneously.

## Content and AI

### How does AI content generation work?

Our AI uses advanced language models (GPT-4, Claude) to generate content:
1. You provide a topic or prompt
2. AI analyzes your request and generates relevant content
3. You can regenerate, edit, or refine the output
4. Choose tone, length, and style preferences

The AI learns from your edits to improve future suggestions.

### Can I edit AI-generated content?

Absolutely! AI-generated content is just a starting point:
- Edit text directly in the editor
- Regenerate if you don't like the result
- Adjust tone or length settings
- Combine AI suggestions with your own writing

Think of AI as a writing assistant, not a replacement.

### How many posts can I generate per month?

Depends on your plan:
- **Free**: 10 posts/month
- **Starter**: 100 posts/month
- **Professional**: Unlimited posts
- **Enterprise**: Unlimited posts

AI generation counts toward your monthly quota.

### What languages does the AI support?

The AI can generate content in 50+ languages including:
- English, Spanish, French, German, Italian
- Portuguese, Dutch, Russian, Polish
- Chinese, Japanese, Korean
- Arabic, Hindi, and many more

Specify the language in your prompt or settings.

## Billing and Plans

### How does billing work?

- **Monthly Billing**: Charged on the same day each month
- **Annual Billing**: Pay upfront, save 20%
- **Prorated Upgrades**: Only pay the difference when upgrading
- **Downgrade**: Takes effect at next billing cycle

All plans include a 14-day free trial (no credit card required).

### Can I change my plan?

Yes, anytime:
- **Upgrade**: Instant access, prorated billing
- **Downgrade**: Scheduled for next billing cycle
- **Cancel**: No penalties, access until period ends

Go to **Settings** → **Billing** to manage your plan.

### What payment methods do you accept?

- Credit cards (Visa, Mastercard, Amex, Discover)
- PayPal
- Invoice billing (Enterprise plans only)

All payments are processed securely through Stripe.

### What happens if I exceed my post limit?

On Free and Starter plans:
- You'll receive a warning at 80% usage
- At 100%, you can't create new posts until next cycle
- Upgrade anytime to increase your limit

Professional and Enterprise plans have unlimited posts.

### Do you offer refunds?

- **14-day trial**: Cancel anytime, no charge
- **Monthly plans**: No refunds, but you can cancel anytime
- **Annual plans**: Prorated refunds within 30 days
- **Enterprise**: Custom terms

Contact support for special circumstances.

## Team and Collaboration

### How do I add team members?

1. Go to **Settings** → **Team**
2. Click **Invite Member**
3. Enter their email address
4. Select their role (Admin, Editor, Viewer)
5. Click **Send Invitation**

They'll receive an email with instructions to join.

### What are the different user roles?

- **Admin**: Full access, can manage billing and team
- **Editor**: Create, edit, schedule, and publish posts
- **Viewer**: Read-only access to posts and analytics

Admins can change roles anytime.

### Can I manage multiple clients or brands?

Yes! Use workspaces:
- **Professional**: Up to 3 workspaces
- **Enterprise**: Unlimited workspaces

Each workspace has separate:
- Social accounts
- Content and media
- Team members
- Analytics

Switch between workspaces using the dropdown in the top navigation.

### How do approval workflows work?

Enable in **Settings** → **Workflows**:
1. Editors create posts marked as "Draft"
2. Admins review and approve or reject
3. Approved posts can be published or scheduled
4. Rejected posts return to editor with feedback

Perfect for agencies managing client content.

## Analytics and Reporting

### What metrics can I track?

Platform-specific metrics:
- **Engagement**: Likes, comments, shares, saves
- **Reach**: Impressions, unique viewers
- **Growth**: Follower changes over time
- **Clicks**: Link clicks and conversions
- **Video**: Views, watch time, completion rate

### How often are analytics updated?

- **Real-time**: Engagement metrics update every 15 minutes
- **Daily**: Follower counts and reach metrics
- **Platform limits**: Some platforms have API rate limits

Refresh manually anytime from the Analytics dashboard.

### Can I export analytics data?

Yes! Export options:
- **CSV**: Raw data for Excel or Google Sheets
- **PDF**: Formatted reports with charts
- **API**: Programmatic access (Professional and Enterprise)

Go to **Analytics** → **Export** to download.

### How do I generate reports for clients?

1. Navigate to **Analytics** → **Reports**
2. Select date range and metrics
3. Choose report template
4. Add your branding (Enterprise only)
5. Download PDF or schedule email delivery

Set up automated weekly or monthly reports.

## Technical and Security

### Is my data secure?

Yes, we take security seriously:
- **Encryption**: All data encrypted at rest and in transit (TLS 1.3)
- **Secure Storage**: Media stored in encrypted AWS S3 buckets
- **Access Control**: Role-based permissions
- **2FA**: Two-factor authentication available
- **SOC 2 Certified**: Enterprise plans

### Can I export my data?

Yes, full GDPR compliance:
1. Go to **Settings** → **Privacy**
2. Click **Export My Data**
3. Receive download link via email within 24 hours

Includes all posts, media, analytics, and account data.

### How do I delete my account?

1. Go to **Settings** → **Account**
2. Click **Delete Account**
3. Confirm deletion
4. All data permanently deleted within 30 days

This action cannot be undone. Export your data first if needed.

### What happens to scheduled posts if I cancel?

- Posts scheduled within your current billing period will still publish
- Posts scheduled after your plan expires will be cancelled
- You can manually publish or export them before cancellation

### Do you have an API?

Yes! API access available on:
- **Professional**: Rate-limited API access
- **Enterprise**: Unlimited API access with dedicated support

Documentation at `/api/docs` or contact support for API keys.

## Troubleshooting

### Why won't my social account connect?

Common issues:
- **Permissions**: Make sure you grant all requested permissions
- **Browser**: Try a different browser or disable ad blockers
- **Platform Issues**: Check if the platform is experiencing outages
- **Account Type**: Some platforms require business accounts

Still stuck? Contact support with screenshots.

### My scheduled post didn't publish. Why?

Possible reasons:
- **Account Disconnected**: Reconnect your social account
- **Platform Limits**: You hit daily posting limits
- **Content Violation**: Post flagged by platform policies
- **Service Outage**: Temporary platform or service issues

Check **Activity Log** for detailed error messages.

### How do I reconnect a disconnected account?

1. Go to **Settings** → **Connected Accounts**
2. Find the disconnected account (red warning icon)
3. Click **Reconnect**
4. Complete the OAuth flow again

Your scheduled posts will resume automatically.

### Can I recover deleted posts?

- **Within 30 days**: Yes, contact support
- **After 30 days**: No, permanently deleted

We recommend exporting important content regularly.

## Still Have Questions?

- **Email Support**: support@1aisocial.com
- **Live Chat**: Available on Professional and Enterprise plans
- **Community**: Join our Discord server
- **Documentation**: Check our full docs at `/docs`

Response times:
- Free: 48 hours
- Starter: 24 hours
- Professional: 12 hours
- Enterprise: 4 hours (priority support)
