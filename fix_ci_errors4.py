import re

with open("tests/test_lemonsqueezy_webhook.py", "r") as f:
    content = f.read()

content = re.sub(r'print\("Signature: \{signature\}"\)\n    print\("', 'print(f"Signature: {signature}\\nTo test webhook, use:")', content)
content = re.sub(r'To test webhook, use:"\)\n    print\("  X-Signature: \{signature\}"\)\n    print\("  Body: \{body\}"\)', 'print(f"  X-Signature: {signature}")\n    print(f"  Body: {body}")', content)

content = re.sub(r'print\("\\nPayload:\\n\{body\}"\)\n    print\("', 'print(f"\\nPayload:\\n{body}\\nCURL command:")', content)
content = re.sub(r'CURL command:"\)', '', content)

content = content.replace('print("curl -X POST http://localhost:8000/webhooks/lemonsqueezy \\\\")', 'print("curl -X POST http://localhost:8000/webhooks/lemonsqueezy \\\\")')

with open("tests/test_lemonsqueezy_webhook.py", "w") as f:
    f.write(content)

with open("tests/test_security_penetration.py", "r") as f:
    content = f.read()
content = content.replace('from datetime import datetime, timedelta\nimport importlib', 'from datetime import datetime, timedelta\nimport importlib\nfrom unittest.mock import patch')
with open("tests/test_security_penetration.py", "w") as f:
    f.write(content)
