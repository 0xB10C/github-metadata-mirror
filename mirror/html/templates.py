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
    """Return the force-graph JS (port of partials/graph.html)."""
    b = config.base_url
    return f"""\
<div id="graph-wrapper" class="container">
    <div id="graph"></div>
</div>

<script src="//unpkg.com/force-graph"></script>
<script src="//unpkg.com/d3-force"></script>
<script src="//unpkg.com/d3-quadtree"></script>

<script>
    window.onload = function () {{
        function nodeColor(n) {{
            if (n.state == "merged" || n.state == "complete") {{
                return "#6610f2";
            }} else if (n.state == "draft") {{
                return "";
            }} else if (n.state == "closed") {{
                return "#6c757d";
            }} else if (n.state == "open") {{
                return "#188754";
            }}
            return "black";
        }}

        function nodeCanvasObject(node, ctx) {{
            const size = 12;
            ctx.drawImage(node.img, node.x  - size / 2, node.y - size / 2, size, size);

            ctx.beginPath();
            if (node.is_pr) {{
                ctx.arc(node.x, node.y, 7, 0, Math.PI * 2, true);
            }} else {{
                ctx.rect(node.x - 7, node.y - 7, 14, 14);
            }}
            ctx.strokeStyle = nodeColor(node);
            ctx.lineWidth = 3;
            ctx.stroke();

            ctx.fillStyle = "gray";
            ctx.font = "12px monospace";
            ctx.fillText("#" + node.number, node.x + 12, node.y + 4);
        }}

        fetch('{b}graph.json')
            .then((response) => response.json())
            .then((graph) => {{

            graph.nodes.forEach(n => {{
                const img = new Image();
                img.src = n.avatar_url;
                n.img = img;
            }});

            let graphWrapper = document.getElementById('graph-wrapper')

            const Graph = ForceGraph()
            (document.getElementById('graph'))
                .graphData(graph)
                .nodeId('number')
                .nodeLabel(n => (n.is_pr ? "PR " : "Issue ") +  "#" + n.number + ": " + n.title)
                .nodeColor(nodeColor)
                .nodeVal(8)
                .nodeAutoColorBy("state")
                .linkSource('source')
                .linkTarget('target')
                .linkColor("#b10c00")
                .warmupTicks(20)
                .width(graphWrapper.getBoundingClientRect().width)
                .height(graphWrapper.getBoundingClientRect().height * 0.8)
                .d3Force('manybody', d3.forceManyBody().strength(-100))
                .d3Force('collide', d3.forceCollide(20))
                .d3Force('x', d3.forceX(0).strength(0.05))
                .d3Force('y', d3.forceY(0).strength(0.05))
                .backgroundColor("white")
                .linkDirectionalArrowLength(6)
                .linkDirectionalArrowRelPos(0.1)
                .nodeCanvasObject(nodeCanvasObject)
                .onNodeDragEnd(node => {{
                    node.fx = node.x;
                    node.fy = node.y;
                }})
                .onNodeClick(node => window.open(node.url, '_blank').focus())
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
