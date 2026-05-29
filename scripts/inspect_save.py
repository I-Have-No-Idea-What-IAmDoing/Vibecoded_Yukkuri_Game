"""CLI tool for inspecting Vibecoded Yukkuri Game save files.

Dumps sqlite chunks and msgpack contents in a human-readable format.
"""

import argparse
import collections
import json
import os
import sqlite3
import sys
from typing import Any

import msgspec


def main() -> None:
    """Main CLI entry point for inspecting save files."""
    parser = argparse.ArgumentParser(
        description="Inspect and dump Vibecoded Yukkuri Game save files."
    )
    parser.add_argument("save_file", help="Path to the .sqlite save file")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a brief summary instead of full JSON",
    )
    parser.add_argument(
        "--entity",
        type=int,
        help="Filter and dump only components for this entity ID",
    )
    parser.add_argument(
        "--component",
        help="Filter and dump all instances of this component type",
    )
    args = parser.parse_args()

    sqlite_path = args.save_file
    if not os.path.exists(sqlite_path):
        print(
            f"Error: Save file '{sqlite_path}' not found.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
    except Exception as e:
        print(f"Error opening SQLite database: {e}", file=sys.stderr)
        sys.exit(1)

    # 1. Load Global State if exists
    global_data: dict[str, Any] = {}
    try:
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='global_state'"
        )
        if cursor.fetchone():
            cursor.execute(
                "SELECT value FROM global_state WHERE key='global_data'"
            )
            row = cursor.fetchone()
            if row:
                global_data = json.loads(row[0])
    except Exception as e:
        print(f"Warning: Failed to load global_state: {e}", file=sys.stderr)

    # 2. Load Spatial Chunks
    chunks_data: dict[str, list[dict[str, Any]]] = {}
    try:
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='chunks'"
        )
        if not cursor.fetchone():
            print(
                f"Error: '{sqlite_path}' is not a valid save file "
                f"(missing 'chunks' table).",
                file=sys.stderr,
            )
            conn.close()
            sys.exit(1)

        cursor.execute("SELECT chunk_id, data FROM chunks")
        rows = cursor.fetchall()
        for chunk_id, blob in rows:
            chunks_data[chunk_id] = msgspec.msgpack.decode(blob)
    except Exception as e:
        print(f"Error reading chunks table: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    conn.close()

    # Apply filters
    filtered_chunks: dict[str, list[dict[str, Any]]] = {}
    total_entities = 0
    components_count: dict[str, int] = collections.defaultdict(int)

    for chunk_id, entities in chunks_data.items():
        matched_entities = []
        for ent in entities:
            ent_id = ent.get("entity_id")
            comps = ent.get("components", {})

            # Filter by entity ID
            if args.entity is not None and ent_id != args.entity:
                continue

            # Filter by component name
            if args.component is not None:
                if args.component not in comps:
                    continue
                # Keep only matched component
                comps = {args.component: comps[args.component]}

            # Collect stats
            for cname in comps:
                components_count[cname] += 1

            matched_entities.append(
                {
                    "entity_id": ent_id,
                    "stable_id": ent.get("stable_id"),
                    "components": comps,
                }
            )

        if matched_entities:
            filtered_chunks[chunk_id] = matched_entities
            total_entities += len(matched_entities)

    if args.summary:
        print(f"=== Save File Summary: {sqlite_path} ===")
        print("Global Data:")
        for k, v in sorted(global_data.items()):
            print(f"  {k}: {v}")
        print(f"Total Chunks: {len(chunks_data)}")
        print(f"Total Matched Entities: {total_entities}")
        print("\nMatched Components:")
        for cname, count in sorted(
            components_count.items(), key=lambda x: -x[1]
        ):
            print(f"  {cname}: {count}")
    else:
        # Full dump as JSON
        output = {
            "global_data": global_data,
            "chunks": filtered_chunks,
        }
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
