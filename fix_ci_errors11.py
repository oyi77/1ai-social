import re

with open("tests/test_tenant_isolation.py", "r") as f:
    content = f.read()

content = content.replace("from sqlalchemy import create_engine, text\nfrom sqlalchemy.orm import sessionmaker, Session\n", "")
content = "from sqlalchemy import create_engine, text\nfrom sqlalchemy.orm import sessionmaker, Session\n" + content

with open("tests/test_tenant_isolation.py", "w") as f:
    f.write(content)

with open("tests/test_usage_tracking.py", "r") as f:
    content = f.read()

content = content.replace("from sqlalchemy import create_engine, text\nfrom sqlalchemy.orm import sessionmaker\n\nimport importlib\n", "")
content = "from sqlalchemy import create_engine, text\nfrom sqlalchemy.orm import sessionmaker\nimport importlib\n" + content

with open("tests/test_usage_tracking.py", "w") as f:
    f.write(content)
