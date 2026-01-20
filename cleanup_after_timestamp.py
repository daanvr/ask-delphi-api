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
import json
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

from askdelphi_client import AskDelphiClient


# Output files
REPORT_FILE = "cleanup_report.txt"
JSON_EXPORT_FILE = "cleanup_topics_dump.json"


class Logger:
    """Simple logger that writes to both console and file."""

    def __init__(self, filename: str):
        self.filename = filename
        self.file = open(filename, "w", encoding="utf-8")
        self.file.write(f"Cleanup Report - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.file.write("=" * 80 + "\n\n")

    def log(self, message: str = "", end: str = "\n", flush: bool = False):
        """Write to both console and file."""
        print(message, end=end, flush=flush)
        self.file.write(message + end)
        if flush:
            self.file.flush()

    def close(self):
        self.file.close()


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


def get_topic_timestamp(topic: Dict[str, Any]) -> Optional[datetime]:
    """Extract timestamp from a topic, with fallback to modification date."""
    # Try createdAt first (primary)
    ts_str = topic.get("createdAt") or topic.get("created")

    # Fallback to modifiedAt / lastModificationDate
    if not ts_str:
        ts_str = (
            topic.get("modifiedAt") or
            topic.get("modified") or
            topic.get("lastModificationDate")
        )

    if not ts_str:
        return None

    try:
        # Handle ISO format with timezone
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1]
        if "+" in ts_str:
            ts_str = ts_str.split("+")[0]

        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return None


def get_topic_timestamp_source(topic: Dict[str, Any]) -> str:
    """Return which field the timestamp came from."""
    if topic.get("createdAt") or topic.get("created"):
        return "createdAt"
    if topic.get("modifiedAt") or topic.get("modified") or topic.get("lastModificationDate"):
        return "lastModified"
    return "none"


def get_topic_id(topic: Dict[str, Any]) -> Optional[str]:
    """Extract topic ID from a topic (handles different API response formats)."""
    return topic.get("topicId") or topic.get("topicGuid")


def get_topic_version_id(topic: Dict[str, Any]) -> Optional[str]:
    """Extract topic version ID from a topic (handles different API response formats)."""
    return topic.get("topicVersionId") or topic.get("topicVersionKey")


def get_topic_title(topic: Dict[str, Any]) -> str:
    """Extract topic title from a topic (handles different API response formats)."""
    return topic.get("topicTitle") or topic.get("title") or "Untitled"


def filter_topics_after_cutoff(
    topics: List[Dict[str, Any]],
    cutoff: datetime
) -> List[Dict[str, Any]]:
    """Filter topics that were created after the cutoff timestamp."""
    filtered = []

    for topic in topics:
        ts = get_topic_timestamp(topic)
        if ts and ts > cutoff:
            topic["_parsed_timestamp"] = ts
            filtered.append(topic)

    # Sort by timestamp (oldest first)
    filtered.sort(key=lambda t: t.get("_parsed_timestamp", datetime.min))

    return filtered


def print_topics_preview(logger: Logger, topics: List[Dict[str, Any]], max_display: int = 20):
    """Print a preview of topics that will be deleted."""
    logger.log(f"\nTopics to be deleted ({len(topics)} total):")
    logger.log("-" * 80)

    for i, topic in enumerate(topics[:max_display]):
        topic_id = get_topic_id(topic) or "unknown"
        title = get_topic_title(topic)[:40]
        ts = topic.get("_parsed_timestamp", "unknown")
        if isinstance(ts, datetime):
            ts = ts.strftime("%Y-%m-%d %H:%M:%S")

        logger.log(f"  {i+1:3}. [{ts}] {title:<40} ({topic_id[:8]}...)")

    if len(topics) > max_display:
        logger.log(f"  ... and {len(topics) - max_display} more topics")

    logger.log("-" * 80)


