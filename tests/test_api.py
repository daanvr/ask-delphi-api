#!/usr/bin/env python3
"""
Ask Delphi API Test Script

This script tests the API connection and demonstrates basic operations.
Run this to verify your setup is working correctly.

Usage:
    python test_api.py [test_name]

    test_name can be:
        auth        - Test authentication only
        design      - Get content design (topic types)
        search      - Search for topics
        create      - Create a test topic
        full        - Run all tests (default)
"""

import sys
import json
from src.askdelphi_client import AskDelphiClient


def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_json(data, max_lines: int = 30):
    """Print JSON data nicely formatted."""
    output = json.dumps(data, indent=2, default=str)
    lines = output.split("\n")
    if len(lines) > max_lines:
        print("\n".join(lines[:max_lines]))
        print(f"... ({len(lines) - max_lines} more lines)")
    else:
        print(output)


def test_authentication(client: AskDelphiClient) -> bool:
    """Test 1: Authentication"""
    print_header("TEST 1: Authentication")

    try:
        client.authenticate()
        print("SUCCESS: Authentication completed!")
        print(f"  - Tenant ID: {client.tenant_id}")
        print(f"  - Project ID: {client.project_id}")
        print(f"  - ACL Entry ID: {client.acl_entry_id}")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False


def test_content_design(client: AskDelphiClient) -> dict:
    """Test 2: Get content design (topic types)"""
    print_header("TEST 2: Content Design (Topic Types)")

    try:
        design = client.get_content_design()

        topic_types = design.get("topicTypes", [])
        print(f"Found {len(topic_types)} topic types:\n")

        for i, tt in enumerate(topic_types[:10]):  # Show first 10
            print(f"  {i+1}. {tt.get('title', 'Unknown')}")
            print(f"     ID: {tt.get('key', 'N/A')}")
            print(f"     Namespace: {tt.get('namespace', 'N/A')}")
            print()

        if len(topic_types) > 10:
            print(f"  ... and {len(topic_types) - 10} more")

        return design
    except Exception as e:
        print(f"FAILED: {e}")
        return {}


def test_search_topics(client: AskDelphiClient) -> dict:
    """Test 3: Search topics"""
    print_header("TEST 3: Search Topics")

    try:
        # Search for all topics (empty query)
        result = client.search_topics(query="", limit=5)

        items = result.get("items", result.get("data", []))
        total = result.get("total", result.get("totalCount", len(items)))

        print(f"Found {total} total topics, showing first {len(items)}:\n")

        for i, topic in enumerate(items):
            print(f"  {i+1}. {topic.get('title', 'Untitled')}")
            print(f"     ID: {topic.get('topicId', topic.get('id', 'N/A'))}")
            print(f"     Type: {topic.get('topicTypeTitle', topic.get('typeName', 'Unknown'))}")
            print()

        return result
    except Exception as e:
        print(f"FAILED: {e}")
        return {}


def test_create_topic(client: AskDelphiClient, topic_type_id: str = None) -> dict:
    """Test 4: Create a test topic"""
    print_header("TEST 4: Create Topic")

    if not topic_type_id:
        print("Skipping topic creation - no topic_type_id provided")
        print("To create a topic, first run 'design' test to get topic type IDs")
        print("Then run: python test_api.py create <topic_type_id>")
        return {}

    try:
        import uuid
        test_title = f"API Test Topic {str(uuid.uuid4())[:8]}"

        print(f"Creating topic: '{test_title}'")
        print(f"Topic type ID: {topic_type_id}")
        print()

        result = client.create_topic(
            title=test_title,
            topic_type_id=topic_type_id
        )

        print("SUCCESS: Topic created!")
        print(f"  - Topic ID: {result.get('topicId')}")
        print(f"  - Version ID: {result.get('topicVersionKey')}")

        return result
    except Exception as e:
        print(f"FAILED: {e}")
        return {}


def test_topic_parts(client: AskDelphiClient, topic_id: str, version_id: str) -> dict:
    """Test 5: Get topic parts"""
    print_header("TEST 5: Get Topic Parts")

    try:
        parts = client.get_topic_parts(topic_id, version_id)

        print(f"Topic parts structure:\n")
        print_json(parts, max_lines=50)

        return parts
    except Exception as e:
        print(f"FAILED: {e}")
        return {}


def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "=" * 60)
    print("  ASK DELPHI API TEST SUITE")
    print("=" * 60)

    # Initialize client
    try:
        client = AskDelphiClient()
    except Exception as e:
        print(f"\nFailed to initialize client: {e}")
        print("\nMake sure you have:")
        print("  1. Copied .env.example to .env")
        print("  2. Filled in your credentials in .env")
        return

    # Test 1: Authentication
    if not test_authentication(client):
        print("\nAuthentication failed. Cannot continue with other tests.")
        return

    # Test 2: Content Design
    design = test_content_design(client)

    # Test 3: Search Topics
    search_result = test_search_topics(client)

    # Test 4 & 5: Create topic and get parts (optional)
    print_header("SUMMARY")

    print("Completed tests:")
    print("  [x] Authentication")
    print("  [x] Content Design")
    print("  [x] Topic Search")
    print()
    print("To test topic creation:")
    print("  1. Pick a topic type ID from the 'Content Design' output above")
    print("  2. Run: python test_api.py create <topic_type_id>")
    print()
    print("Example:")

    topic_types = design.get("topicTypes", [])
    if topic_types:
        example_type = topic_types[0]
        print(f"  python test_api.py create {example_type.get('key')}")


def main():
    """Main entry point."""
    args = sys.argv[1:]

    if not args or args[0] == "full":
        run_all_tests()
        return

    # Initialize client
    try:
        client = AskDelphiClient()
    except Exception as e:
        print(f"Failed to initialize client: {e}")
        return

    # Always authenticate first
    if not test_authentication(client):
        return

    test_name = args[0].lower()

    if test_name == "auth":
        # Already done above
        pass

    elif test_name == "design":
        test_content_design(client)

    elif test_name == "search":
        query = args[1] if len(args) > 1 else ""
        print_header(f"Search Topics: '{query}'")
        result = client.search_topics(query=query, limit=10)
        print_json(result)

    elif test_name == "create":
        if len(args) < 2:
            print("Usage: python test_api.py create <topic_type_id>")
            print("\nRun 'python test_api.py design' to see available topic types")
            return
        topic_type_id = args[1]
        result = test_create_topic(client, topic_type_id)
        if result:
            topic_id = result.get("topicId")
            version_id = result.get("topicVersionKey")
            print("\nTo get topic parts, run:")
            print(f"  python test_api.py parts {topic_id} {version_id}")

    elif test_name == "parts":
        if len(args) < 3:
            print("Usage: python test_api.py parts <topic_id> <version_id>")
            return
        test_topic_parts(client, args[1], args[2])

    else:
        print(f"Unknown test: {test_name}")
        print("Available tests: auth, design, search, create, parts, full")


if __name__ == "__main__":
    main()
