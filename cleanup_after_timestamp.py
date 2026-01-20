#!/usr/bin/env python3
"""
Cleanup script - Delete all topics created after a specific timestamp.
Useful for resetting a test environment to a known state.

Usage:
    python cleanup_after_timestamp.py --cutoff "2025-01-15T12:00:00" --dry-run
    python cleanup_after_timestamp.py --cutoff "2025-01-15T12:00:00"
    python cleanup_after_timestamp.py --cutoff "2025-01-15T12:00:00" --yes
"""

import argparse
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

from askdelphi_client import AskDelphiClient


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse a timestamp string into a datetime object."""
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str, fmt)
        except ValueError:
            continue

    raise ValueError(
        f"Could not parse timestamp '{timestamp_str}'. "
        f"Expected format like: 2025-01-15T12:00:00 or 2025-01-15"
    )


def get_topic_created_at(topic: Dict[str, Any]) -> Optional[datetime]:
    """Extract creation timestamp from a topic, with fallback to modification date."""
    # Try createdAt first (primary)
    created_str = topic.get("createdAt") or topic.get("created")

    # Fallback to modifiedAt
    if not created_str:
        created_str = (
            topic.get("modifiedAt") or
            topic.get("modified") or
            topic.get("lastModificationDate")
        )

    if not created_str:
        return None

    try:
        # Handle ISO format with timezone
        if created_str.endswith("Z"):
            created_str = created_str[:-1]
        if "+" in created_str:
            created_str = created_str.split("+")[0]

        return datetime.fromisoformat(created_str)
    except (ValueError, TypeError):
        return None


def filter_topics_after_cutoff(
    topics: List[Dict[str, Any]],
    cutoff: datetime
) -> List[Dict[str, Any]]:
    """Filter topics that were created after the cutoff timestamp."""
    filtered = []

    for topic in topics:
        created_at = get_topic_created_at(topic)
        if created_at and created_at > cutoff:
            topic["_parsed_created_at"] = created_at
            filtered.append(topic)

    # Sort by creation date (oldest first)
    filtered.sort(key=lambda t: t.get("_parsed_created_at", datetime.min))

    return filtered


def print_topics_preview(topics: List[Dict[str, Any]], max_display: int = 20):
    """Print a preview of topics that will be deleted."""
    print(f"\nTopics to be deleted ({len(topics)} total):")
    print("-" * 70)

    for i, topic in enumerate(topics[:max_display]):
        topic_id = topic.get("topicId", "unknown")
        title = topic.get("topicTitle", "Untitled")[:40]
        created = topic.get("_parsed_created_at", "unknown")
        if isinstance(created, datetime):
            created = created.strftime("%Y-%m-%d %H:%M")

        print(f"  {i+1:3}. [{created}] {title:<40} ({topic_id[:8]}...)")

    if len(topics) > max_display:
        print(f"  ... and {len(topics) - max_display} more topics")

    print("-" * 70)


def delete_topics(
    client: AskDelphiClient,
    topics: List[Dict[str, Any]],
    dry_run: bool = False
) -> tuple:
    """Delete the specified topics. Returns (success_count, failed_count)."""
    success = 0
    failed = 0

    total = len(topics)

    for i, topic in enumerate(topics):
        topic_id = topic.get("topicId")
        title = topic.get("topicTitle", "Untitled")[:30]

        if dry_run:
            print(f"  [{i+1}/{total}] Would delete: {title} ({topic_id[:8]}...)")
            success += 1
            continue

        try:
            print(f"  [{i+1}/{total}] Deleting: {title}...", end=" ", flush=True)
            client.delete_topic(topic_id)
            print("OK")
            success += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

    return success, failed


def main():
    parser = argparse.ArgumentParser(
        description="Delete all topics created after a specific timestamp.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview what would be deleted
  python cleanup_after_timestamp.py --cutoff "2025-01-15T12:00:00" --dry-run

  # Delete with confirmation prompt
  python cleanup_after_timestamp.py --cutoff "2025-01-15T12:00:00"

  # Delete without confirmation
  python cleanup_after_timestamp.py --cutoff "2025-01-15T12:00:00" --yes
        """
    )

    parser.add_argument(
        "--cutoff", "-c",
        required=True,
        help="Delete topics created AFTER this timestamp (e.g., '2025-01-15T12:00:00')"
    )

    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )

    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    # Parse cutoff timestamp
    try:
        cutoff = parse_timestamp(args.cutoff)
        print(f"Cutoff timestamp: {cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Initialize client
    print("\nInitializing API client...")
    try:
        client = AskDelphiClient()
        client.authenticate()
    except Exception as e:
        print(f"Error: Failed to authenticate: {e}")
        sys.exit(1)

    # Fetch all topics
    print("\nFetching all topics...")
    try:
        all_topics = client.get_all_topics(
            progress_callback=lambda cur, tot: print(f"  Fetched {cur}/{tot} topics...", end="\r")
        )
        print(f"  Fetched {len(all_topics)} topics total.      ")
    except Exception as e:
        print(f"Error: Failed to fetch topics: {e}")
        sys.exit(1)

    # Filter topics after cutoff
    topics_to_delete = filter_topics_after_cutoff(all_topics, cutoff)

    if not topics_to_delete:
        print(f"\nNo topics found created after {cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
        print("Nothing to delete.")
        sys.exit(0)

    # Show preview
    print_topics_preview(topics_to_delete)

    # Dry run mode
    if args.dry_run:
        print("\n[DRY RUN] No topics will be deleted.")
        delete_topics(client, topics_to_delete, dry_run=True)
        print(f"\n[DRY RUN] Would have deleted {len(topics_to_delete)} topics.")
        sys.exit(0)

    # Confirm deletion
    if not args.yes:
        print(f"\nThis will DELETE {len(topics_to_delete)} topics!")
        print("This action cannot be easily undone.")
        confirm = input("Are you sure? Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    # Delete topics
    print("\nDeleting topics...")
    success, failed = delete_topics(client, topics_to_delete)

    # Summary
    print(f"\n{'='*50}")
    print(f"Deletion complete!")
    print(f"  Deleted: {success}")
    print(f"  Failed:  {failed}")
    print(f"{'='*50}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
