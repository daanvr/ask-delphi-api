#!/usr/bin/env python3
"""
Ask Delphi Content Upload Script

Uploads changes from a local JSON file to an Ask Delphi project.

Usage:
    python upload_content.py data.json --dry-run          # Show what would change
    python upload_content.py data.json                    # Upload changes
    python upload_content.py data.json --original orig.json  # Compare with specific file
    python upload_content.py data.json --no-backup --force   # Skip backup and confirmation
"""

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from askdelphi_client import AskDelphiClient, logger, setup_logging


@dataclass
class ChangeReport:
    """Report of detected changes between original and modified content."""
    new_topics: List[str] = field(default_factory=list)
    modified_topics: List[Dict[str, Any]] = field(default_factory=list)
    deleted_topics: List[str] = field(default_factory=list)
    unchanged_topics: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.new_topics or self.modified_topics or self.deleted_topics)

    @property
    def total_changes(self) -> int:
        return len(self.new_topics) + len(self.modified_topics) + len(self.deleted_topics)


@dataclass
class UploadReport:
    """Report of upload results."""
    created: List[Dict[str, Any]] = field(default_factory=list)
    updated: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    dry_run: bool = False


def calculate_checksum(data: Dict[str, Any]) -> str:
    """Calculate SHA256 checksum of topic data."""
    # Remove checksum field for calculation
    data_copy = {k: v for k, v in data.items() if k != "_checksum"}
    json_str = json.dumps(data_copy, sort_keys=True, ensure_ascii=False)
    return f"sha256:{hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]}"


