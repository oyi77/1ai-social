import re
import os

# 1. Fix unused imports and formatting
files_to_fix = [
    "tests/test_config.py",
    "tests/test_e2e_integration.py",
    "tests/test_gdpr_compliance.py",
    "tests/test_generators.py",
    "tests/test_lemonsqueezy_webhook.py",
    "tests/test_models.py",
    "tests/test_orchestrators.py",
    "tests/test_plan_changes.py",
    "tests/test_schedulers.py",
    "tests/test_security_penetration.py",
    "tests/test_tenant_isolation.py",
    "tests/test_usage_tracking.py",
    "verify_gdpr.py",
    "verify_rate_limiter.py"
]

for file in files_to_fix:
    if os.path.exists(file):
        with open(file, "r") as f:
            content = f.read()

        # Remove "import sys" and "sys.path.insert(0, ".")" if added unnecessarily at module level
        content = re.sub(r'import sys\n', '', content)
        content = re.sub(r'sys\.path\.insert\(0, "\."\)\n', '', content)
        content = re.sub(r'sys\.path\.insert\(0, os\.path\.dirname\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\)\)\)\n', '', content)

        # Specific file fixes
        if file == "tests/test_config.py":
            content = re.sub(r'from pathlib import Path\n', '', content)
        if file == "tests/test_gdpr_compliance.py":
            content = re.sub(r'from typing import Dict, Any\n', '', content)
            content = re.sub(r'from unittest\.mock import Mock, MagicMock, patch\n', '', content)
            content = re.sub(r'export_data = self\.manager\.export_user_data\(.*?\)', 'self.manager.export_user_data(user_id="user123", tenant_id="tenant456")', content, flags=re.DOTALL)
            content = re.sub(r'deletion_summary = self\.manager\.delete_user_data\(.*?\)', 'self.manager.delete_user_data(user_id="user123", tenant_id="tenant_id")', content, flags=re.DOTALL)
            content = re.sub(r'consent_id = manager\.record_consent\(.*?\)', 'manager.record_consent(user_id="user123", tenant_id="tenant456")', content, flags=re.DOTALL)
            content = re.sub(r'consent_id = manager\.record_consent\(.*?\)', 'manager.record_consent(user_id="user123", tenant_id="tenant456")', content, flags=re.DOTALL)
        if file == "tests/test_e2e_integration.py":
            content = re.sub(r'mock_redis_instance = mock\.MagicMock\(\)\n\s+mock_redis\.return_value = mock_redis_instance\n', '', content)
            content = re.sub(r'mock_redis\.return_value = mock_redis_instance\n', '', content)
            content = re.sub(r'mock_redis_instance\.get\.return_value = b"45"\n', '', content)
        if file == "tests/test_generators.py":
            content = re.sub(r'from unittest\.mock import Mock, patch\n', 'from unittest.mock import patch\n', content)
        if file == "tests/test_lemonsqueezy_webhook.py":
            content = re.sub(r'from datetime import datetime\n', '', content)
            content = re.sub(r'f"Payload:', '"Payload:', content)
            content = re.sub(r'f"Signature:', '"Signature:', content)
            content = re.sub(r'f"\\nTo test webhook, use:"', r'"\nTo test webhook, use:"', content)
            content = re.sub(r'f"  X-Signature:', '"  X-Signature:', content)
            content = re.sub(r'f"  Body:', '"  Body:', content)
            content = re.sub(r'f"\\nCURL command:"', r'"\nCURL command:"', content)
            content = re.sub(r'f"curl -X POST http://localhost:8000/webhooks/lemonsqueezy \\\\"', '"curl -X POST http://localhost:8000/webhooks/lemonsqueezy \\\\"', content)
            content = re.sub(r"f'  -H \"Content-Type: application/json\" \\\\'", "'  -H \"Content-Type: application/json\" \\\\'", content)
        if file == "tests/test_models.py":
            content = re.sub(r'from datetime import datetime, timezone\n', '', content)
        if file == "tests/test_orchestrators.py":
            content = re.sub(r'from unittest\.mock import Mock, patch, MagicMock\n', '', content)
        if file == "tests/test_plan_changes.py":
            content = re.sub(r'from sqlalchemy import create_engine, Column, String, DateTime, Column, String, DateTime\n', 'from sqlalchemy import create_engine, Column, String, DateTime\n', content)
        if file == "tests/test_schedulers.py":
            content = re.sub(r'import json\n', '', content)
            content = re.sub(r'callback = lambda: None', 'def callback():\n            pass', content)
        if file == "tests/test_security_penetration.py":
            content = re.sub(r'from unittest\.mock import Mock, patch, MagicMock\n', '', content)
            content = re.sub(r'malicious_input = "\'; DROP TABLE users; --"\n', '', content)
            content = re.sub(r'xss_payload = "<script>alert\(\'XSS\'\)</script>"\n', '', content)
            content = re.sub(r'expired_time = datetime\.utcnow\(\) - timedelta\(hours=2\)\n', '', content)
        if file == "tests/test_tenant_isolation.py":
            content = re.sub(r'from datetime import datetime, timezone\n', '', content)
        if file == "tests/test_usage_tracking.py":
            content = re.sub(r'from datetime import datetime, timedelta\n', '', content)
        if file == "verify_gdpr.py":
            content = re.sub(r'from sqlalchemy\.orm import sessionmaker\n', '', content)
        if file == "verify_rate_limiter.py":
            content = content.replace('from 1ai_social.rate_limiter import RateLimiter, RateLimitExceeded, RATE_LIMITS\n\nprint("✓ Rate limiter module imports successfully")', 'from 1ai_social.rate_limiter import RateLimiter, RateLimitExceeded, RATE_LIMITS\nprint("✓ Rate limiter module imports successfully")')
            content = content.replace('from 1ai_social.rate_limiter import RateLimiter, RateLimitExceeded, RATE_LIMITS\nprint("✓ Rate limiter module imports successfully")', 'from 1ai_social.rate_limiter import RateLimiter, RateLimitExceeded, RATE_LIMITS\nprint("✓ Rate limiter module imports successfully")')
            # ensure no multiple imports or bad syntax

        with open(file, "w") as f:
            f.write(content)
