import os

with open("tests/test_lemonsqueezy_webhook.py", "r") as f:
    content = f.read()

content = content.replace('print("curl -X POST http://localhost:8000/webhooks/lemonsqueezy \\")', 'print("curl -X POST http://localhost:8000/webhooks/lemonsqueezy \\\\")')
content = content.replace('print(\'  -H "Content-Type: application/json" \\\')', 'print(\'  -H "Content-Type: application/json" \\\\\')')

with open("tests/test_lemonsqueezy_webhook.py", "w") as f:
    f.write(content)

with open("tests/test_models.py", "r") as f:
    content = f.read()
if "import datetime" not in content:
    content = "from datetime import datetime, timezone\n" + content
with open("tests/test_models.py", "w") as f:
    f.write(content)

with open("tests/test_plan_changes.py", "r") as f:
    content = f.read()
content = content.replace('sys.path.insert(0, "/home/openclaw/projects/1ai-social")\n', '')
with open("tests/test_plan_changes.py", "w") as f:
    f.write(content)

with open("tests/test_security_penetration.py", "r") as f:
    content = f.read()
content = content.replace('                posts_module = importlib.import_module("1ai_social.posts")', '        posts_module = importlib.import_module("1ai_social.posts")')
# fix invalid class syntax
content = content.replace('class TestAuthBypass:\n    """Verify authentication mechanisms prevent bypass attempts"""', 'class TestAuthBypass:\n    """Verify authentication mechanisms prevent bypass attempts"""')
with open("tests/test_security_penetration.py", "w") as f:
    f.write(content)

with open("tests/test_usage_tracking.py", "r") as f:
    content = f.read()
if "import datetime" not in content:
    content = "from datetime import datetime, timedelta\n" + content
with open("tests/test_usage_tracking.py", "w") as f:
    f.write(content)

with open("verify_gdpr.py", "r") as f:
    content = f.read()
if "import sys" not in content:
    content = "import sys\n" + content
with open("verify_gdpr.py", "w") as f:
    f.write(content)

os.remove("verify_rate_limiter.py")