def load_json(file_path: str) -> Dict[str, Any]:
    """Load and validate a JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Basic validation
    if "_metadata" not in data:
        raise ValueError(f"Invalid format: missing _metadata in {file_path}")
    if "topics" not in data:
        raise ValueError(f"Invalid format: missing topics in {file_path}")

    return data

### TOEGEVOEGD ###

FIELDS_TO_IGNORE = {"version_id", "_checksum", "modified_at", "created_at"}

def normalize_topic(topic: Dict[str, Any]) -> Dict[str, Any]:
    """Remove volatile fields before comparison.""" 
    return { 
        key: ( 
            normalize_topic(value) if isinstance(value, dict) else value 
            ) 
            for key, value in topic.items() 
            if key not in FIELDS_TO_IGNORE
        }

### TOEGEVOEGD ###

def detect_changes(original: Dict[str, Any], modified: Dict[str, Any]) -> ChangeReport:
    """
    Detect changes between original and modified content.

    Args:
        original: Original exported content
        modified: Modified content to upload

    Returns:
        ChangeReport with lists of new, modified, deleted, unchanged topics
    """
    original_topics = original.get("topics", {})
    modified_topics = modified.get("topics", {})

    report = ChangeReport()

    # Check each topic in modified version
    for topic_id, topic_data in modified_topics.items():
        if topic_id not in original_topics:
            # New topic
            report.new_topics.append(topic_id)
        else:
            # Check if modified
            # orig_checksum = original_topics[topic_id].get("_checksum")
            # new_checksum = calculate_checksum(topic_data)

            ### VERVANGEN VAN REGELS HIERBOVEN ### 
            orig_clean = normalize_topic(original_topics[topic_id]) 
            new_clean = normalize_topic(topic_data) 
            
            orig_checksum = calculate_checksum(orig_clean) 
            new_checksum = calculate_checksum(new_clean)
            ### VERVANGEN VAN REGELS HIERBOVEN ###

            if orig_checksum != new_checksum:
                # Find which parts changed
                changed_parts = diff_parts(
                    original_topics[topic_id].get("parts", {}),
                    topic_data.get("parts", {})
                )

                # Check if title changed
                title_changed = (
                    original_topics[topic_id].get("title") != topic_data.get("title")
                )

                report.modified_topics.append({
                    "topic_id": topic_id,
                    "title": topic_data.get("title"),
                    "title_changed": title_changed,
                    "old_title": original_topics[topic_id].get("title"),
                    "changed_parts": changed_parts,
                    "old_checksum": orig_checksum,
                    "new_checksum": new_checksum
                })
            else:
                report.unchanged_topics.append(topic_id)

    # Check for deleted topics
    for topic_id in original_topics:
        if topic_id not in modified_topics:
            report.deleted_topics.append(topic_id)

    return report


def diff_parts(original_parts: Dict, modified_parts: Dict) -> List[Dict[str, Any]]:
    """Find which parts have changed between original and modified."""
    changes = []

    # Check modified and new parts
    for part_id, part_data in modified_parts.items():
        if part_id not in original_parts:
            changes.append({
                "part_id": part_id,
                "change_type": "new",
                "name": part_data.get("name", part_id)
            })
        else:
            orig_content = original_parts[part_id].get("content")
            new_content = part_data.get("content")

            if orig_content != new_content:
                changes.append({
                    "part_id": part_id,
                    "change_type": "modified",
                    "name": part_data.get("name", part_id)
                })

    # Check deleted parts
    for part_id in original_parts:
        if part_id not in modified_parts:
            changes.append({
                "part_id": part_id,
                "change_type": "deleted",
                "name": original_parts[part_id].get("name", part_id)
            })

    return changes


def print_change_report(report: ChangeReport, modified_data: Dict[str, Any]):
    """Print a human-readable change report."""
    print("\n" + "=" * 60)
    print("CHANGE REPORT")
    print("=" * 60)

    topics = modified_data.get("topics", {})

    if not report.has_changes:
        print("\nNo changes detected.")
        print("=" * 60 + "\n")
        return

    # New topics
    if report.new_topics:
        print(f"\n NEW TOPICS ({len(report.new_topics)}):")
        for topic_id in report.new_topics[:10]:  # Limit display
            title = topics.get(topic_id, {}).get("title", "Untitled")
            print(f"   + {title}")
            print(f"     ID: {topic_id}")
        if len(report.new_topics) > 10:
            print(f"   ... and {len(report.new_topics) - 10} more")

    # Modified topics
    if report.modified_topics:
        print(f"\n MODIFIED TOPICS ({len(report.modified_topics)}):")
        for change in report.modified_topics[:10]:
            title = change.get("title", "Untitled")
            print(f"   ~ {title}")
            if change.get("title_changed"):
                print(f"     Title: \"{change.get('old_title')}\" -> \"{title}\"")
            if change.get("changed_parts"):
                parts_summary = ", ".join(
                    p.get("name", p.get("part_id"))
                    for p in change["changed_parts"][:3]
                )
                if len(change["changed_parts"]) > 3:
                    parts_summary += f", +{len(change['changed_parts']) - 3} more"
                print(f"     Parts: {parts_summary}")
        if len(report.modified_topics) > 10:
            print(f"   ... and {len(report.modified_topics) - 10} more")

    # Deleted topics
    if report.deleted_topics:
        print(f"\n DELETED TOPICS ({len(report.deleted_topics)}):")
        print("   (Topics will NOT be auto-deleted - manual action required)")
        for topic_id in report.deleted_topics[:5]:
            print(f"   - {topic_id}")
        if len(report.deleted_topics) > 5:
            print(f"   ... and {len(report.deleted_topics) - 5} more")

    # Summary
    print("\n" + "-" * 60)
    print(f"SUMMARY: {report.total_changes} change(s)")
    print(f"  New: {len(report.new_topics)}")
    print(f"  Modified: {len(report.modified_topics)}")
    print(f"  Deleted: {len(report.deleted_topics)} (require manual action)")
    print(f"  Unchanged: {len(report.unchanged_topics)}")
    print("=" * 60 + "\n")


def create_backup(client: AskDelphiClient, backup_dir: str = ".") -> str:
    """Create a backup of current server state before upload."""
    from download_content import download_all_content

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = Path(backup_dir) / f"backup_before_upload_{timestamp}.json"

    print(f"Creating backup: {backup_file}")
    download_all_content(
        output_file=str(backup_file),
        include_parts=True,
        verbose=False
    )

    return str(backup_file)


def upload_changes(
    input_file: str,
    original_file: Optional[str] = None,
    dry_run: bool = False,
    create_backup_file: bool = True,
    force: bool = False,
    rate_limit_ms: int = 0,
    verbose: bool = False
) -> UploadReport:
    """
    Upload changes from a modified JSON file to the platform.

    Args:
        input_file: Modified JSON file to upload
        original_file: Original JSON file for comparison (auto-fetch if None)
        dry_run: Only show what would change, don't upload
        create_backup_file: Create backup before uploading
        force: Skip confirmation prompt
        rate_limit_ms: Delay between API calls

    Returns:
        UploadReport with results
    """
    setup_logging(verbose=verbose)

    print("\n" + "=" * 60)
    print("ASK DELPHI CONTENT UPLOAD")
    print("=" * 60 + "\n")

    # Load modified file
    print(f"Loading modified file: {input_file}")
    modified_data = load_json(input_file)
    print(f"  Topics in file: {len(modified_data.get('topics', {}))}")

    # Initialize client
    print("\nInitializing client...")
    client = AskDelphiClient()
    client.authenticate()
    print("Authentication successful!")

    # Load or fetch original data
    if original_file:
        print(f"\nLoading original file: {original_file}")
        original_data = load_json(original_file)
    else:
        print("\nNo original file provided. Fetching current state from server...")
        # Import here to avoid circular import
        from download_content import download_all_content

        temp_file = f".temp_original_{datetime.now().strftime('%H%M%S')}.json"
        download_all_content(
            output_file=temp_file,
            include_parts=True,
            verbose=False
        )
        original_data = load_json(temp_file)
        # Clean up temp file
        Path(temp_file).unlink()

    print(f"  Topics in original: {len(original_data.get('topics', {}))}")

    # Detect changes
    print("\nDetecting changes...")
    changes = detect_changes(original_data, modified_data)

    # Print report
    print_change_report(changes, modified_data)

    # Dry run mode
    if dry_run:
        print("DRY RUN MODE - No changes were made.")
        return UploadReport(dry_run=True)

    if not changes.has_changes:
        print("No changes to upload.")
        return UploadReport()

    # Confirmation
    if not force:
        print(f"About to upload {changes.total_changes} change(s).")
        response = input("Continue? [y/N]: ").strip().lower()
        if response != 'y':
            print("Upload cancelled.")
            return UploadReport()

    # Create backup
    if create_backup_file:
        try:
            backup_path = create_backup(client)
            print(f"Backup created: {backup_path}\n")
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")
            if not force:
                response = input("Continue without backup? [y/N]: ").strip().lower()
                if response != 'y':
                    print("Upload cancelled.")
                    return UploadReport()

    # Process changes
    report = UploadReport()
    topics = modified_data.get("topics", {})

    # Process new topics
    if changes.new_topics:
        print(f"\nCreating {len(changes.new_topics)} new topic(s)...")
        for topic_id in changes.new_topics:
            topic_data = topics[topic_id]
            try:
                result = client.create_topic(
                    title=topic_data.get("title", "Untitled"),
                    topic_type_id=topic_data.get("topic_type_id")
                )
                report.created.append({
                    "topic_id": topic_id,
                    "title": topic_data.get("title"),
                    "new_id": result.get("topicId")
                })
                print(f"  + Created: {topic_data.get('title')}")

                # TODO: Set parts for new topic
                # This would require additional API calls

            except Exception as e:
                report.errors.append({
                    "topic_id": topic_id,
                    "title": topic_data.get("title"),
                    "error": str(e)
                })
                print(f"  ! Error creating {topic_data.get('title')}: {e}")

            time.sleep(rate_limit_ms / 1000)

    # Process modified topics
    if changes.modified_topics:
        print(f"\nUpdating {len(changes.modified_topics)} modified topic(s)...")
        for change in changes.modified_topics:
            topic_id = change["topic_id"]
            topic_data = topics[topic_id]
            version_id = topic_data.get("version_id")

            try:
                # First, try to reset any existing checkout (cancel or checkin)
                # This ensures we have a clean state before our checkout
                try:
                    current_version = None
                    search_result = client.search_topics(query="", limit=1000)
                    topic_list = search_result.get("topicList", {}).get("result", [])
                    for t in topic_list:
                        tid = t.get("topicGuid") or t.get("topicId")
                        if tid == topic_id:
                            current_version = t.get("topicVersionKey") or t.get("topicVersionId")
                            break

                    if current_version:
                        # Try to cancel any existing checkout first
                        try:
                            client.cancel_checkout(topic_id, current_version)
                            logger.info(f"Cancelled existing checkout for {topic_id}")
                        except:
                            pass  # Ignore if cancel fails (might not be checked out)
                except Exception as e:
                    logger.debug(f"Could not reset checkout state: {e}")

                # Checkout
                new_version_id = client.checkout_topic(topic_id)
                print(f"  ~ Updating: {topic_data.get('title')}")

                # update title if changed
                if change.get("title_changed"):
                    try:
                        client.update_topic_metadata(
                            topic_id,
                            new_version_id,
                            title=topic_data.get("title")
                        )
                        
                        print(f'    Title updated: "{change.get("old_title")}" -> "{topic_data.get("title")}"')
                    except Exception as e:
                        logger.error(f"Failed to update title {e}")

                # Update changed parts
                parts_updated = 0
                for part_change in change.get("changed_parts", []):
                    if part_change["change_type"] in ["new", "modified"]:
                        part_id = part_change["part_id"]
                        part_data = topic_data.get("parts", {}).get(part_id, {})

                        try:
                            client.update_topic_part(
                                topic_id,
                                new_version_id,
                                part_id,
                                part_data
                            )
                            parts_updated += 1
                        except Exception as e:
                            logger.error(f"Failed to update part {part_id}: {e}")

                # Checkin
                client.checkin_topic(topic_id, new_version_id)

                report.updated.append({
                    "topic_id": topic_id,
                    "title": topic_data.get("title"),
                    "parts_updated": parts_updated
                })

            except Exception as e:
                report.errors.append({
                    "topic_id": topic_id,
                    "title": topic_data.get("title"),
                    "error": str(e)
                })
                print(f"  ! Error updating {topic_data.get('title')}: {e}")

                # Try to cancel checkout
                try:
                    client.cancel_checkout(topic_id, version_id)
                except:
                    pass

            time.sleep(rate_limit_ms / 1000)

    # Log deleted topics (no auto-delete)
    for topic_id in changes.deleted_topics:
        report.warnings.append({
            "topic_id": topic_id,
            "message": "Topic removed from local file but not deleted on server"
        })

    # Print summary
    print("\n" + "=" * 60)
    print("UPLOAD COMPLETE")
    print("=" * 60)
    print(f"  Created: {len(report.created)}")
    print(f"  Updated: {len(report.updated)}")
    print(f"  Errors: {len(report.errors)}")
    print(f"  Warnings: {len(report.warnings)}")

    if report.errors:
        print("\nErrors:")
        for error in report.errors:
            print(f"  - {error.get('title')}: {error.get('error')}")

    print("=" * 60 + "\n")

    return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload content changes to Ask Delphi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s data.json --dry-run           Show what would change
  %(prog)s data.json                     Upload changes
  %(prog)s data.json --original orig.json  Compare with specific file
  %(prog)s data.json --no-backup --force   Skip backup and confirmation
        """
    )

    parser.add_argument(
        "input_file",
        metavar="INPUT_FILE",
        help="Modified JSON file to upload"
    )
    parser.add_argument(
        "--original",
        metavar="FILE",
        help="Original JSON file for comparison (auto-fetch if not provided)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without uploading"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup before upload"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt"
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=0,
        metavar="MS",
        help="Delay between API calls in milliseconds (default: 0, no delay)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed progress information"
    )

    args = parser.parse_args()

    try:
        report = upload_changes(
            input_file=args.input_file,
            original_file=args.original,
            dry_run=args.dry_run,
            create_backup_file=not args.no_backup,
            force=args.force,
            rate_limit_ms=args.rate_limit,
            verbose=args.verbose
        )

        if report.errors:
            print(f"Completed with {len(report.errors)} error(s)")
            return 1

        if report.dry_run:
            print("Dry run completed successfully")
        else:
            print("Upload completed successfully")
        return 0

    except KeyboardInterrupt:
        print("\n\nUpload cancelled by user")
        return 1
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        return 1
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        print(f"\nError: {e}")
        print("Check askdelphi_debug.log for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
