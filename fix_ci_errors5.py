import re
import os

with open("tests/test_lemonsqueezy_webhook.py", "r") as f:
    content = f.read()

content = content.replace('        print(f"\\nPayload:\\n{body}\\nCURL command:")\n\n        print("curl -X POST http://localhost:8000/webhooks/lemonsqueezy \\\\")', '        print(f"\\nPayload:\\n{body}\\nCURL command:")\n        print("curl -X POST http://localhost:8000/webhooks/lemonsqueezy \\\\")')

with open("tests/test_lemonsqueezy_webhook.py", "w") as f:
    f.write(content)