def print_recent_topics_analysis(
    logger: Logger,
    all_topics: List[Dict[str, Any]],
    topics_to_delete: set,
    cutoff: datetime,
    count: int = 50
):
    """Print the most recent topics with their timestamps and selection status."""
    logger.log(f"\n{'='*80}")
    logger.log(f"ANALYSIS: Last {count} topics by timestamp (cutoff: {cutoff.strftime('%Y-%m-%d %H:%M:%S')})")
    logger.log(f"{'='*80}")

    # Add timestamps to all topics and sort
    topics_with_ts = []
    topics_without_ts = []
    for topic in all_topics:
        ts = get_topic_timestamp(topic)
        topic["_parsed_timestamp"] = ts
        if ts:
            topics_with_ts.append(topic)
        else:
            topics_without_ts.append(topic)

    # Sort by timestamp descending (most recent first)
    topics_with_ts.sort(
        key=lambda t: t.get("_parsed_timestamp") or datetime.min,
        reverse=True
    )

    # Get topic IDs that are selected for deletion
    delete_ids = {get_topic_id(t) for t in topics_to_delete}

    logger.log(f"\n{'#':<4} {'SELECTED':<10} {'TIMESTAMP':<20} {'SOURCE':<12} {'TITLE':<35} {'ID':<10}")
    logger.log("-" * 95)

    for i, topic in enumerate(topics_with_ts[:count]):
        topic_id = get_topic_id(topic) or "unknown"
        title = get_topic_title(topic)[:33]
        ts = topic.get("_parsed_timestamp")
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "NO TIMESTAMP"
        ts_source = get_topic_timestamp_source(topic)

        is_selected = topic_id in delete_ids
        selected_str = ">> YES <<" if is_selected else "no"

        logger.log(f"{i+1:<4} {selected_str:<10} {ts_str:<20} {ts_source:<12} {title:<35} {topic_id[:8]}...")

    logger.log("-" * 95)

    # Show topics WITHOUT timestamp (these might be the missing ones!)
    if topics_without_ts:
        logger.log(f"\n{'!'*80}")
        logger.log(f"WARNING: {len(topics_without_ts)} topics have NO TIMESTAMP!")
        logger.log(f"These topics cannot be filtered by date and might be the missing ones:")
        logger.log(f"{'!'*80}")
        for i, topic in enumerate(topics_without_ts[:20]):
            topic_id = get_topic_id(topic) or "unknown"
            title = get_topic_title(topic)[:50]
            logger.log(f"  {i+1}. {title:<50} ({topic_id[:8]}...)")
        if len(topics_without_ts) > 20:
            logger.log(f"  ... and {len(topics_without_ts) - 20} more without timestamp")

    # Summary
    recent_selected = sum(1 for t in topics_with_ts[:count] if get_topic_id(t) in delete_ids)
    logger.log(f"\nSUMMARY:")
    logger.log(f"  Topics with timestamp: {len(topics_with_ts)}")
    logger.log(f"  Topics WITHOUT timestamp: {len(topics_without_ts)}")
    logger.log(f"  Total topics in project: {len(all_topics)}")
    logger.log(f"  In top {count} recent: {recent_selected} selected for deletion")
    logger.log(f"  Total selected for deletion: {len(topics_to_delete)}")


