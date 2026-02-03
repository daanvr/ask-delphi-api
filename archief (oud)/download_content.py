#!/usr/bin/env python3
"""
Ask Delphi Content Download Script

Downloads all content from an Ask Delphi project to a JSON file.

Usage:
    python download_content.py                     # Download all content (10 parallel)
    python download_content.py -o backup.json      # Save to specific file
    python download_content.py -w 20               # Use 20 parallel workers (faster)
    python download_content.py -w 1                # Sequential (1 at a time)
    python download_content.py --no-parts          # Metadata only (fastest)
"""

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("Note: Install 'tqdm' for progress bars: pip install tqdm")

from askdelphi_client_oud import AskDelphiClient, logger, setup_logging


def calculate_checksum(data: Dict[str, Any]) -> str:
    """Calculate SHA256 checksum of topic data for change detection."""
    # Create a stable JSON string (sorted keys)
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return f"sha256:{hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]}"


def create_progress_bar(desc: str, total: int):
    """Create a progress bar (or fallback to simple counter)."""
    if HAS_TQDM:
        return tqdm(total=total, desc=desc, unit="topics")
    else:
        # Simple fallback
        class SimpleProgress:
            def __init__(self, total, desc):
                self.current = 0
                self.total = total
                self.desc = desc

            def update(self, n=1):
                self.current += n
                print(f"\r{self.desc}: {self.current}/{self.total}", end="", flush=True)

            def close(self):
                print()  # Newline

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        return SimpleProgress(total, desc)


def download_all_content(
    output_file: Optional[str] = None,
    include_parts: bool = True,
    topic_type_ids: Optional[List[str]] = None,
    workers: int = 10,
    verbose: bool = False
) -> str:
    """
    Download all content from Ask Delphi to a JSON file.

    Args:
        output_file: Path to output file (auto-generated if None)
        include_parts: Whether to download topic parts (content)
        topic_type_ids: Optional filter by topic type IDs
        workers: Number of parallel downloads (default: 10)
        verbose: Show detailed progress

    Returns:
        Path to the generated file
    """
    # Setup logging
    setup_logging(verbose=verbose)

    print("\n" + "=" * 60)
    print("ASK DELPHI CONTENT DOWNLOAD")
    print("=" * 60 + "\n")

    # Initialize client
    print("Initializing client...")
    client = AskDelphiClient()

    # Authenticate
    print("Authenticating...")
    client.authenticate()
    print("Authentication successful!\n")

    # Step 1: Get content design
    print("Fetching content design (topic types, relations)...")
    content_design = client.get_content_design()

    topic_types = content_design.get("topicTypes", [])
    print(f"  Found {len(topic_types)} topic types")

    # Step 2: Get all topics
    print("\nFetching topic list...")
    all_topics = client.get_all_topics(
        topic_type_ids=topic_type_ids,
        page_size=50
    )
    print(f"  Found {len(all_topics)} topics")

    if not all_topics:
        print("\nNo topics found. Creating empty export...")
        topics_dict = {}
    else:
        # Step 3: Fetch parts for each topic
        topics_dict = {}

        if include_parts:
            print(f"\nDownloading topic content & relations ({workers} parallel workers)...")

            def fetch_topic_data(topic: Dict) -> Tuple[str, Dict, Dict, Dict]:
                """Fetch parts and relations for a single topic (runs in thread)."""
                topic_id = topic.get("topicId") or topic.get("topicGuid")
                version_id = topic.get("topicVersionId") or topic.get("topicVersionKey")

                if not topic_id or not version_id:
                    return None, topic, {"error": "Missing ID/version"}, {}

                parts_data = {}
                relations_data = {}

                try:
                    parts_data = client.get_topic_parts(topic_id, version_id)
                except Exception as e:
                    logger.error(f"Failed to get parts for {topic_id}: {e}")
                    parts_data = {"error": str(e)}

                try:
                    relations_data = client.get_topic_relations(topic_id)
                except Exception as e:
                    logger.debug(f"Failed to get relations for {topic_id}: {e}")
                    relations_data = {}

                return topic_id, topic, parts_data, relations_data

            # Use ThreadPoolExecutor for parallel downloads
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(fetch_topic_data, topic): topic for topic in all_topics}

                with create_progress_bar("Downloading", len(all_topics)) as pbar:
                    for future in as_completed(futures):
                        topic_id, topic, parts_data, relations_data = future.result()

                        if topic_id:
                            topic_entry = build_topic_entry(topic, parts_data, relations_data)
                            topics_dict[topic_id] = topic_entry
                        else:
                            logger.warning(f"Skipping topic without ID/version: {futures[future]}")

                        pbar.update(1)

            # Build parent relationships from children
            # (If topic A has child B, then B's parent is A)
            print("\nBuilding parent relationships...")
            for topic_id, topic_entry in topics_dict.items():
                for child_id in topic_entry["relations"]["children"]:
                    if child_id in topics_dict:
                        if topics_dict[child_id]["relations"]["parent"] is None:
                            topics_dict[child_id]["relations"]["parent"] = topic_id
        else:
            print("\nSkipping parts download (--no-parts mode)...")
            for topic in all_topics:
                topic_id = topic.get("topicId") or topic.get("topicGuid")
                if topic_id:
                    topic_entry = build_topic_entry(topic, parts_data=None, relations_data=None)
                    topics_dict[topic_id] = topic_entry

    # Step 4: Build final structure
    print("\nBuilding export structure...")

    export_data = {
        "_metadata": {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "tenant_id": client.tenant_id,
            "project_id": client.project_id,
            "acl_entry_id": client.acl_entry_id,
            "topic_count": len(topics_dict),
            "includes_parts": include_parts,
            "includes_relations": include_parts,  # Relations are fetched with parts
            "source": "askdelphi-content-download"
        },
        "content_design": {
            "topic_types": [
                {
                    "key": tt.get("key"),
                    "title": tt.get("title"),
                    "namespace": tt.get("namespace")
                }
                for tt in topic_types
            ],
            "relations": content_design.get("relations", []),
            "tag_hierarchies": content_design.get("tagHierarchies", content_design.get("tagGroups", []))
        },
        "topics": topics_dict
    }

    # Step 5: Write file
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"content_export_{timestamp}.json"

    output_path = Path(output_file)

    print(f"\nWriting to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    file_size = output_path.stat().st_size
    file_size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / 1024 / 1024:.1f} MB"

    print("\n" + "=" * 60)
    print("DOWNLOAD COMPLETE")
    print("=" * 60)
    print(f"  Output file: {output_path}")
    print(f"  File size: {file_size_str}")
    print(f"  Topics: {len(topics_dict)}")
    print(f"  Topic types: {len(topic_types)}")
    print("=" * 60 + "\n")

    return str(output_path)


