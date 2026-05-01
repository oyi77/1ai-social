import re

with open("tests/test_lemonsqueezy_webhook.py", "r") as f:
    content = f.read()

content = content.replace('        print(f"\\nPayload:\\n{body}")\n        print("\n\n        print("curl', '        print(f"\\nPayload:\\n{body}")\n        print("curl')

with open("tests/test_lemonsqueezy_webhook.py", "w") as f:
    f.write(content)