def delete_topics(
    logger: Logger,
    client: AskDelphiClient,
    topics: List[Dict[str, Any]],
    dry_run: bool = False
) -> tuple:
    """Delete the specified topics. Returns (success_count, failed_count)."""
    success = 0
    failed = 0

    total = len(topics)

    for i, topic in enumerate(topics):
        topic_id = get_topic_id(topic)
        topic_version_id = get_topic_version_id(topic)
        title = get_topic_title(topic)[:30]

        # Check if topic is checked out (from topic list data)
        is_locked = topic.get("isLocked", False)
        checked_out_by_me = topic.get("checkedOutByMe", False)

        if not topic_id:
            logger.log(f"  [{i+1}/{total}] Skipping: {title} (no topic ID found)")
            failed += 1
            continue

        if dry_run:
            locked_info = " [LOCKED]" if is_locked else ""
            logger.log(f"  [{i+1}/{total}] Would delete: {title} ({topic_id[:8]}...){locked_info}")
            success += 1
            continue

        try:
            # If topic is checked out, cancel the checkout first
            if is_locked or checked_out_by_me:
                logger.log(f"  [{i+1}/{total}] Cancelling checkout for: {title}...", end=" ", flush=True)
                try:
                    client.cancel_checkout(topic_id, topic_version_id)
                    logger.log("OK, ", end="", flush=True)
                except Exception as e:
                    logger.log(f"(cancel failed: {e}), ", end="", flush=True)

            logger.log(f"Deleting: {title}...", end=" ", flush=True)
            client.delete_topic(topic_id, topic_version_id)
            logger.log("OK")
            success += 1
        except Exception as e:
            logger.log(f"FAILED: {e}")
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

    # Initialize logger
    logger = Logger(REPORT_FILE)
    logger.log(f"Output is also being written to: {REPORT_FILE}")

    # Parse cutoff timestamp
    try:
        cutoff = parse_timestamp(args.cutoff)
        logger.log(f"Cutoff timestamp: {cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
    except ValueError as e:
        logger.log(f"Error: {e}")
        logger.close()
        sys.exit(1)

    # Initialize client
    logger.log("\nInitializing API client...")
    try:
        client = AskDelphiClient()
        client.authenticate()
    except Exception as e:
        logger.log(f"Error: Failed to authenticate: {e}")
        logger.close()
        sys.exit(1)

    # Fetch all topics
    logger.log("\nFetching all topics...")
    try:
        all_topics = client.get_all_topics(
            progress_callback=lambda cur, tot: print(f"  Fetched {cur}/{tot} topics...", end="\r")
        )
        logger.log(f"  Fetched {len(all_topics)} topics total.      ")
    except Exception as e:
        logger.log(f"Error: Failed to fetch topics: {e}")
        logger.close()
        sys.exit(1)

    # Export raw API data to JSON for debugging
    logger.log(f"\nExporting raw topic data to {JSON_EXPORT_FILE}...")
    try:
        with open(JSON_EXPORT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "export_timestamp": datetime.now().isoformat(),
                "cutoff": cutoff.isoformat(),
                "total_topics": len(all_topics),
                "topics": all_topics
            }, f, indent=2, default=str)
        logger.log(f"  Exported {len(all_topics)} topics to {JSON_EXPORT_FILE}")
    except Exception as e:
        logger.log(f"  Warning: Failed to export JSON: {e}")

    # Filter topics after cutoff
    topics_to_delete = filter_topics_after_cutoff(all_topics, cutoff)

    # Print analysis of recent topics (always, for debugging)
    print_recent_topics_analysis(logger, all_topics, topics_to_delete, cutoff, count=50)

    if not topics_to_delete:
        logger.log(f"\nNo topics found with timestamp after {cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.log("Nothing to delete.")
        logger.log(f"\nReport saved to: {REPORT_FILE}")
        logger.close()
        sys.exit(0)

    # Show preview
    print_topics_preview(logger, topics_to_delete)

    # Dry run mode
    if args.dry_run:
        logger.log("\n[DRY RUN] No topics will be deleted.")
        delete_topics(logger, client, topics_to_delete, dry_run=True)
        logger.log(f"\n[DRY RUN] Would have deleted {len(topics_to_delete)} topics.")
        logger.log(f"\nReport saved to: {REPORT_FILE}")
        logger.close()
        sys.exit(0)

    # Confirm deletion
    if not args.yes:
        logger.log(f"\nThis will DELETE {len(topics_to_delete)} topics!")
        logger.log("This action cannot be easily undone.")
        confirm = input("Are you sure? Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            logger.log("Aborted.")
            logger.log(f"\nReport saved to: {REPORT_FILE}")
            logger.close()
            sys.exit(0)

    # Delete topics
    logger.log("\nDeleting topics...")
    success, failed = delete_topics(logger, client, topics_to_delete)

    # Summary
    logger.log(f"\n{'='*50}")
    logger.log(f"Deletion complete!")
    logger.log(f"  Deleted: {success}")
    logger.log(f"  Failed:  {failed}")
    logger.log(f"{'='*50}")

    logger.log(f"\nReport saved to: {REPORT_FILE}")
    logger.close()

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