def build_topic_entry(
    topic: Dict[str, Any],
    parts_data: Optional[Dict[str, Any]],
    relations_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Build a topic entry for the export JSON."""
    # API returns topicGuid or topicId depending on endpoint
    topic_id = topic.get("topicId") or topic.get("topicGuid")
    version_id = topic.get("topicVersionId") or topic.get("topicVersionKey")

    entry = {
        "id": topic_id,
        "version_id": version_id,
        "title": topic.get("title") or topic.get("topicTitle"),
        "topic_type_id": topic.get("topicTypeId") or topic.get("topicTypeKey"),
        "topic_type_title": topic.get("topicTypeTitle") or topic.get("topicTypeName") or topic.get("typeName"),
        "created_at": topic.get("createdAt") or topic.get("created"),
        "modified_at": topic.get("modifiedAt") or topic.get("modified") or topic.get("lastModificationDate"),
        "tags": topic.get("tags", []),
        "parts": {},
        "relations": {
            "related": [],
            "children": [],
            "parent": None  # Will be populated later by reverse lookup
        }
    }

    # Add parts if available
    if parts_data and not parts_data.get("error"):
        entry["parts"] = extract_parts(parts_data)

    # Extract relations (children) from relations data
    if relations_data:
        entry["relations"]["children"] = extract_child_relations(relations_data)

    # Calculate checksum (excluding the checksum field itself)
    entry["_checksum"] = calculate_checksum(entry)

    return entry


def extract_child_relations(relations_data: Dict[str, Any]) -> List[str]:
    """Extract child topic IDs from relations response."""
    children = []

    # Relations can be in different structures
    relations = relations_data.get("relations", [])

    for rel in relations:
        target_id = rel.get("targetTopicId")
        if target_id:
            children.append(target_id)

    return children


def extract_parts(parts_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract parts from the API response into a cleaner structure."""
    parts = {}

    # The parts data can have different structures depending on the API response
    # Try to handle common patterns

    if isinstance(parts_data, dict):
        # Check for groups structure
        groups = parts_data.get("groups", parts_data.get("partGroups", []))

        if groups:
            for group in groups:
                group_name = group.get("name", group.get("title", "default"))
                editors = group.get("editors", group.get("parts", []))

                for editor in editors:
                    part_id = editor.get("id") or editor.get("partId") or editor.get("name")
                    if part_id:
                        parts[part_id] = {
                            "id": part_id,
                            "name": editor.get("name") or editor.get("title"),
                            "type": editor.get("type") or editor.get("editorType"),
                            "group": group_name,
                            "content": editor.get("value") or editor.get("content") or editor.get("data")
                        }
        else:
            # Direct parts structure
            for key, value in parts_data.items():
                if key not in ["error", "success", "response"]:
                    if isinstance(value, dict):
                        parts[key] = {
                            "id": key,
                            "name": value.get("name", key),
                            "type": value.get("type"),
                            "content": value.get("value") or value.get("content")
                        }
                    else:
                        parts[key] = {
                            "id": key,
                            "name": key,
                            "type": "unknown",
                            "content": value
                        }

    return parts


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download all content from Ask Delphi to a JSON file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              Download all content
  %(prog)s -o backup.json               Save to specific file
  %(prog)s --no-parts                   Metadata only (faster)
  %(prog)s --topic-types "id1,id2"      Filter by topic types
        """
    )

    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Output JSON file path (default: content_export_TIMESTAMP.json)"
    )
    parser.add_argument(
        "--no-parts",
        action="store_true",
        help="Skip downloading topic parts (metadata only, much faster)"
    )
    parser.add_argument(
        "--topic-types",
        metavar="IDS",
        help="Comma-separated topic type IDs to filter"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=10,
        metavar="N",
        help="Number of parallel downloads (default: 10)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed progress information"
    )

    args = parser.parse_args()

    # Parse topic types filter
    topic_type_ids = None
    if args.topic_types:
        topic_type_ids = [t.strip() for t in args.topic_types.split(",")]

    # Run download
    try:
        output_path = download_all_content(
            output_file=args.output,
            include_parts=not args.no_parts,
            topic_type_ids=topic_type_ids,
            workers=args.workers,
            verbose=args.verbose
        )
        print(f"Success! Content exported to: {output_path}")
        return 0
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Download failed: {e}")
        print(f"\nError: {e}")
        print("Check askdelphi_debug.log for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
