import re

with open("tests/test_gdpr_compliance.py", "r") as f:
    content = f.read()

content = re.sub(r'self\.manager\.export_user_data\(user_id="user123", tenant_id="tenant456"\)', 'export_data = self.manager.export_user_data(user_id="user123", tenant_id="tenant456")', content)
content = re.sub(r'self\.manager\.delete_user_data\(user_id="user123", tenant_id="tenant_id"\)', 'deletion_summary = self.manager.delete_user_data(user_id="user123", tenant_id="tenant_id")', content)
content = re.sub(r'manager\.record_consent\(user_id="user123", tenant_id="tenant456"\)', 'consent_id = manager.record_consent(user_id="user123", tenant_id="tenant456")', content)

with open("tests/test_gdpr_compliance.py", "w") as f:
    f.write(content)
