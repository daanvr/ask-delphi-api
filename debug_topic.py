#!/usr/bin/env python3
"""Debug script to investigate topic version ID issue."""

import json
from askdelphi_client import AskDelphiClient

def main():
    client = AskDelphiClient()
    client.authenticate()

    topic_id = 'f922f105-013e-4486-929a-ec0a8d0692af'

    print("\n" + "="*60)
    print("DEBUGGING TOPIC VERSION ID")
    print("="*60)

    # 1. Check workflow state
    print("\n1. Workflow State:")
    state = client.get_topic_workflow_state(topic_id)
    print(json.dumps(state, indent=2))

    # 2. Search topic list for this specific topic
    print("\n2. Searching Topic List:")
    search_result = client.search_topics(query="Inning en betalingsverkeer", limit=10)
    topic_list = search_result.get("topicList", {})
    print(f"   Total available: {topic_list.get('totalAvailable', 'unknown')}")

    results = topic_list.get("result", [])
    print(f"   Results returned: {len(results)}")

    for topic in results:
        tid = topic.get("topicId")
        vid = topic.get("topicVersionId") or topic.get("topicVersionKey")
        title = topic.get("title") or topic.get("topicTitle")
        print(f"   - {title}")
        print(f"     topicId: {tid}")
        print(f"     versionId: {vid}")
        print(f"     Match: {tid == topic_id}")
        print(f"     All keys: {list(topic.keys())}")

    # 3. Check what's in original export file
    print("\n3. Version ID from export file:")
    try:
        with open('content_export_20260126_110428.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        topic_data = data.get('topics', {}).get(topic_id, {})
        print(f"   version_id: {topic_data.get('version_id')}")
        print(f"   title: {topic_data.get('title')}")
    except Exception as e:
        print(f"   Error: {e}")

    # 4. Try to get topic parts with the version from file
    print("\n4. Try get_topic_parts with version from file:")
    try:
        with open('content_export_20260126_110428.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        version_id = data.get('topics', {}).get(topic_id, {}).get('version_id')
        if version_id:
            parts = client.get_topic_parts(topic_id, version_id)
            print(f"   Success! Got parts response with keys: {list(parts.keys()) if isinstance(parts, dict) else type(parts)}")
        else:
            print("   No version_id in file")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    main()