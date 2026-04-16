-- Test script to verify Row-Level Security (RLS) tenant isolation
-- Run this after applying migration 004_rls_policies.py

-- Setup: Create test tenants as admin
SELECT set_tenant_context('bootstrap', 'admin');

INSERT INTO tenants (id, name, plan, status) VALUES
    ('tenant-a', 'Tenant A Corp', 'enterprise', 'active'),
    ('tenant-b', 'Tenant B Inc', 'starter', 'active')
ON CONFLICT (id) DO NOTHING;

-- Setup: Create test data for Tenant A
INSERT INTO platforms (name, credentials, user_id, tenant_id) VALUES
    ('X', '{"token": "xxx"}', 'user-a', 'tenant-a')
ON CONFLICT (name) DO NOTHING;

INSERT INTO contents (text, platform, tenant_id) VALUES
    ('Post from Tenant A', 'X', 'tenant-a');

-- Setup: Create test data for Tenant B
INSERT INTO platforms (name, credentials, user_id, tenant_id) VALUES
    ('Instagram', '{"token": "yyy"}', 'user-b', 'tenant-b')
ON CONFLICT (name) DO NOTHING;

INSERT INTO contents (text, platform, tenant_id) VALUES
    ('Post from Tenant B', 'Instagram', 'tenant-b');

-- Clear context
SELECT clear_tenant_context();

\echo '\n=== TEST 1: Tenant A Isolation ==='
SELECT set_tenant_context('tenant-a');
\echo 'Tenant A should see ONLY their own data:'
SELECT id, name, user_id, tenant_id FROM platforms;
SELECT id, text, tenant_id FROM contents;

\echo '\n=== TEST 2: Tenant B Isolation ==='
SELECT set_tenant_context('tenant-b');
\echo 'Tenant B should see ONLY their own data:'
SELECT id, name, user_id, tenant_id FROM platforms;
SELECT id, text, tenant_id FROM contents;

\echo '\n=== TEST 3: No Context (Should see nothing) ==='
SELECT clear_tenant_context();
\echo 'Without context, should see 0 rows:'
SELECT COUNT(*) as platforms_count FROM platforms;
SELECT COUNT(*) as contents_count FROM contents;

\echo '\n=== TEST 4: Admin Access (Should see all) ==='
SELECT set_tenant_context('tenant-a', 'admin');
\echo 'Admin should see ALL data from both tenants:'
SELECT id, name, user_id, tenant_id FROM platforms ORDER BY tenant_id;
SELECT id, text, tenant_id FROM contents ORDER BY tenant_id;

\echo '\n=== TEST 5: Tenants Table Isolation ==='
SELECT clear_tenant_context();
SELECT set_tenant_context('tenant-a');
\echo 'Tenant A should see only their own tenant record:'
SELECT id, name FROM tenants;

SELECT clear_tenant_context();
SELECT set_tenant_context('tenant-b');
\echo 'Tenant B should see only their own tenant record:'
SELECT id, name FROM tenants;

SELECT clear_tenant_context();
SELECT set_tenant_context('tenant-a', 'admin');
\echo 'Admin should see all tenants:'
SELECT id, name FROM tenants ORDER BY id;

\echo '\n=== TEST 6: Cross-Tenant Write Protection ==='
SELECT clear_tenant_context();
SELECT set_tenant_context('tenant-a');
\echo 'Tenant A attempts to update Tenant B data (should affect 0 rows):'
UPDATE contents SET text = 'Hacked by Tenant A' WHERE tenant_id = 'tenant-b';
SELECT 'Rows affected:' as test, (SELECT COUNT(*) FROM contents WHERE text = 'Hacked by Tenant A') as count;

SELECT clear_tenant_context();
SELECT set_tenant_context('tenant-b');
\echo 'Verify Tenant B data is unchanged:'
SELECT text FROM contents WHERE tenant_id = 'tenant-b';

-- Cleanup
SELECT clear_tenant_context();

\echo '\n=== RLS Tests Complete ==='
\echo 'Expected Results:'
\echo '✓ TEST 1: Tenant A sees only tenant-a data (1 platform, 1 content)'
\echo '✓ TEST 2: Tenant B sees only tenant-b data (1 platform, 1 content)'
\echo '✓ TEST 3: No context = 0 rows visible'
\echo '✓ TEST 4: Admin sees all data from both tenants (2 platforms, 2 contents)'
\echo '✓ TEST 5: Each tenant sees only their own tenant record, admin sees all'
\echo '✓ TEST 6: Cross-tenant update affects 0 rows, data unchanged'
