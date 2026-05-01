import re

with open("tests/test_lemonsqueezy_webhook.py", "r") as f:
    content = f.read()

content = re.sub(r'        print\(f"Signature: \{signature\}\nTo test webhook, use:"\)\n    print\(f"  X-Signature: \{signature\}"\)\n    print\(f"  Body: \{body\}"\)', '    print(f"Signature: {signature}\\nTo test webhook, use:")\n    print(f"  X-Signature: {signature}")\n    print(f"  Body: {body}")', content)

with open("tests/test_lemonsqueezy_webhook.py", "w") as f:
    f.write(content)
