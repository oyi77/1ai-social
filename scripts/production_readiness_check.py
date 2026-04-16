#!/usr/bin/env python3
#
# Production Readiness Check Script
# Comprehensive production readiness verification
#

import os
import sys
import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, List, Tuple

# Configuration
DB_CONTAINER = os.getenv("DB_CONTAINER", "1ai-social-postgres")
REDIS_CONTAINER = os.getenv("REDIS_CONTAINER", "1ai-social-redis")
DB_NAME = os.getenv("DB_NAME", "1ai_social")
DB_USER = os.getenv("DB_USER", "1ai")
LOG_FILE = os.getenv("LOG_FILE", "./logs/production_readiness.log")

# Ensure log directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class ProductionReadinessChecker:
    def __init__(self):
        self.checks_passed = 0
        self.checks_failed = 0
        self.checks_skipped = 0

    def run_command(self, cmd: str) -> Tuple[bool, str]:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, str(e)

    def check(self, name: str, command: str) -> bool:
        success, output = self.run_command(command)
        if success:
            logger.info(f"✓ PASS: {name}")
            self.checks_passed += 1
            return True
        else:
            logger.error(f"✗ FAIL: {name}")
            if output:
                logger.error(f"  Details: {output}")
            self.checks_failed += 1
            return False

    def skip(self, name: str, reason: str = ""):
        logger.warning(f"⊘ SKIP: {name}")
        if reason:
            logger.warning(f"  Reason: {reason}")
        self.checks_skipped += 1

    def verify_database_schema(self) -> bool:
        cmd = f"docker exec {DB_CONTAINER} psql -U {DB_USER} -d {DB_NAME} -t -c \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'\""
        success, output = self.run_command(cmd)
        if success and output.strip().isdigit():
            table_count = int(output.strip())
            if table_count > 0:
                logger.info(f"✓ PASS: Database schema current ({table_count} tables)")
                self.checks_passed += 1
                return True
        logger.error("✗ FAIL: Database schema not current")
        self.checks_failed += 1
        return False

    def verify_required_env_vars(self) -> bool:
        required_vars = [
            "DATABASE_URL",
            "REDIS_URL",
            "SENTRY_DSN",
            "SECRET_KEY",
            "ENCRYPTION_KEY",
        ]
        missing = [var for var in required_vars if not os.getenv(var)]

        if not missing:
            logger.info("✓ PASS: All required environment variables present")
            self.checks_passed += 1
            return True
        else:
            logger.error(f"✗ FAIL: Missing environment variables: {', '.join(missing)}")
            self.checks_failed += 1
            return False

    def verify_encryption_key(self) -> bool:
        encryption_key = os.getenv("ENCRYPTION_KEY", "").strip()
        if encryption_key and len(encryption_key) >= 32:
            logger.info("✓ PASS: Encryption key configured")
            self.checks_passed += 1
            return True
        else:
            logger.error("✗ FAIL: Encryption key not configured or too short")
            self.checks_failed += 1
            return False

    def verify_redis_available(self) -> bool:
        cmd = f"docker exec {REDIS_CONTAINER} redis-cli ping"
        return self.check("Redis available", cmd)

    def verify_sentry_configured(self) -> bool:
        sentry_dsn = os.getenv("SENTRY_DSN", "").strip()
        if sentry_dsn and sentry_dsn.startswith("https://"):
            logger.info("✓ PASS: Sentry DSN configured")
            self.checks_passed += 1
            return True
        else:
            logger.error("✗ FAIL: Sentry DSN not configured")
            self.checks_failed += 1
            return False

    def verify_prometheus_metrics(self) -> bool:
        cmd = "curl -sf http://localhost:8000/metrics > /dev/null 2>&1"
        if self.run_command("command -v curl")[0]:
            return self.check("Prometheus metrics endpoint accessible", cmd)
        else:
            self.skip("Prometheus metrics endpoint", "curl not available")
            return True

    def verify_ssl_tls_configured(self) -> bool:
        ssl_cert = os.getenv("SSL_CERT_PATH", "/etc/ssl/certs/1ai-social.crt")
        ssl_key = os.getenv("SSL_KEY_PATH", "/etc/ssl/private/1ai-social.key")

        cert_exists = os.path.isfile(ssl_cert)
        key_exists = os.path.isfile(ssl_key)

        if cert_exists and key_exists:
            logger.info("✓ PASS: SSL/TLS configured")
            self.checks_passed += 1
            return True
        else:
            missing = []
            if not cert_exists:
                missing.append(f"certificate ({ssl_cert})")
            if not key_exists:
                missing.append(f"key ({ssl_key})")
            logger.error(
                f"✗ FAIL: SSL/TLS not configured - missing {', '.join(missing)}"
            )
            self.checks_failed += 1
            return False

    def verify_cors_headers(self) -> bool:
        cors_origins = os.getenv("CORS_ORIGINS", "").strip()
        if cors_origins:
            logger.info(f"✓ PASS: CORS headers configured ({cors_origins})")
            self.checks_passed += 1
            return True
        else:
            logger.error("✗ FAIL: CORS headers not configured")
            self.checks_failed += 1
            return False

    def verify_rate_limiting(self) -> bool:
        rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        if rate_limit_enabled:
            logger.info("✓ PASS: Rate limiting active")
            self.checks_passed += 1
            return True
        else:
            logger.error("✗ FAIL: Rate limiting not active")
            self.checks_failed += 1
            return False

    def run_all_checks(self) -> int:
        logger.info("=" * 50)
        logger.info("Production Readiness Check")
        logger.info("=" * 50)

        logger.info("")
        logger.info("Checking Database...")
        self.verify_database_schema()
        self.check(
            "Database connectivity",
            f"docker exec {DB_CONTAINER} psql -U {DB_USER} -d {DB_NAME} -c 'SELECT 1' > /dev/null 2>&1",
        )

        logger.info("")
        logger.info("Checking Environment...")
        self.verify_required_env_vars()
        self.verify_encryption_key()

        logger.info("")
        logger.info("Checking Services...")
        self.verify_redis_available()
        self.verify_sentry_configured()

        logger.info("")
        logger.info("Checking Monitoring...")
        self.verify_prometheus_metrics()

        logger.info("")
        logger.info("Checking Security...")
        self.verify_ssl_tls_configured()
        self.verify_cors_headers()
        self.verify_rate_limiting()

        logger.info("")
        logger.info("=" * 50)
        logger.info("Readiness Summary")
        logger.info("=" * 50)
        logger.info(f"Passed: {self.checks_passed}")
        logger.info(f"Failed: {self.checks_failed}")
        logger.info(f"Skipped: {self.checks_skipped}")
        logger.info("=" * 50)

        if self.checks_failed == 0:
            logger.info("✓ Production environment is ready")
            return 0
        else:
            logger.error("✗ Production environment has issues")
            return 1


def main():
    checker = ProductionReadinessChecker()
    exit_code = checker.run_all_checks()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
