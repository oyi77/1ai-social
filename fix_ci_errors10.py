import re

with open("tests/test_gdpr_compliance.py", "r") as f:
    content = f.read()

# Fix mock undefined error in tests/test_gdpr_compliance.py
if "from unittest.mock import Mock" not in content:
    content = "from unittest.mock import Mock\n" + content

with open("tests/test_gdpr_compliance.py", "w") as f:
    f.write(content)

with open("tests/test_models.py", "r") as f:
    content = f.read()
if "from datetime import datetime, timezone\n" in content:
    content = content.replace("from datetime import datetime, timezone\n", "")
    content = "from datetime import datetime, timezone\n" + content
with open("tests/test_models.py", "w") as f:
    f.write(content)

with open("tests/test_security_penetration.py", "r") as f:
    content = f.read()
if "from datetime import datetime, timedelta\n" in content:
    content = content.replace("from datetime import datetime, timedelta\nimport importlib\nfrom unittest.mock import patch\n", "")
    content = "from datetime import datetime, timedelta\nimport importlib\nfrom unittest.mock import patch\n" + content
with open("tests/test_security_penetration.py", "w") as f:
    f.write(content)
