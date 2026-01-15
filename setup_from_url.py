#!/usr/bin/env python3
"""
Setup Ask Delphi credentials from a CMS URL.

Extracts tenant_id, project_id, and acl_entry_id from a CMS URL and
creates/updates the .env file.

Usage:
    python setup_from_url.py "https://xxx.askdelphi.com/cms/tenant/.../project/.../acl/.../"

Or run without arguments and paste the URL when prompted.
"""

import re
import sys
from pathlib import Path


def parse_cms_url(url: str) -> dict:
    """
    Parse an Ask Delphi CMS URL and extract the IDs.

    URL format:
    https://xxx.askdelphi.com/cms/tenant/{TENANT_ID}/project/{PROJECT_ID}/acl/{ACL_ENTRY_ID}/...

    Returns:
        dict with tenant_id, project_id, acl_entry_id
    """
    # Pattern to match the URL structure
    pattern = r'/tenant/([a-f0-9-]+)/project/([a-f0-9-]+)/acl/([a-f0-9-]+)'

    match = re.search(pattern, url, re.IGNORECASE)

    if not match:
        raise ValueError(
            "Could not parse URL. Expected format:\n"
            "https://xxx.askdelphi.com/cms/tenant/{TENANT_ID}/project/{PROJECT_ID}/acl/{ACL_ENTRY_ID}/..."
        )

    return {
        "tenant_id": match.group(1),
        "project_id": match.group(2),
        "acl_entry_id": match.group(3)
    }


def update_env_file(ids: dict, portal_code: str = None):
    """Create or update .env file with the extracted IDs."""
    env_path = Path(".env")

    # Read existing .env if it exists
    existing_lines = []
    existing_keys = {}

    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                existing_lines.append(line)
                if '=' in line and not line.strip().startswith('#'):
                    key = line.split('=')[0].strip()
                    existing_keys[key] = len(existing_lines) - 1

    # Update or add values
    updates = {
        "ASKDELPHI_TENANT_ID": ids["tenant_id"],
        "ASKDELPHI_PROJECT_ID": ids["project_id"],
        "ASKDELPHI_ACL_ENTRY_ID": ids["acl_entry_id"],
    }

    if portal_code:
        updates["ASKDELPHI_PORTAL_CODE"] = portal_code

    for key, value in updates.items():
        if key in existing_keys:
            # Update existing line
            idx = existing_keys[key]
            existing_lines[idx] = f"{key}={value}\n"
        else:
            # Add new line
            existing_lines.append(f"{key}={value}\n")

    # Write back
    with open(env_path, 'w') as f:
        f.writelines(existing_lines)

    print(f"Updated {env_path}")


def main():
    print("\n" + "=" * 50)
    print("ASK DELPHI - SETUP FROM URL")
    print("=" * 50 + "\n")

    # Get URL from argument or prompt
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        print("Paste your CMS URL (from browser address bar):")
        print("Example: https://xxx.askdelphi.com/cms/tenant/.../project/.../acl/...\n")
        url = input("URL: ").strip()

    if not url:
        print("Error: No URL provided")
        return 1

    # Parse URL
    try:
        ids = parse_cms_url(url)
    except ValueError as e:
        print(f"\nError: {e}")
        return 1

    # Show extracted IDs
    print("\nExtracted IDs:")
    print(f"  Tenant ID:    {ids['tenant_id']}")
    print(f"  Project ID:   {ids['project_id']}")
    print(f"  ACL Entry ID: {ids['acl_entry_id']}")

    # Ask for portal code (optional)
    print("\nPortal code (from Mobile tab in publication):")
    print("Press Enter to skip if you already have one in .env")
    portal_code = input("Portal code: ").strip() or None

    # Update .env
    update_env_file(ids, portal_code)

    print("\n" + "=" * 50)
    print("SETUP COMPLETE")
    print("=" * 50)
    print("\nYou can now run:")
    print("  python test_api.py")
    print("  python download_content.py")
    print("=" * 50 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
