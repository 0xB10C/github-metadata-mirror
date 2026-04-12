"""HTML page skeleton: base layout, head, nav, footer, style, search JS, graph JS."""

from __future__ import annotations

from mirror.config import Config
from mirror.util import format_datetime_utc


def style_css() -> str:
    """Return the inline <style> block (port of partials/style.html)."""
    return """\
<style>
:root {
  --bs-body-bg: #0d1117;
  --bs-body-color: var(--bs-gray-300);
}

body {
  min-width: 300px;
}

blockquote > p {
  margin: 0.3em 0em;
}

blockquote:not([class]) {
  margin: 1em 1em;
  border-left: 4px solid #eaecf0;
  padding: 2px 10px;
}

p {
  margin-top: 0.5em;
  margin-bottom: 0.5em;
}

p:empty {
  margin-top: 0px;
  margin-bottom: 0px;
}

p > code {
  color: var(--bs-light);
  background-color: var(--bs-gray-700);
  border-radius: 5px;
  padding: 0.15em;
}

pre {
  padding: 1em;
  margin-top: 0.5em;
  margin-bottom: 0.5em;
}

table, td, th {
  border: 1px solid var(--bs-gray-700);
  padding: 0.4em;
}

.state-dot {
  width: 6px;
  height: 6px;
  padding: 0;
  border-radius: 50%;
}

.state-complete {
  background-color: var(--bs-indigo) !important;
  color: var(--bs-light);
}

.state-merged {
  background-color: var(--bs-indigo) !important;
  color: var(--bs-light);
}

.state-draft {
  background-color: var(--bs-gray);
  color: var(--bs-light);
}

.state-closed {
  background-color: var(--bs-red) !important;
  color: var(--bs-light);
}

.state-open {
  background-color: var(--bs-green) !important;
  color: var(--bs-light);
}

.timeline {
  margin-left: auto;
  margin-right: auto;
  display: flex;
  flex-direction: column;
  border-left: 1px solid var(--bs-gray);
  font-size: 1.125rem;
}

.timeline-item:first-child {
  margin-top: 0 !important;
}

.timeline-item {
  display: flex;
  gap: 24px;
}

.timeline-item-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  margin-left: -52px;
  flex-shrink: 0;
  overflow: hidden;
}

.timeline-item-description {
  display: block;
  padding-top: 6px;
  gap: 8px;
}

.timeline-item-icon-circle {
  height: 32px;
  width: 32px;
  background-color: #444;
  border-radius: 50%;
  display: inline;
  text-align: center;
}

.body-text img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.body-text a {
  text-decoration: none;
}
</style>
"""


def head_html(title: str, config: Config) -> str:
    """Return the <head> content (port of partials/head.html)."""
    b = config.base_url
    return f"""\
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

  <meta name="generator" content="github-metadata-mirror (Python)">

  <link rel="apple-touch-icon" sizes="180x180" href="{b}img/apple-touch-icon.png">
  <link rel="icon" type="image/png" sizes="32x32" href="{b}img/favicon-32x32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="{b}img/favicon-16x16.png">
  <link rel="manifest" href="{b}site.webmanifest">
  <link rel="mask-icon" href="{b}img/safari-pinned-tab.svg" color="#5bbad5">
  <link rel="shortcut icon" href="{b}img/favicon.ico">
  <meta name="apple-mobile-web-app-title" content="{title}">
  <meta name="application-name" content="{title}">
  <meta name="msapplication-TileColor" content="#00aba9">
  <meta name="msapplication-config" content="{b}browserconfig.xml">
  <meta name="theme-color" content="#ffffff">

  <link rel="stylesheet" href="{b}css/bootstrap.min.css">
  <script src="{b}js/bootstrap.min.js"></script>
  <script src="{b}js/minisearch.js"></script>

  <title>{title}</title>

  {style_css()}
</head>
"""


def nav_html(config: Config) -> str:
    """Return the navigation bar (port of partials/nav.html)."""
    b = config.base_url
    return f"""\
<nav class="navbar navbar-expand-lg bg-body-tertiary mb-3">
  <div class="container">
    <a class="navbar-brand" href="{b}">
      <img src="{b}img/favicon.svg" alt="Logo" style="filter: invert(1);" width="48" height="48">
      {config.title}
    </a>
    <div class="collapse navbar-collapse d-flex justify-content-between">
      <div class="navbar-nav">
        <a class="nav-link" href="{b}labels/">Labels</a>
        <a class="nav-link" href="{b}contributors/">Contributors</a>
      </div>
    </div>
  </div>
</nav>
"""


