import re

with open("tests/test_lemonsqueezy_webhook.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.strip() == 'print(f"Signature: {signature}':
        new_lines.append('    print(f"Signature: {signature}\\nTo test webhook, use:")\n')
        skip = True
    elif skip and line.strip() == 'To test webhook, use:")':
        skip = False
    else:
        if not skip:
            new_lines.append(line)

with open("tests/test_lemonsqueezy_webhook.py", "w") as f:
    f.writelines(new_lines)
