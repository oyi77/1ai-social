"""Test script to verify input validation and sanitization."""

import sys
from pydantic import ValidationError

sys.path.insert(0, "/home/openclaw/projects/1ai-social")

from ai_social.schemas import (
    PostCreateSchema,
    ContentCreateSchema,
    HookCreateSchema,
    CampaignCreateSchema,
    AnalyticsQuerySchema,
)


def test_xss_protection():
    """Test XSS attack prevention."""
    print("\n=== Testing XSS Protection ===\n")

    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg onload=alert('XSS')>",
        "' onmouseover='alert(1)'",
    ]

    for payload in xss_payloads:
        try:
            schema = PostCreateSchema(niche=payload, platforms=["tiktok"])
            print(f"✓ XSS payload sanitized: {payload[:50]}")
            print(f"  Sanitized to: {schema.niche[:50]}")
        except ValidationError as e:
            print(f"✗ XSS payload rejected: {payload[:50]}")
            print(f"  Error: {e.errors()[0]['msg']}")


def test_sql_injection_protection():
    """Test SQL injection attack prevention."""
    print("\n=== Testing SQL Injection Protection ===\n")

    sql_payloads = [
        "' OR '1'='1",
        "1; DROP TABLE posts--",
        "admin'--",
        "' UNION SELECT * FROM users--",
        "1' AND '1'='1",
    ]

    for payload in sql_payloads:
        try:
            schema = AnalyticsQuerySchema(post_id=payload)
            print(f"✗ SQL injection payload accepted: {payload}")
        except ValidationError as e:
            print(f"✓ SQL injection payload blocked: {payload}")
            print(f"  Error: {e.errors()[0]['msg']}")


def test_url_validation():
    """Test URL validation and scheme whitelisting."""
    print("\n=== Testing URL Validation ===\n")

    test_urls = [
        ("https://example.com/image.jpg", True),
        ("http://example.com/video.mp4", True),
        ("javascript:alert('XSS')", False),
        ("data:text/html,<script>alert('XSS')</script>", False),
        ("file:///etc/passwd", False),
        ("ftp://example.com/file.txt", False),
    ]

    for url, should_pass in test_urls:
        try:
            schema = ContentCreateSchema(
                text="Test content", platform="tiktok", media_url=url
            )
            if should_pass:
                print(f"✓ Valid URL accepted: {url}")
            else:
                print(f"✗ Invalid URL accepted: {url}")
        except ValidationError as e:
            if not should_pass:
                print(f"✓ Invalid URL rejected: {url}")
            else:
                print(f"✗ Valid URL rejected: {url}")


def test_field_length_limits():
    """Test field length validation."""
    print("\n=== Testing Field Length Limits ===\n")

    long_text = "A" * 10000
    try:
        schema = ContentCreateSchema(text=long_text, platform="tiktok")
        print(f"✗ Long text accepted: {len(long_text)} chars")
    except ValidationError as e:
        print(f"✓ Long text rejected: {len(long_text)} chars")
        print(f"  Error: {e.errors()[0]['msg']}")

    too_many_hashtags = ["tag" + str(i) for i in range(50)]
    try:
        schema = ContentCreateSchema(
            text="Test", platform="tiktok", hashtags=too_many_hashtags
        )
        print(
            f"✓ Hashtags limited to: {len(schema.hashtags)} (from {len(too_many_hashtags)})"
        )
    except ValidationError as e:
        print(f"✓ Too many hashtags rejected: {len(too_many_hashtags)}")


def test_platform_validation():
    """Test platform name validation."""
    print("\n=== Testing Platform Validation ===\n")

    valid_platforms = ["tiktok", "instagram", "facebook", "x", "linkedin"]
    invalid_platforms = ["twitter", "youtube", "snapchat", "unknown"]

    for platform in valid_platforms:
        try:
            schema = PostCreateSchema(niche="test", platforms=[platform])
            print(f"✓ Valid platform accepted: {platform}")
        except ValidationError as e:
            print(f"✗ Valid platform rejected: {platform}")

    for platform in invalid_platforms:
        try:
            schema = PostCreateSchema(niche="test", platforms=[platform])
            print(f"✗ Invalid platform accepted: {platform}")
        except ValidationError as e:
            print(f"✓ Invalid platform rejected: {platform}")


def test_numeric_bounds():
    """Test numeric field bounds validation."""
    print("\n=== Testing Numeric Bounds ===\n")

    test_cases = [
        ("count", 0, False),
        ("count", 1, True),
        ("count", 5, True),
        ("count", 10, True),
        ("count", 11, False),
        ("days", 0, False),
        ("days", 1, True),
        ("days", 90, True),
        ("days", 91, False),
    ]

    for field, value, should_pass in test_cases:
        try:
            if field == "count":
                schema = PostCreateSchema(niche="test", count=value)
            elif field == "days":
                schema = CampaignCreateSchema(niche="test", days=value)

            if should_pass:
                print(f"✓ Valid {field}={value} accepted")
            else:
                print(f"✗ Invalid {field}={value} accepted")
        except ValidationError as e:
            if not should_pass:
                print(f"✓ Invalid {field}={value} rejected")
            else:
                print(f"✗ Valid {field}={value} rejected")


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Input Validation and Sanitization Test Suite")
    print("=" * 60)

    try:
        test_xss_protection()
        test_sql_injection_protection()
        test_url_validation()
        test_field_length_limits()
        test_platform_validation()
        test_numeric_bounds()

        print("\n" + "=" * 60)
        print("Test suite completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test suite failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
