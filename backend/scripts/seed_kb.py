"""Seed the knowledge base with ~25 realistic support articles.

Usage (from backend/ directory):
    python -m scripts.seed_kb

Or inside Docker:
    docker-compose exec api python -m scripts.seed_kb
"""
from __future__ import annotations

import asyncio
import sys

# Sample KB documents: (title, category, content)
SAMPLE_DOCS: list[dict] = [
    # ── Billing docs ──────────────────────────────────────────────────────────
    {
        "title": "How to Update Your Payment Method",
        "category": "billing",
        "content": (
            "To update your payment method, navigate to Settings > Billing > Payment Methods. "
            "Click 'Add Payment Method' and enter your new credit card or bank details. "
            "Once verified, you can set it as the default for future invoices. "
            "Old payment methods can be removed after a new one is confirmed. "
            "We accept Visa, Mastercard, American Express, and ACH bank transfers. "
            "Changes take effect on your next billing cycle. "
            "If your card was declined, check that the billing address matches your bank records."
        ),
        "source_url": "https://help.example.com/billing/update-payment",
    },
    {
        "title": "Understanding Your Invoice",
        "category": "billing",
        "content": (
            "Your invoice is generated on the 1st of each month and covers usage from the previous month. "
            "Each invoice lists: your plan subscription fee, any overage charges, and applicable taxes. "
            "Invoices are sent to your billing email address. To change the billing email, go to Settings > Billing. "
            "You can download PDF copies of all past invoices from the Billing History page. "
            "VAT/GST is applied based on your billing country and is shown as a separate line item."
        ),
        "source_url": "https://help.example.com/billing/invoice-guide",
    },
    {
        "title": "Requesting a Refund",
        "category": "billing",
        "content": (
            "We offer a 14-day money-back guarantee for new subscriptions. "
            "To request a refund, contact support within 14 days of your initial payment. "
            "Refunds are processed within 5-10 business days to the original payment method. "
            "Partial refunds may be issued for unused portions of annual plans if cancelled before 30 days. "
            "Usage-based charges (API calls, storage overages) are non-refundable. "
            "Promotional credits cannot be refunded as cash."
        ),
        "source_url": "https://help.example.com/billing/refunds",
    },
    {
        "title": "Upgrading or Downgrading Your Plan",
        "category": "billing",
        "content": (
            "You can change your plan at any time from Settings > Billing > Change Plan. "
            "Upgrades take effect immediately; you are prorated for the remainder of the billing cycle. "
            "Downgrades take effect at the end of the current billing cycle. "
            "If you downgrade below your current usage (e.g., active seats), you must reduce usage first. "
            "Annual plan holders who upgrade mid-year will be charged the difference prorated to the upgrade date."
        ),
        "source_url": "https://help.example.com/billing/plan-changes",
    },
    {
        "title": "Failed Payment and Account Suspension",
        "category": "billing",
        "content": (
            "If a payment fails, we will retry automatically on day 3, 7, and 14. "
            "You will receive email notifications for each failed attempt. "
            "After three failed retries, your account will be suspended. "
            "Suspended accounts retain data for 30 days. Update your payment method to reactivate. "
            "To avoid suspension, ensure your card has sufficient funds and the billing address is correct."
        ),
        "source_url": "https://help.example.com/billing/failed-payments",
    },
    {
        "title": "Annual vs. Monthly Billing",
        "category": "billing",
        "content": (
            "Annual billing provides a 20% discount compared to monthly billing. "
            "Annual plans are charged in full upfront. "
            "You can switch from monthly to annual at any time; the annual charge applies at your next renewal. "
            "Switching from annual to monthly takes effect at the end of the annual period. "
            "Annual plan invoices are issued once per year."
        ),
        "source_url": "https://help.example.com/billing/annual-vs-monthly",
    },

    # ── Technical docs ────────────────────────────────────────────────────────
    {
        "title": "API Authentication and API Keys",
        "category": "technical",
        "content": (
            "All API requests require a Bearer token in the Authorization header: "
            "`Authorization: Bearer YOUR_API_KEY`. "
            "API keys can be generated from Settings > Developer > API Keys. "
            "Each key has a configurable scope (read-only or read-write). "
            "For security, rotate keys every 90 days and never commit them to source control. "
            "Rate limits: 1000 requests/minute for Pro plans, 5000 for Enterprise. "
            "If you receive 401 Unauthorized, verify your key is active and the Authorization header format is correct."
        ),
        "source_url": "https://docs.example.com/api/authentication",
    },
    {
        "title": "Troubleshooting Webhook Delivery Failures",
        "category": "technical",
        "content": (
            "Webhooks are sent via HTTPS POST to your configured endpoint. "
            "If delivery fails (non-2xx response or timeout), we retry up to 5 times with exponential backoff. "
            "Common causes of failure: endpoint URL changed, SSL certificate expired, firewall blocking our IPs. "
            "Our webhook IPs are: 203.0.113.1, 203.0.113.2, 203.0.113.3 — whitelist these. "
            "You can view delivery logs in Settings > Developer > Webhook Logs. "
            "To replay a failed webhook, click 'Retry' in the logs dashboard."
        ),
        "source_url": "https://docs.example.com/webhooks/troubleshooting",
    },
    {
        "title": "Integrating with Zapier",
        "category": "technical",
        "content": (
            "To connect your account to Zapier: "
            "1. Log into Zapier and create a new Zap. "
            "2. Search for 'Example SaaS' in the app directory. "
            "3. Click 'Connect' and enter your API key when prompted. "
            "4. Select a trigger event (e.g., 'New Ticket Created'). "
            "5. Map fields to your target app. "
            "Supported triggers: new ticket, ticket status changed, ticket closed. "
            "Supported actions: create ticket, update ticket status, add message. "
            "If authentication fails, regenerate your API key and reconnect."
        ),
        "source_url": "https://docs.example.com/integrations/zapier",
    },
    {
        "title": "Single Sign-On (SSO) Setup Guide",
        "category": "technical",
        "content": (
            "SSO is available on Enterprise plans. Supported providers: Okta, Azure AD, Google Workspace. "
            "Setup steps: "
            "1. Go to Settings > Security > Single Sign-On. "
            "2. Download our SAML metadata XML. "
            "3. Upload it to your IdP and configure the assertion consumer service URL. "
            "4. Copy the IdP metadata URL back into our SSO settings. "
            "5. Enable SSO — existing users will be prompted to link accounts on next login. "
            "SSO does not disable password login unless you also enable 'Enforce SSO'."
        ),
        "source_url": "https://docs.example.com/security/sso",
    },
    {
        "title": "Data Export and Backup",
        "category": "technical",
        "content": (
            "You can export all your data from Settings > Data Management > Export. "
            "Exports include: all tickets, messages, users, and knowledge base articles in JSON format. "
            "Large exports are processed asynchronously; you will receive an email with a download link within 1 hour. "
            "Download links expire after 48 hours. "
            "Automated backups run daily and are retained for 30 days (Enterprise: 90 days). "
            "To restore from a backup, contact support with your account ID and desired restore point."
        ),
        "source_url": "https://docs.example.com/data/export",
    },
    {
        "title": "Rate Limiting and Error Codes",
        "category": "technical",
        "content": (
            "When you exceed your rate limit, the API returns HTTP 429 Too Many Requests. "
            "The response includes a Retry-After header indicating seconds to wait. "
            "Common error codes: "
            "400 Bad Request — invalid request body (check Pydantic validation errors in the 'detail' field). "
            "401 Unauthorized — missing or invalid API key. "
            "403 Forbidden — valid key but insufficient scope. "
            "404 Not Found — resource does not exist or was deleted. "
            "429 Too Many Requests — slow down and implement exponential backoff. "
            "500 Internal Server Error — our fault; check our status page at status.example.com."
        ),
        "source_url": "https://docs.example.com/api/error-codes",
    },
    {
        "title": "Setting Up Two-Factor Authentication",
        "category": "technical",
        "content": (
            "Enable 2FA from Settings > Security > Two-Factor Authentication. "
            "Supported methods: authenticator app (TOTP), SMS, hardware keys (FIDO2). "
            "Recommended: use an authenticator app (Google Authenticator, Authy, 1Password). "
            "Steps: click 'Enable 2FA', scan the QR code with your authenticator app, enter the 6-digit code to confirm. "
            "Save your backup codes in a secure location — they are shown once. "
            "If you lose access to your 2FA device, use a backup code or contact support with account verification."
        ),
        "source_url": "https://docs.example.com/security/2fa",
    },
    {
        "title": "Mobile App Troubleshooting",
        "category": "technical",
        "content": (
            "Common mobile app issues and solutions: "
            "App crashes on launch: force-close the app, clear cache, and restart. If persists, reinstall. "
            "Notifications not received: check that notifications are enabled in your phone settings for the app. "
            "Login loop: clear app storage and log in again. Check that your account is not suspended. "
            "Sync delays: pull-to-refresh to force a manual sync. Check your internet connection. "
            "Minimum supported versions: iOS 15+, Android 10+. "
            "If issues persist after these steps, collect logs from Help > Send Logs within the app and contact support."
        ),
        "source_url": "https://help.example.com/mobile/troubleshooting",
    },

    # ── General docs ──────────────────────────────────────────────────────────
    {
        "title": "Getting Started: Your First 30 Days",
        "category": "general",
        "content": (
            "Welcome! Here's what to do in your first 30 days: "
            "Week 1: Complete your profile, invite team members, and explore the dashboard. "
            "Week 2: Import your existing data using our CSV importer or API. "
            "Week 3: Set up automations and notifications to fit your workflow. "
            "Week 4: Review analytics and adjust your configuration. "
            "Our onboarding checklist in the dashboard tracks your progress. "
            "Book a free 30-minute onboarding call with our team from the Help menu."
        ),
        "source_url": "https://help.example.com/getting-started",
    },
    {
        "title": "Managing Team Members and Roles",
        "category": "general",
        "content": (
            "Invite team members from Settings > Team > Invite Members. "
            "Available roles: Admin (full access), Agent (handle tickets), Viewer (read-only). "
            "Admins can: manage billing, configure settings, and invite/remove members. "
            "Agents can: view and respond to tickets, manage their own profile. "
            "Viewers can: read tickets and reports but not take actions. "
            "To remove a member, go to Settings > Team, find the member, and click 'Remove'. "
            "Removed members lose access immediately."
        ),
        "source_url": "https://help.example.com/team/roles",
    },
    {
        "title": "Customizing Notifications",
        "category": "general",
        "content": (
            "Configure notifications from Settings > Notifications. "
            "You can enable/disable: email notifications, in-app notifications, and mobile push notifications. "
            "Notification types: new ticket, ticket replied, ticket escalated, ticket closed. "
            "You can set 'Quiet Hours' to suppress notifications during off-hours. "
            "Team-level notification rules can be set by Admins in Settings > Team > Notification Rules."
        ),
        "source_url": "https://help.example.com/notifications",
    },
    {
        "title": "Using Tags and Labels",
        "category": "general",
        "content": (
            "Tags help organise tickets. Create tags from Settings > Tags. "
            "Apply tags to tickets manually or via automation rules. "
            "Tags are colour-coded for visual scanning of the ticket list. "
            "Use the tag filter on the ticket list to view tickets by tag. "
            "Tags can be used in automation rules (e.g., auto-assign tickets tagged 'urgent' to senior agents). "
            "Tags are also available in analytics reports for trend analysis."
        ),
        "source_url": "https://help.example.com/tags",
    },
    {
        "title": "Privacy Policy and Data Retention",
        "category": "general",
        "content": (
            "We are GDPR and CCPA compliant. Your data is stored in EU-West data centres by default. "
            "Data retention: ticket data is retained for the lifetime of your account plus 90 days after cancellation. "
            "You can request data deletion at any time from Settings > Privacy > Delete My Data. "
            "Deletion requests are processed within 30 days. "
            "We do not sell your data to third parties. "
            "For DPA (Data Processing Agreement) requests, email privacy@example.com."
        ),
        "source_url": "https://help.example.com/privacy",
    },
    {
        "title": "Service Level Agreement (SLA) Overview",
        "category": "general",
        "content": (
            "Our SLA commitments by plan: "
            "Basic: 99.5% uptime, email support with 48h response time. "
            "Pro: 99.9% uptime, email + chat support with 12h response time. "
            "Enterprise: 99.99% uptime, priority support with 1h response time, dedicated account manager. "
            "Uptime is calculated monthly, excluding scheduled maintenance. "
            "SLA credits: if uptime falls below the guarantee, you receive service credits (10% of monthly fee per 0.1% below guarantee). "
            "Monitor our live status at status.example.com."
        ),
        "source_url": "https://help.example.com/sla",
    },
    {
        "title": "Resetting Your Password",
        "category": "general",
        "content": (
            "To reset your password: "
            "1. Click 'Forgot Password' on the login page. "
            "2. Enter your registered email address. "
            "3. Check your email for a password reset link (valid for 1 hour). "
            "4. Click the link and enter your new password (min 8 characters). "
            "If you don't receive the email within 5 minutes, check your spam folder. "
            "If you no longer have access to the email address, contact support with account verification."
        ),
        "source_url": "https://help.example.com/account/reset-password",
    },
    {
        "title": "Closing or Cancelling Your Account",
        "category": "general",
        "content": (
            "To cancel your subscription, go to Settings > Billing > Cancel Subscription. "
            "Your access continues until the end of the current billing period. "
            "Annual plans: no refund after 30 days (see Refund Policy for details). "
            "To permanently delete your account and all data, go to Settings > Danger Zone > Delete Account. "
            "Account deletion is irreversible and removes all data within 30 days. "
            "We recommend exporting your data before deletion."
        ),
        "source_url": "https://help.example.com/account/cancel",
    },
    {
        "title": "Feature Requests and Roadmap",
        "category": "general",
        "content": (
            "We love hearing from customers about new features. "
            "Submit feature requests at feedback.example.com — use your account email to track status. "
            "Vote on existing requests to signal priority to our product team. "
            "Our public roadmap is available at roadmap.example.com and updated monthly. "
            "High-voted features are reviewed in our quarterly product planning cycle. "
            "Enterprise customers can discuss custom feature development with their account manager."
        ),
        "source_url": "https://help.example.com/feedback",
    },
    {
        "title": "Accessibility Features",
        "category": "general",
        "content": (
            "Our platform is designed to WCAG 2.1 AA standards. "
            "Accessibility features include: full keyboard navigation, screen reader support (ARIA labels), "
            "high-contrast mode (Settings > Appearance > High Contrast), adjustable font size, "
            "and captions on all video tutorials. "
            "If you encounter an accessibility barrier, please report it to accessibility@example.com "
            "and we will prioritise a fix."
        ),
        "source_url": "https://help.example.com/accessibility",
    },
]


async def seed() -> None:
    from app.db.session import AsyncSessionLocal
    from app.rag.ingest import ingest_document

    print(f"Seeding {len(SAMPLE_DOCS)} knowledge base documents...")

    async with AsyncSessionLocal() as db:
        for i, doc in enumerate(SAMPLE_DOCS, 1):
            print(f"  [{i}/{len(SAMPLE_DOCS)}] {doc['title']} ({doc['category']})")
            try:
                chunks = await ingest_document(
                    title=doc["title"],
                    content=doc["content"],
                    category=doc["category"],
                    source_url=doc.get("source_url"),
                    db=db,
                )
                print(f"    → {len(chunks)} chunk(s) embedded")
            except Exception as e:
                print(f"    ✗ Error: {e}")
                raise

    print("\n✓ Knowledge base seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
