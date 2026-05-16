#!/usr/bin/env python3
"""Build static HTML mirror site from GitHub metadata backup.

Replaces the Hugo-based build pipeline. Reads backup JSON files,
builds a lightweight in-memory index, then renders HTML pages one
at a time using zero external dependencies.

Usage:
    python build.py \\
        --input ./github-metadata-backup-bitcoin-core-secp256k1 \\
        --output ./public \\
        --title "secp256k1 GitHub Mirror" \\
        --owner bitcoin-core \\
        --repository secp256k1 \\
        [--footer "<b>Hosted by 0xB10C</b>"] \\
        [--base-url "/"] \\
        [--subset]
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from mirror.config import Config
from mirror.index import build_index
from mirror.markdown import MarkdownRenderer
from mirror.html.renderer import SiteRenderer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build static HTML mirror from GitHub metadata backup.",
    )
    parser.add_argument(
        "--input", required=True, type=Path,
        help="Path to the github-metadata-backup directory.",
    )
    parser.add_argument(
        "--output", required=True, type=Path,
        help="Output directory for the generated HTML site.",
    )
    parser.add_argument(
        "--title", required=True,
        help="Site title (shown in nav bar).",
    )
    parser.add_argument(
        "--owner", required=True,
        help="GitHub repository owner.",
    )
    parser.add_argument(
        "--repository", required=True,
        help="GitHub repository name.",
    )
    parser.add_argument(
        "--footer", default="",
        help="Footer HTML (shown on every page).",
    )
    parser.add_argument(
        "--base-url", default="/",
        help="Base URL path (e.g. '/' or '/mirror/'). Default: /",
    )
    parser.add_argument(
        "-s", "--subset", action="store_true",
        help="Only process a small subset (for testing).",
    )
    parser.add_argument(
        "--markdown", action="store_true",
        help="Also emit a plain-markdown index.md alongside each issue/PR index.html.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = Config(
        title=args.title,
        owner=args.owner,
        repository=args.repository,
        footer=args.footer,
        base_url=args.base_url,
        input_dir=args.input,
        output_dir=args.output,
        subset=args.subset,
        markdown=args.markdown,
    )

    # Ensure output directory exists
    config.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Input:  {config.input_dir}")
    print(f"Output: {config.output_dir}")
    print(f"Repo:   {config.owner}/{config.repository}")
    print()

    # Pass 1: Build index
    t0 = time.monotonic()
    print("=== Pass 1: Building index ===")
    index = build_index(config)
    t1 = time.monotonic()
    print(f"Index built: {len(index.entries)} entries, "
          f"{len(index.by_contributor)} contributors, "
          f"{len(index.by_label)} labels, "
          f"{len(index.graph.nodes)} graph nodes, "
          f"{len(index.graph.links)} graph links")
    print(f"Pass 1 took {t1 - t0:.1f}s")
    print()

    # Pass 2: Render HTML
    print("=== Pass 2: Rendering HTML ===")
    md = MarkdownRenderer()
    renderer = SiteRenderer(config, index, md)
    renderer.render_all()
    t2 = time.monotonic()
    print(f"Pass 2 took {t2 - t1:.1f}s")
    print()

    print(f"Done! Total: {t2 - t0:.1f}s")
    print(f"Site generated at: {config.output_dir}")


if __name__ == "__main__":
    main()