def footer_html(config: Config) -> str:
    """Return the footer (port of partials/footer.html)."""
    b = config.base_url
    generated = format_datetime_utc()
    return f"""\
<hr>
<div class="row text-center my-3">
    <div class="col-lg-6">
        <span class="my-auto">
            <a target="_blank" rel="noopener" href="https://github.com/0xb10c/github-metadata-mirror" class="text-reset text-decoration-none">
                <svg width=32 height=32 fill="currentColor" alt="GitHub logo">
                    <use xlink:href="{b}img/bootstrap-icons.svg#git"/>
                </svg>
                <span class="text-decoration-underline">github-metadata-mirror</span>
            </a>
            <br>
            <br>
            <span class="text-muted">
                This is a metadata mirror of the GitHub repository
                <a class="text-reset" target="_blank" rel="noopener" href="https://github.com/{config.owner}/{config.repository}">{config.owner}/{config.repository}</a>.
                This site is not affiliated with GitHub.
                Content is generated from a <a target="_blank" rel="noopener" href="https://github.com/0xb10c/github-metadata-backup" class="text-reset text-decoration-none"><span class="text-decoration-underline">GitHub metadata backup</span></a>.
                <br>
                <small>
                    generated: {generated}
                </small>
            </span>
            <br>
        </span>
    </div>
    <div class="col-lg-6">
        <span class="my-auto">
            {config.footer}
        </span>
    </div>
</div>
"""


def search_script(config: Config) -> str:
    """Return the MiniSearch search JS (port of partials/search.html)."""
    b = config.base_url
    return f"""\
<template id="search-result">
    <a href="#" id="link" class="list-group-item">
        <span id="badge" class="badge">badge</span>
        <span id="title" class="fw-bold">title</span>
        <span id="number" class="text-mute"></span>
        <br>
        <b id="contributor"></b>
        on
        <span id="date"></span>
        <small id="score" class="small text-mute"></small>
    </a>
</template>

<script>
    window.onload = function () {{

        const searchBar = document.querySelector("#search-bar");
        const staticRecent = document.querySelector("#static-recent");
        const searchResultTemplate = document.querySelector('#search-result');
        const searchResults = document.querySelector('#search-results');

        fetch('{b}index.json')
            .then((response) => response.json())
            .then((index) => {{

                let miniSearch = new MiniSearch({{
                    idField: "number",
                    fields: ["title", "contributor", "number", "state", "type"],
                    storeFields: ["title", "contributor", "number", "date", "state", "permalink", "type"],
                    searchOptions: {{
                        prefix: true,
                        boost: {{ title: 2 }},
                        fuzzy: 0.2
                    }}
                }})

                miniSearch.addAll(index)

                async function showResults(results) {{
                    while (searchResults.firstChild) {{ searchResults.removeChild(searchResults.firstChild); }}
                    let resultsToDisplay = Math.min(100, results.length);
                    for (let i = 0; i < resultsToDisplay; i++) {{
                        const clone = searchResultTemplate.content.cloneNode(true);
                        const result = results[i];

                        clone.querySelector("#title").innerHTML = result.title;
                        clone.querySelector("#contributor").textContent = result.contributor;
                        clone.querySelector("#date").textContent = result.date;
                        clone.querySelector("#number").textContent = result.number;
                        clone.querySelector("#link").href = result.permalink;
                        clone.querySelector("#badge").textContent = result.type;
                        clone.querySelector("#badge").classList.add("state-" + result.state);

                        searchResults.appendChild(clone);
                    }}
                }}

                async function handleEvent(event) {{
                    let term = event.target.value;
                    if (term) {{
                        const results = miniSearch.search(term)
                        staticRecent.classList.add("d-none");
                        showResults(results)
                    }} else {{
                        while (searchResults.firstChild) {{ searchResults.removeChild(searchResults.firstChild); }}
                        staticRecent.classList.remove("d-none");
                    }}
                }}

                searchBar.addEventListener("input", async (event) => {{ handleEvent(event) }});
            }});
    }};
</script>
"""


