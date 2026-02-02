#!/usr/bin/env python3
"""
Ask Delphi Topic Hierarchy Visualizer

Generates an interactive HTML tree visualization of topic hierarchy.

Usage:
    python visualize_hierarchy.py content.json           # Generate HTML from export
    python visualize_hierarchy.py content.json -o tree.html
    python visualize_hierarchy.py --download             # Download fresh + visualize
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict


# Color palette for topic types
TOPIC_TYPE_COLORS = {
    "Procedure": "#3b82f6",      # Blue
    "Concept": "#22c55e",        # Green
    "Container": "#6b7280",      # Gray
    "Reference": "#8b5cf6",      # Purple
    "Task": "#f59e0b",           # Amber
    "Troubleshooting": "#ef4444", # Red
    "Glossary": "#06b6d4",       # Cyan
    "Overview": "#ec4899",       # Pink
}

DEFAULT_COLOR = "#64748b"  # Slate


def load_export_file(file_path: str) -> Dict[str, Any]:
    """Load and parse the exported JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_tree(topics: Dict[str, Dict]) -> Dict[str, List[str]]:
    """
    Build a tree structure from parent-child relations.

    Returns a dict mapping topic_id -> list of child topic_ids
    """
    children_map = defaultdict(list)

    for topic_id, topic in topics.items():
        parent_id = topic.get("relations", {}).get("parent")
        if parent_id:
            children_map[parent_id].append(topic_id)
        # Also use the explicit children list
        for child_id in topic.get("relations", {}).get("children", []):
            if child_id not in children_map[topic_id]:
                children_map[topic_id].append(child_id)

    return dict(children_map)


def find_root_topics(topics: Dict[str, Dict], children_map: Dict[str, List[str]]) -> List[str]:
    """Find topics that have no parent (root nodes)."""
    roots = []
    for topic_id, topic in topics.items():
        parent_id = topic.get("relations", {}).get("parent")
        if not parent_id:
            roots.append(topic_id)

    # Sort roots by title
    roots.sort(key=lambda tid: topics.get(tid, {}).get("title", "").lower())
    return roots


def get_topic_type_color(topic_type: Optional[str]) -> str:
    """Get color for a topic type."""
    if not topic_type:
        return DEFAULT_COLOR

    # Try exact match first
    if topic_type in TOPIC_TYPE_COLORS:
        return TOPIC_TYPE_COLORS[topic_type]

    # Try partial match
    for key, color in TOPIC_TYPE_COLORS.items():
        if key.lower() in topic_type.lower():
            return color

    return DEFAULT_COLOR


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
    )


def escape_js_string(text: str) -> str:
    """Escape string for JavaScript."""
    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
    )


def generate_tree_html(
    topics: Dict[str, Dict],
    children_map: Dict[str, List[str]],
    root_ids: List[str]
) -> str:
    """Generate HTML for the tree structure."""

    def render_node(topic_id: str, depth: int = 0) -> str:
        topic = topics.get(topic_id, {})
        title = topic.get("title", "Untitled")
        topic_type = topic.get("topic_type_title", "")
        tags = topic.get("tags", [])
        children = children_map.get(topic_id, [])

        # Sort children by title
        children.sort(key=lambda tid: topics.get(tid, {}).get("title", "").lower())

        color = get_topic_type_color(topic_type)
        has_children = len(children) > 0

        # Build tag badges
        tag_html = ""
        if tags:
            tag_names = []
            for tag in tags[:3]:  # Show max 3 tags
                if isinstance(tag, dict):
                    tag_names.append(tag.get("name", tag.get("title", "")))
                else:
                    tag_names.append(str(tag))
            if tag_names:
                tag_html = f'<span class="tags">{", ".join(escape_html(t) for t in tag_names if t)}</span>'
            if len(tags) > 3:
                tag_html += f'<span class="tag-more">+{len(tags) - 3}</span>'

        # Build the node HTML
        node_class = "tree-node" + (" has-children" if has_children else "")
        icon = "▶" if has_children else "•"
        icon_class = "toggle" if has_children else "leaf"

        html = f'''
        <div class="{node_class}" data-id="{escape_html(topic_id)}" data-title="{escape_html(title.lower())}" data-type="{escape_html(topic_type.lower() if topic_type else '')}">
            <div class="node-content">
                <span class="{icon_class}">{icon}</span>
                <span class="title">{escape_html(title)}</span>
                <span class="type-badge" style="background-color: {color}">{escape_html(topic_type) if topic_type else 'Unknown'}</span>
                {tag_html}
                {f'<span class="child-count">{len(children)}</span>' if has_children else ''}
            </div>
        '''

        if has_children:
            html += '<div class="children" style="display: none;">'
            for child_id in children:
                if child_id in topics:  # Only render if topic exists
                    html += render_node(child_id, depth + 1)
            html += '</div>'

        html += '</div>'
        return html

    # Render all root nodes
    tree_html = ""
    for root_id in root_ids:
        tree_html += render_node(root_id)

    return tree_html


