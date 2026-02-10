def find_node_id(session: AskDelphiSession, hierarchy_title: str, node_path: str, verbose: bool = False) -> str:
    """Find hierarchy node ID by hierarchy title and path."""
   
    # Find hierarchy
    response = session.post(
        "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topiclist",
        json={"query": hierarchy_title, "pageSize": 1000}
    )
   
    topics = response.get("response", {}).get("topicList", {}).get("result", [])
    if not topics:
        raise ValueError(f"Hierarchy '{hierarchy_title}' not found")
   
    hierarchy = topics[0]
    hierarchy_id = hierarchy.get("topicGuid")
    hierarchy_version = hierarchy.get("topicVersionKey")
   
    # Get tree data
    response = session.get(
        f"v3/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{hierarchy_id}/topicVersion/{hierarchy_version}/part"
    )
   
    groups = response.get("topicEditorData", {}).get("groups", [])
    content_group = next((g for g in groups if g.get("partGroupId") == "content"), None)
    tree_part = next((p for p in content_group.get("parts", []) if p.get("partId") == "tree-editor"), None)
    tree_field = next((e for e in tree_part.get("editors", []) if e.get("editorFieldId") == "tree-editor"), None)
    tree_data = tree_field.get("value", {}).get("tree", [])
   
    # Search tree
    def find_in_tree(nodes, parts):
        if not parts or not nodes:
            return None
        current = parts[0]
        for node in nodes:
            if node.get("nodeTitle", "").lower() == current.lower():
                if len(parts) == 1:
                    return node.get("nodeId")
                return find_in_tree(node.get("children", []), parts[1:])
        return None
   
    node_id = find_in_tree(tree_data, node_path.split("/"))
    if not node_id:
        raise ValueError(f"Node '{node_path}' not found")
   
    return node_id


def build_tags(session: AskDelphiSession, tag_strings: list) -> list:
    """
    Build tags dict from hierarchy:path strings.
   
    Args:
        session: AskDelphiSession instance
        tag_strings: List of strings like ["Department:Engineering/Backend", "Priority:High"]
   
    Returns:
        List of dicts with HierarchyTopicId and HierarchyNodeId (PascalCase for API)
   
    Example:
        tags = build_tags(session, ["Department:Engineering/Backend", "Priority:High"])
        # Returns: [
        #     {"HierarchyTopicId": "uuid1", "HierarchyNodeId": "uuid2"},
        #     {"HierarchyTopicId": "uuid3", "HierarchyNodeId": "uuid4"}
        # ]
    """
    tags = []
   
    for tag_string in tag_strings:
        hierarchy_title, node_path = tag_string.split(":", 1)
       
        # Find hierarchy topic
        response = session.post(
            "v1/tenant/{tenantId}/project/{projectId}/acl/{aclEntryId}/topiclist",
            json={"query": hierarchy_title, "pageSize": 1000}
        )
       
        hierarchy_topic = response.get("response", {}).get("topicList", {}).get("result", [])[0]
        hierarchy_id = hierarchy_topic.get("topicGuid")
       
        # Find node ID
        node_id = find_node_id(session, hierarchy_title, node_path, verbose=False)
       
        # IMPORTANT: Use PascalCase field names for AskDelphi API compliance
        tags.append({
            "HierarchyTopicId": hierarchy_id,
            "HierarchyNodeId": node_id
        })
   
    return tags


def tag_and_metadata(
    session: AskDelphiSession,
    topic_id: str,
    topic_version_id: str,
    tags: list,
    metadata: dict = None
) -> bool:
    """
    Tag a topic and add metadata (minimal version).
   
    Args:
        session: AskDelphiSession instance
        topic_id: UUID of the topic
        topic_version_id: UUID of the topic version
        tags: List of dicts with HierarchyTopicId and HierarchyNodeId (from build_tags())
        metadata: Dict of key-value pairs to add as metadata
   
    Returns:
        True if successful
   
    Example:
        tags = build_tags(session, ["Department:Engineering/Backend"])
        metadata = {
            "External-Source-Id": "source-123",
            "External-Batch-Id": "batch-456"
        }
        tag_and_metadata(session, topic_id, topic_version_id, tags, metadata)
    """
   
    # Add tags (v2 API endpoint)
    if tags:
        response = session.post(
            f"v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{topic_version_id}/tag",
            json={"Tags": tags}  # PascalCase for API compliance
        )
        if not response.get("success"):
            raise Exception(f"Tag addition failed: {response.get('errorMessage')}")
   
    # Add metadata (v2 API endpoint - PUT request)
    if metadata:
        metadata_list = [{"Key": k, "Value": v} for k, v in metadata.items()]  # PascalCase
        response = session.put(
            f"v2/tenant/{{tenantId}}/project/{{projectId}}/acl/{{aclEntryId}}/topic/{topic_id}/topicVersion/{topic_version_id}/topicversionmetadata",
            json={"Data": metadata_list}  # Correct payload structure
        )
        if not response.get("success"):
            raise Exception(f"Metadata addition failed: {response.get('errorMessage')}")
   
    return True


# Usage
if __name__ == "__main__":
    session = AskDelphiSession(use_auth_cache=True)
    session.auth_manager.authenticate()
   
    # Build tags from hierarchy:path strings
    tags = build_tags(session, [
        "Department:Engineering/Backend",
        "Priority:High"
    ])
   
    metadata = {
        "External-Source-Id": "source-123",
        "External-Batch-Id": "batch-456"
    }
   
    tag_and_metadata(session, "topic-uuid", "version-uuid", tags, metadata)
    print("✓ Tagged and metadata added")