def graph_script(config: Config) -> str:
    """Return the force-graph JS.

    Reads ?start=N from the URL. The graph starts with that node and its
    immediate neighbours rendered as cards. Clicking a card expands its hidden
    neighbours; ctrl/cmd-clicking opens the issue/PR page.
    """
    b = config.base_url
    return f"""\
<style>
/* Break out of Bootstrap container so the graph uses the full viewport width. */
#graph-wrapper {{
    width: 100vw;
    position: relative;
    left: 50%;
    margin-left: -50vw;
    height: calc(100vh - 120px);
    min-height: 400px;
    background: #0d1117;
}}
#graph-controls {{
    position: absolute;
    top: 8px;
    left: 8px;
    z-index: 10;
}}
#graph-hint {{
    position: absolute;
    bottom: 12px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 10;
    font-size: 0.78em;
    color: #555;
    pointer-events: none;
}}
</style>

<div id="graph-wrapper">
    <div id="graph-controls">
        <button id="btn-reset" class="btn btn-sm btn-outline-secondary">Reset</button>
    </div>
    <span id="graph-hint">click card to open &middot; click &ldquo;Load +N connected&rdquo; to expand</span>
    <div id="graph"></div>
</div>

<script src="//unpkg.com/force-graph"></script>
<script src="//unpkg.com/d3-force"></script>
<script src="//unpkg.com/d3-quadtree"></script>

<script>
window.onload = function () {{
    const params = new URLSearchParams(window.location.search);
    const startNum = params.has('start') ? parseInt(params.get('start')) : null;

    if (startNum === null) {{
        document.getElementById('graph').innerHTML =
            '<p style="color:#888;padding:2em;">Open this graph from an issue or PR page.</p>';
        document.getElementById('btn-reset').style.display = 'none';
        return;
    }}

    // Card dimensions in graph-space pixels.
    const CW = 240, CH = 78, CR = 4;

    function stateColor(n) {{
        if (n.state === "merged" || n.state === "complete") return "#6610f2";
        if (n.state === "draft") return "#6c757d";
        if (n.state === "closed") return "#dc3545";
        if (n.state === "open") return "#188754";
        return "#444";
    }}

    // Draw a rounded rectangle path (no fill/stroke — caller decides).
    function roundRect(ctx, x, y, w, h, r) {{
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.arcTo(x + w, y,     x + w, y + r,     r);
        ctx.lineTo(x + w, y + h - r);
        ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
        ctx.lineTo(x + r, y + h);
        ctx.arcTo(x,     y + h, x,     y + h - r, r);
        ctx.lineTo(x,     y + r);
        ctx.arcTo(x,     y,     x + r, y,          r);
        ctx.closePath();
    }}

    // Truncate text to fit maxWidth pixels on the given ctx.
    function truncate(ctx, text, maxWidth) {{
        if (ctx.measureText(text).width <= maxWidth) return text;
        let lo = 0, hi = text.length;
        while (lo < hi) {{
            const mid = (lo + hi + 1) >> 1;
            ctx.measureText(text.slice(0, mid) + '\u2026').width <= maxWidth ? lo = mid : hi = mid - 1;
        }}
        return text.slice(0, lo) + '\u2026';
    }}

    // Word-wrap text into lines, each no wider than maxWidth pixels.
    function wrapText(ctx, text, maxWidth) {{
        const words = text.split(' ');
        const lines = [];
        let current = '';
        for (const word of words) {{
            const test = current ? current + ' ' + word : word;
            if (current && ctx.measureText(test).width > maxWidth) {{
                lines.push(current);
                current = word;
            }} else {{
                current = test;
            }}
        }}
        if (current) lines.push(current);
        return lines;
    }}

    // Height of the expand-button strip at the bottom of each card.
    const EXPAND_H = 18;

    fetch('{b}graph.json')
        .then(r => r.json())
        .then(raw => {{
            // Keep original numeric src/tgt — ForceGraph mutates link objects
            // during simulation, replacing numbers with node references.
            const allNodes = raw.nodes;
            const allLinks = raw.links.map(l => ({{ src: l.source, tgt: l.target }}));
            const nodeMap = new Map(allNodes.map(n => [n.number, n]));

            // Lazy-load avatar images on first access.
            const imgs = new Map();
            function getImg(num, url) {{
                if (!imgs.has(num)) {{
                    const img = new Image();
                    img.src = url;
                    imgs.set(num, img);
                }}
                return imgs.get(num);
            }}

            // Undirected adjacency map: number -> Set<number>.
            // Only include links where BOTH endpoints exist in allNodes so we
            // never add phantom neighbors (cross-refs outside the data set) to
            // the visible set or pass orphan links to ForceGraph.
            const adj = new Map();
            allLinks.forEach(l => {{
                if (!nodeMap.has(l.src) || !nodeMap.has(l.tgt)) return;
                if (!adj.has(l.src)) adj.set(l.src, new Set());
                if (!adj.has(l.tgt)) adj.set(l.tgt, new Set());
                adj.get(l.src).add(l.tgt);
                adj.get(l.tgt).add(l.src);
            }});

            // Place nums sorted ascending in a circle of given radius around (cx, cy).
            // Only sets position for nodes that haven't been placed yet.
            const RING_R = 320;
            function placeInRing(nums, cx, cy) {{
                const sorted = [...nums].sort((a, b) => a - b);
                const count = sorted.length || 1;
                sorted.forEach((num, i) => {{
                    const n = nodeMap.get(num);
                    if (n && n.x == null) {{
                        const angle = (2 * Math.PI * i) / count - Math.PI / 2;
                        n.x = cx + RING_R * Math.cos(angle);
                        n.y = cy + RING_R * Math.sin(angle);
                    }}
                }});
            }}

            let visible = new Set();

            function initVisible() {{
                visible = new Set([startNum]);
                // Reset all positions so re-init starts fresh.
                allNodes.forEach(n => {{
                    delete n.x; delete n.y; delete n.vx; delete n.vy;
                    delete n.fx; delete n.fy;
                }});
                // Pre-position start node at origin.
                const startNode = nodeMap.get(startNum);
                if (startNode) {{ startNode.x = 0; startNode.y = 0; }}
            }}
            initVisible();

            // Expand hidden neighbours of a node, placing them in a ring around it.
            function expandNode(node) {{
                const neighbors = adj.get(node.number) || new Set();
                const newNums = [...neighbors].filter(n => !visible.has(n));
                if (newNums.length === 0) return false;
                newNums.forEach(n => visible.add(n));
                placeInRing(newNums, node.x ?? 0, node.y ?? 0);
                return true;
            }}

            // Fresh node/link arrays for the current visible set. Links are new
            // objects each call so ForceGraph doesn't see stale mutated references.
            function getGraphData() {{
                return {{
                    nodes: allNodes.filter(n => visible.has(n.number)),
                    links: allLinks
                        .filter(l => visible.has(l.src) && visible.has(l.tgt))
                        .map(l => ({{ source: l.src, target: l.tgt }})),
                }};
            }}

            function nodeCanvasObject(node, ctx) {{
                const x = node.x - CW / 2, y = node.y - CH / 2;
                const color = stateColor(node);
                const isStart = node.number === startNum;
                const neighbors = adj.get(node.number) || new Set();
                let hiddenCount = 0;
                for (const n of neighbors) if (!visible.has(n)) hiddenCount++;

                // Card background.
                roundRect(ctx, x, y, CW, CH, CR);
                ctx.fillStyle = isStart ? "#2d333b" : "#1c2128";
                ctx.fill();

                // Outer border — brighter for the start node.
                roundRect(ctx, x, y, CW, CH, CR);
                ctx.strokeStyle = isStart ? "#768390" : "#30363d";
                ctx.lineWidth = isStart ? 2 : 1;
                ctx.stroke();

                // Left state strip (6px) — plain rect clipped to the card's left rounded corners.
                ctx.save();
                roundRect(ctx, x, y, CW, CH, CR);
                ctx.clip();
                ctx.fillStyle = color;
                ctx.fillRect(x, y, 6, CH);
                ctx.restore();

                const textX = x + 14;
                const av = 20;
                const avX = x + CW - av - 8, avY = y + 8;

                // Avatar (clipped circle, top-right).
                const img = getImg(node.number, node.avatar_url);
                if (img && img.complete && img.naturalWidth > 0) {{
                    ctx.save();
                    ctx.beginPath();
                    ctx.arc(avX + av / 2, avY + av / 2, av / 2, 0, Math.PI * 2);
                    ctx.clip();
                    ctx.drawImage(img, avX, avY, av, av);
                    ctx.restore();
                }}

                // State badge (colored pill, left of avatar).
                const stateLabel = node.state.charAt(0).toUpperCase() + node.state.slice(1);
                ctx.font = "bold 9px sans-serif";
                const badgeW = ctx.measureText(stateLabel).width + 10;
                const badgeX = avX - badgeW - 6, badgeY = avY + 3;
                roundRect(ctx, badgeX, badgeY, badgeW, 15, 3);
                ctx.fillStyle = color;
                ctx.fill();
                ctx.fillStyle = "#fff";
                ctx.fillText(stateLabel, badgeX + 5, badgeY + 11);

                // Number row: "#1234  PR/Issue".
                ctx.font = "bold 11px monospace";
                ctx.fillStyle = "#8b949e";
                ctx.fillText("#" + node.number, textX, y + 20);
                const numW = ctx.measureText("#" + node.number).width;
                ctx.font = "10px sans-serif";
                ctx.fillStyle = "#555";
                ctx.fillText(node.is_pr ? "PR" : "Issue", textX + numW + 5, y + 20);

                // Title — word-wrapped to 2 lines, third line truncated.
                ctx.font = "11px sans-serif";
                ctx.fillStyle = "#e6edf3";
                const titleW = CW - 14 - 8; // strip + margins
                const lines = wrapText(ctx, node.title, titleW);
                ctx.fillText(lines[0], textX, y + 38);
                if (lines.length > 1) {{
                    const line2 = lines.length > 2
                        ? truncate(ctx, lines.slice(1).join(' '), titleW)
                        : lines[1];
                    ctx.fillText(line2, textX, y + 54);
                }}

                // Expand button strip along the bottom of the card.
                if (hiddenCount > 0) {{
                    const by = y + CH - EXPAND_H;
                    // Separator line.
                    ctx.strokeStyle = "#30363d";
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(x + 6, by);
                    ctx.lineTo(x + CW, by);
                    ctx.stroke();
                    // Strip background on hover hint.
                    ctx.fillStyle = "#21262d";
                    ctx.fillRect(x + 6, by, CW - 6, EXPAND_H);
                    // Label.
                    ctx.font = "bold 9px sans-serif";
                    ctx.fillStyle = "#768390";
                    const label = "Load +" + hiddenCount + " connected";
                    ctx.fillText(label, x + 14, by + 13);
                }}
            }}

            // Hit area matches the card rectangle for accurate hover/click.
            function nodePointerAreaPaint(node, color, ctx) {{
                ctx.fillStyle = color;
                ctx.fillRect(node.x - CW / 2, node.y - CH / 2, CW, CH);
            }}

            const wrapper = document.getElementById('graph-wrapper');
            const G = ForceGraph()(document.getElementById('graph'))
                .graphData(getGraphData())
                .nodeId('number')
                .nodeLabel(() => '')
                .nodeCanvasObject(nodeCanvasObject)
                .nodeCanvasObjectMode(() => 'replace')
                .nodePointerAreaPaint(nodePointerAreaPaint)
                .linkSource('source')
                .linkTarget('target')
                .linkColor(() => "#b10c00")
                .linkDirectionalArrowLength(6)
                .linkDirectionalArrowRelPos(0.1)
                .warmupTicks(40)
                .width(wrapper.getBoundingClientRect().width)
                .height(wrapper.getBoundingClientRect().height)
                // Moderate repulsion — strong enough to separate cards, weak enough
                // that the link spring can keep connected nodes on screen.
                .d3Force('manybody', d3.forceManyBody().strength(-400))
                .d3Force('collide', d3.forceCollide(Math.sqrt((CW / 2) ** 2 + (CH / 2) ** 2) + 20))
                .d3Force('x', d3.forceX(0).strength(0.05))
                .d3Force('y', d3.forceY(0).strength(0.05))
                .backgroundColor("#0d1117")
                .onNodeDragEnd(node => {{ node.fx = node.x; node.fy = node.y; }})
                .onNodeClick((node, event) => {{
                    const neighbors = adj.get(node.number) || new Set();
                    let hiddenCount = 0;
                    for (const n of neighbors) if (!visible.has(n)) hiddenCount++;

                    // Convert click position to graph space and check if it landed
                    // in the expand strip at the bottom of the card.
                    if (hiddenCount > 0) {{
                        const gp = G.screen2GraphCoords(event.offsetX, event.offsetY);
                        const cardBottom = node.y + CH / 2;
                        if (gp.y >= cardBottom - EXPAND_H) {{
                            if (expandNode(node)) G.graphData(getGraphData());
                            return;
                        }}
                    }}
                    // Card body — open the page.
                    window.open(node.url, '_blank');
                }});

            document.getElementById('btn-reset').addEventListener('click', () => {{
                initVisible();
                G.graphData(getGraphData());
            }});
        }});
}};
</script>
"""


def base_page(title: str, content: str, config: Config) -> str:
    """Wrap content in a complete HTML page (port of baseof.html)."""
    return f"""\
<!doctype html>
<html lang="en" data-bs-theme="dark">

{head_html(title, config)}

<body>
  {nav_html(config)}
  <div class="container">
    <article>
      {content}
    </article>

    {footer_html(config)}
  </div>
</body>

</html>
"""