def generate_html_page(
    topics: Dict[str, Dict],
    metadata: Dict[str, Any],
    content_design: Dict[str, Any]
) -> str:
    """Generate the full HTML page."""

    # Build tree structure
    children_map = build_tree(topics)
    root_ids = find_root_topics(topics, children_map)

    # Get topic type colors for legend
    topic_types = content_design.get("topic_types", [])
    type_legend = ""
    for tt in topic_types:
        title = tt.get("title", "")
        if title:
            color = get_topic_type_color(title)
            type_legend += f'<span class="legend-item"><span class="legend-color" style="background-color: {color}"></span>{escape_html(title)}</span>'

    # Generate tree HTML
    tree_html = generate_tree_html(topics, children_map, root_ids)

    # Stats
    total_topics = len(topics)
    root_count = len(root_ids)
    orphan_count = sum(1 for t in topics.values() if not t.get("relations", {}).get("parent") and not children_map.get(t.get("id")))

    html = f'''<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Topic Hierarchy - Ask Delphi</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #f8fafc;
            color: #1e293b;
            line-height: 1.5;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            background: white;
            border-bottom: 1px solid #e2e8f0;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        h1 {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 10px;
        }}

        .stats {{
            display: flex;
            gap: 20px;
            font-size: 0.875rem;
            color: #64748b;
            margin-bottom: 15px;
        }}

        .stats span {{
            background: #f1f5f9;
            padding: 4px 12px;
            border-radius: 4px;
        }}

        .controls {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }}

        .search-box {{
            flex: 1;
            min-width: 200px;
            max-width: 400px;
            padding: 8px 12px;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 0.875rem;
        }}

        .search-box:focus {{
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }}

        .btn {{
            padding: 8px 16px;
            border: 1px solid #e2e8f0;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
            transition: all 0.15s;
        }}

        .btn:hover {{
            background: #f1f5f9;
            border-color: #cbd5e1;
        }}

        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e2e8f0;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 0.75rem;
            color: #64748b;
        }}

        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 3px;
        }}

        .tree-container {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            padding: 20px;
            min-height: 400px;
        }}

        .tree-node {{
            margin-left: 20px;
        }}

        .tree-node:first-child {{
            margin-left: 0;
        }}

        .node-content {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 8px;
            border-radius: 4px;
            cursor: default;
            transition: background 0.15s;
        }}

        .node-content:hover {{
            background: #f8fafc;
        }}

        .has-children > .node-content {{
            cursor: pointer;
        }}

        .toggle, .leaf {{
            width: 16px;
            font-size: 0.75rem;
            color: #94a3b8;
            flex-shrink: 0;
        }}

        .toggle {{
            cursor: pointer;
            transition: transform 0.15s;
        }}

        .expanded > .node-content > .toggle {{
            transform: rotate(90deg);
        }}

        .title {{
            font-weight: 500;
            flex-shrink: 1;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .type-badge {{
            font-size: 0.625rem;
            padding: 2px 6px;
            border-radius: 3px;
            color: white;
            flex-shrink: 0;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.025em;
        }}

        .tags {{
            font-size: 0.75rem;
            color: #64748b;
            flex-shrink: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .tag-more {{
            font-size: 0.625rem;
            color: #94a3b8;
            margin-left: 4px;
        }}

        .child-count {{
            font-size: 0.625rem;
            background: #e2e8f0;
            color: #64748b;
            padding: 1px 6px;
            border-radius: 10px;
            flex-shrink: 0;
        }}

        .children {{
            border-left: 1px solid #e2e8f0;
            margin-left: 7px;
            padding-left: 12px;
        }}

        .hidden {{
            display: none !important;
        }}

        .highlight .title {{
            background: #fef08a;
            padding: 0 4px;
            border-radius: 2px;
        }}

        .no-results {{
            text-align: center;
            padding: 40px;
            color: #64748b;
        }}

        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}

            .stats {{
                flex-wrap: wrap;
            }}

            .controls {{
                flex-direction: column;
                align-items: stretch;
            }}

            .search-box {{
                max-width: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Topic Hierarchy</h1>
            <div class="stats">
                <span>{total_topics} topics</span>
                <span>{root_count} root nodes</span>
                <span>Exported: {metadata.get('exported_at', 'Unknown')[:10]}</span>
            </div>
            <div class="controls">
                <input type="text" class="search-box" placeholder="Search topics..." id="searchInput">
                <button class="btn" onclick="expandAll()">Expand All</button>
                <button class="btn" onclick="collapseAll()">Collapse All</button>
                <button class="btn" onclick="expandLevel(1)">Level 1</button>
                <button class="btn" onclick="expandLevel(2)">Level 2</button>
            </div>
            <div class="legend">
                {type_legend}
            </div>
        </header>

        <div class="tree-container" id="treeContainer">
            {tree_html}
        </div>
    </div>

    <script>
        // Toggle node expansion
        document.querySelectorAll('.has-children > .node-content').forEach(content => {{
            content.addEventListener('click', (e) => {{
                const node = content.parentElement;
                const children = node.querySelector('.children');
                if (children) {{
                    const isExpanded = node.classList.contains('expanded');
                    if (isExpanded) {{
                        children.style.display = 'none';
                        node.classList.remove('expanded');
                    }} else {{
                        children.style.display = 'block';
                        node.classList.add('expanded');
                    }}
                }}
            }});
        }});

        // Expand all nodes
        function expandAll() {{
            document.querySelectorAll('.has-children').forEach(node => {{
                node.classList.add('expanded');
                const children = node.querySelector('.children');
                if (children) children.style.display = 'block';
            }});
        }}

        // Collapse all nodes
        function collapseAll() {{
            document.querySelectorAll('.has-children').forEach(node => {{
                node.classList.remove('expanded');
                const children = node.querySelector('.children');
                if (children) children.style.display = 'none';
            }});
        }}

        // Expand to specific level
        function expandLevel(level) {{
            collapseAll();
            expandToLevel(document.getElementById('treeContainer'), 0, level);
        }}

        function expandToLevel(container, currentLevel, targetLevel) {{
            if (currentLevel >= targetLevel) return;

            container.querySelectorAll(':scope > .tree-node.has-children').forEach(node => {{
                node.classList.add('expanded');
                const children = node.querySelector('.children');
                if (children) {{
                    children.style.display = 'block';
                    expandToLevel(children, currentLevel + 1, targetLevel);
                }}
            }});
        }}

        // Search functionality
        const searchInput = document.getElementById('searchInput');
        let searchTimeout;

        searchInput.addEventListener('input', (e) => {{
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {{
                filterTree(e.target.value.toLowerCase());
            }}, 200);
        }});

        function filterTree(query) {{
            const allNodes = document.querySelectorAll('.tree-node');

            if (!query) {{
                // Show all nodes, collapse all
                allNodes.forEach(node => {{
                    node.classList.remove('hidden', 'highlight');
                }});
                collapseAll();
                return;
            }}

            // First, hide all nodes
            allNodes.forEach(node => {{
                node.classList.add('hidden');
                node.classList.remove('highlight');
            }});

            // Find matching nodes and show them with their ancestors
            allNodes.forEach(node => {{
                const title = node.dataset.title || '';
                const type = node.dataset.type || '';

                if (title.includes(query) || type.includes(query)) {{
                    // Show this node
                    node.classList.remove('hidden');
                    node.classList.add('highlight');

                    // Show and expand all ancestors
                    let parent = node.parentElement;
                    while (parent) {{
                        if (parent.classList.contains('children')) {{
                            parent.style.display = 'block';
                            const parentNode = parent.parentElement;
                            if (parentNode && parentNode.classList.contains('tree-node')) {{
                                parentNode.classList.remove('hidden');
                                parentNode.classList.add('expanded');
                            }}
                        }}
                        parent = parent.parentElement;
                    }}

                    // Also show direct children (collapsed)
                    const children = node.querySelector('.children');
                    if (children) {{
                        children.querySelectorAll(':scope > .tree-node').forEach(child => {{
                            child.classList.remove('hidden');
                        }});
                    }}
                }}
            }});
        }}

        // Expand first level by default
        expandLevel(1);
    </script>
</body>
</html>
'''
    return html


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate an interactive HTML visualization of topic hierarchy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s content_export.json              Generate hierarchy.html
  %(prog)s content.json -o tree.html        Save to specific file
  %(prog)s --download                       Download fresh data and visualize
        """
    )

    parser.add_argument(
        "input_file",
        nargs="?",
        help="Input JSON file from download_content.py"
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        default="hierarchy.html",
        help="Output HTML file (default: hierarchy.html)"
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download fresh content before visualizing"
    )

    args = parser.parse_args()

    # Handle --download option
    if args.download:
        print("Downloading fresh content...")
        from download_content import download_all_content
        input_file = download_all_content()
    elif args.input_file:
        input_file = args.input_file
    else:
        parser.error("Please provide an input file or use --download")

    try:
        # Load data
        print(f"Loading {input_file}...")
        data = load_export_file(input_file)

        topics = data.get("topics", {})
        metadata = data.get("_metadata", {})
        content_design = data.get("content_design", {})

        if not topics:
            print("No topics found in the export file.")
            return 1

        print(f"Found {len(topics)} topics")

        # Generate HTML
        print("Generating HTML visualization...")
        html = generate_html_page(topics, metadata, content_design)

        # Write output
        output_path = Path(args.output)
        output_path.write_text(html, encoding='utf-8')

        print(f"\nVisualization saved to: {output_path}")
        print(f"Open in browser: file://{output_path.absolute()}")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON file - {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
