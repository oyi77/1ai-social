# CI/CD Pipeline Configuration

## Workflow File
- **Location**: `.github/workflows/ci.yml`
- **Triggers**: Push to `main`/`develop`, Pull Requests to `main`/`develop`
- **Python Version**: 3.11

## Jobs Configured

### 1. Lint Job
- **Tool**: ruff + black
- **Steps**:
  - Checkout code
  - Setup Python 3.11 with pip cache
  - Install ruff and black
  - Run `ruff check .`
  - Run `black --check .`
- **Runs on**: ubuntu-latest

### 2. Typecheck Job
- **Tool**: mypy
- **Steps**:
  - Checkout code
  - Setup Python 3.11 with pip cache
  - Install dev dependencies (`pip install -e ".[dev]"`)
  - Run `mypy 1ai_social/`
- **Runs on**: ubuntu-latest

### 3. Test Job
- **Tool**: pytest with coverage
- **Services**: PostgreSQL 15 (test database)
- **Steps**:
  - Checkout code
  - Setup Python 3.11 with pip cache
  - Install dev dependencies
  - Run pytest with coverage reporting
  - Upload coverage to Codecov
- **Environment Variables**:
  - `DATABASE_URL`: postgresql://test_user:test_password@localhost:5432/test_1ai_social
- **Coverage Reports**: XML and terminal output
- **Runs on**: ubuntu-latest

### 4. Build Job
- **Tool**: Docker Buildx
- **Dependencies**: Requires lint, typecheck, test to pass
- **Steps**:
  - Checkout code
  - Setup Docker Buildx
  - Login to GHCR (only on main branch push)
  - Extract metadata (tags, labels)
  - Build and push Docker image
  - Cache layers via GitHub Actions cache
- **Registry**: ghcr.io
- **Image Name**: ${{ github.repository }}
- **Tags**:
  - Branch reference
  - Semantic versioning
  - Git SHA
  - `latest` (for main branch)
- **Push Condition**: Only on push to main branch
- **Runs on**: ubuntu-latest

### 5. Deploy-Staging Job
- **Dependencies**: Requires build job to pass
- **Condition**: Only runs on push to main branch
- **Environment**: staging (with URL placeholder)
- **Steps**:
  - Checkout code
  - Deploy to staging (placeholder script)
  - Verify deployment with health check
- **Runs on**: ubuntu-latest

## Required Secrets

Configure these in GitHub repository settings (Settings → Secrets and variables → Actions):

| Secret Name | Purpose | Example |
|---|---|---|
| `STAGING_DEPLOY_KEY` | SSH private key for staging deployment | (SSH key content) |
| `STAGING_DEPLOY_HOST` | Staging server hostname | staging.example.com |
| `STAGING_DEPLOY_USER` | SSH user for staging deployment | deploy |
| `STAGING_DATABASE_URL` | Staging database connection string | postgresql://user:pass@host/db |

**Note**: `GITHUB_TOKEN` is automatically provided by GitHub Actions.

## Branch Protection Rules

Recommended configuration in GitHub (Settings → Branches → Branch protection rules):

1. **Require status checks to pass before merging**:
   - ✓ lint
   - ✓ typecheck
   - ✓ test
   - ✓ build

2. **Require branches to be up to date before merging**: Enabled

3. **Require code reviews before merging**: 1 approval

4. **Dismiss stale pull request approvals when new commits are pushed**: Enabled

5. **Require conversation resolution before merging**: Enabled

## Caching Strategy

- **pip dependencies**: Cached per Python version using `actions/setup-python@v4`
- **Docker layers**: Cached via GitHub Actions cache (type=gha)

## Deployment Flow

```
Push to main
    ↓
Lint (ruff + black)
    ↓
Typecheck (mypy)
    ↓
Test (pytest + coverage)
    ↓
Build (Docker image)
    ↓
Deploy-Staging (if all pass)
```

## Local Testing

Before pushing, run locally:

```bash
# Lint
ruff check .
black --check .

# Typecheck
mypy 1ai_social/

# Test
pytest tests/ --cov=1ai_social --cov-report=term-missing

# Build
docker build -t 1ai-social:latest .
```

## Future Enhancements

- [ ] Add deploy-production job (requires approval)
- [ ] Add security scanning (Trivy, Snyk)
- [ ] Add performance benchmarking
- [ ] Add automated changelog generation
- [ ] Add Slack notifications for failures
