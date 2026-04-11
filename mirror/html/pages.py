"""Page-level renderers. Each returns a complete HTML string."""

from __future__ import annotations

from typing import Any

from mirror.config import Config
from mirror.markdown import MarkdownRenderer
from mirror.models import EntryMeta, SiteIndex
from mirror.util import format_date_long, html_escape, urlize
from mirror.html.components import (
    comment_card,
    issue_badge,
    issue_labels,
    list_item_entry,
    render_label,
    svg_icon,
    timeline_event,
)
from mirror.html.templates import base_page, graph_script, search_script


def render_home_page(index: SiteIndex, config: Config) -> str:
    """Render the home page with recent entries, search, labels sidebar, contributors."""
    b = config.base_url
    recent = index.entries[:100]

    # Recent entries list
    entries_html = "\n".join(list_item_entry(e, b) for e in recent)

    # Labels sidebar
    labels_by_count = sorted(index.by_label.items(), key=lambda x: len(x[1]), reverse=True)
    labels_html_parts: list[str] = []
    for label_name, entries in labels_by_count:
        slug = urlize(label_name)
        labels_html_parts.append(
            f'<a href="{b}labels/{slug}/" class="text-decoration-none text-reset m-1">'
            f"{render_label(label_name)}</a>"
        )
    labels_html = "".join(labels_html_parts)

    # Contributors sidebar (top 29)
    contributors_by_count = sorted(
        index.by_contributor.items(), key=lambda x: len(x[1]), reverse=True
    )[:29]
    contributors_html_parts: list[str] = []
    for login, _entries in contributors_by_count:
        avatar = index.contributor_avatars.get(login, "")
        contributors_html_parts.append(
            f'<a href="{b}contributor/{login}/" class="m-1 text-decoration-none text-reset">'
            f'<img src="{avatar}" style="max-width: 32px" class="img-fluid rounded-5 bg-light" '
            f'alt="{html_escape(login)} profile picture"></a>'
        )
    contributors_html = "".join(contributors_html_parts)

    content = f"""\
<h1>Recent Issues and PRs</h1>

<div class="row">

  {search_script(config)}
  <div class="col-12 col-lg-8">
    <div class="input-group mb-3">
      <input class="form-control" id="search-bar" type="search" placeholder="fuzzy search by title, contributor, and number" aria-label="Search">
    </div>
    <div class="list-group" id="search-results"></div>
    <div class="list-group" id="static-recent">
      {entries_html}
    </div>
  </div>

  <div class="col-12 col-lg-4">
    <a href="{b}labels/" class="text-reset text-decoration-none"><b>Labels</b></a>
    <div class="justify-content-start d-flex flex-wrap">
      {labels_html}
    </div>
    <hr>
    <a href="{b}contributors/" class="text-reset text-decoration-none"><b>Contributors</b></a>
    <div class="justify-content-start d-flex flex-wrap">
      {contributors_html}
      <a href="{b}contributors/" class="btn btn-outline-secondary rounded-5">&hellip;</a>
    </div>
  </div>
</div>
"""
    return base_page(config.title, content, config)


def render_entry_page(
    meta: EntryMeta,
    data: dict[str, Any],
    config: Config,
    md: MarkdownRenderer,
) -> str:
    """Render a single issue or PR page."""
    if meta.is_pr:
        content = _render_pull_content(meta, data, config, md)
    else:
        content = _render_issue_content(meta, data, config, md)
    return base_page(f"{meta.title} #{meta.number}", content, config)


def _render_issue_content(
    meta: EntryMeta,
    data: dict[str, Any],
    config: Config,
    md: MarkdownRenderer,
) -> str:
    """Render issue page content (port of partials/render-issue.html)."""
    b = config.base_url
    issue = data["issue"]
    events = data.get("events", [])
    user = issue.get("user", {})
    user_login = user.get("login", "unknown")
    user_login_lower = user_login.lower()

    badge = issue_badge(meta.state, False)
    date_str = format_date_long(meta.date)

    # Initial comment
    initial_comment = comment_card(
        author=user,
        body=issue.get("body"),
        number=meta.number,
        comment_id=issue.get("id", ""),
        created_at=issue.get("created_at", ""),
        author_association=issue.get("author_association"),
        config=config,
        md=md,
    )

    # Timeline events
    contributors: list[dict[str, Any]] = [user]
    events_html_parts: list[str] = []
    for event in events:
        if event.get("event") == "commented" and event.get("actor"):
            contributors.append(event["actor"])
        events_html_parts.append(timeline_event(event, meta.number, config, md))
    events_html = "\n".join(events_html_parts)

    # Sidebar
    sidebar = _render_sidebar(contributors, meta, issue, config)

    return f"""\
<div class="container">
<div class="row">
  <h1 class="h3">
    <span class="text-light">{html_escape(meta.title)}</span>
    <span class="text-muted fw-thin">#{meta.number}</span>
    <a target="_blank" rel="noopener" href="https://github.com/{config.owner}/{config.repository}/issues/{meta.number}" class="text-decoration-none fs-4 text-reset">
      {svg_icon(b, "box-arrow-up-right")}
    </a>
  </h1>
  <span>
    <span class="h4">{badge}</span>
      <a href="{b}contributor/{user_login_lower}/" class="text-decoration-none text-reset"><b>{html_escape(user_login)}</b></a>
      openend this issue on
      {date_str}
  </span>
  <hr class="my-2">
</div>
<div class="container my-3">
  <div class="row">
    <div class="col col-lg-9">
      <ol class="timeline">
        {initial_comment}
        {events_html}
      </ol>
    </div>
    <div class="col col-lg-3">
      {sidebar}
    </div>
  </div>
</div>
</div>
"""


def _render_pull_content(
    meta: EntryMeta,
    data: dict[str, Any],
    config: Config,
    md: MarkdownRenderer,
) -> str:
    """Render PR page content (port of partials/render-pull.html)."""
    b = config.base_url
    pull = data["pull"]
    events = data.get("events", [])
    user = pull.get("user", {})
    user_login = user.get("login", "unknown")
    user_login_lower = user_login.lower()

    badge = issue_badge(meta.state, True)

    commits = pull.get("commits", 0)
    base_label = html_escape(pull.get("base", {}).get("label", ""))
    head_label = html_escape(pull.get("head", {}).get("label", ""))
    changed_files = pull.get("changed_files", 0)
    additions = pull.get("additions", 0)
    deletions = pull.get("deletions", 0)

    # Initial comment
    initial_comment = comment_card(
        author=user,
        body=pull.get("body"),
        number=meta.number,
        comment_id=pull.get("id", ""),
        created_at=pull.get("created_at", ""),
        author_association=pull.get("author_association"),
        config=config,
        md=md,
    )

    # Timeline events
    contributors: list[dict[str, Any]] = [user]
    events_html_parts: list[str] = []
    for event in events:
        ev_type = event.get("event", "")
        if ev_type == "commented" and event.get("actor"):
            contributors.append(event["actor"])
        elif ev_type == "reviewed" and event.get("user"):
            contributors.append(event["user"])
        elif ev_type == "code_review":
            for comment in event.get("data", []):
                if comment.get("user"):
                    contributors.append(comment["user"])
        events_html_parts.append(timeline_event(event, meta.number, config, md))
    events_html = "\n".join(events_html_parts)

    # Requested reviewers sidebar section
    requested_reviewers = pull.get("requested_reviewers", [])
    reviewers_html = ""
    if requested_reviewers:
        reviewer_parts: list[str] = []
        for rv in requested_reviewers:
            rv_login = rv.get("login", "?")
            rv_avatar = rv.get("avatar_url", "?")
            reviewer_parts.append(
                f'<a href="{b}contributor/{rv_login.lower()}/" class="text-decoration-none text-reset m-2">'
                f'<img src="{rv_avatar}" class="img-fluid rounded-5" width=24>'
                f'<span class="text-reset text-decoration-none">{html_escape(rv_login)}</span></a>'
            )
        reviewers_html = f"""\
      <p class="m-3">
        <label>Review Requested</label>
        <br>
        {"".join(reviewer_parts)}
      </p>
"""

    # Sidebar
    sidebar = _render_sidebar(contributors, meta, pull, config, reviewers_html)

    # Tabs
    tabs = f"""\
      <ul class="nav nav-tabs mt-3">
        <li class="nav-item">
          <a class="nav-link active" aria-current="page" href="#">Conversation</a>
        </li>
        <li class="nav-item">
          <a class="nav-link text-reset" target="_blank" rel="noopener" href="https://github.com/{config.owner}/{config.repository}/pull/{meta.number}/commits/">Commits<span class="badge text-reset">{commits}</span>
            {svg_icon(b, "box-arrow-up-right", 12, 12)}
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link text-reset" target="_blank" rel="noopener" href="https://github.com/{config.owner}/{config.repository}/pull/{meta.number}/files/">Files<span class="badge text-reset">{changed_files}</span>
            {svg_icon(b, "box-arrow-up-right", 12, 12)}
          </a>
        </li>
        <li class="nav-item">
          <a class="nav-link text-reset" target="_blank" rel="noopener" href="https://github.com/{config.owner}/{config.repository}/pull/{meta.number}/checks/">Check
            {svg_icon(b, "box-arrow-up-right", 12, 12)}
          </a>
        </li>
      </ul>
"""

    return f"""\
<div class="container">
<div class="row">
  <h1 class="h3">
    <span class="text-light">{html_escape(meta.title)}</span>
    <span class="text-muted fw-thin">#{meta.number}</span>
    <a href="https://github.com/{config.owner}/{config.repository}/issues/{meta.number}" class="text-decoration-none text-reset fs-4">
      {svg_icon(b, "box-arrow-up-right")}
    </a>
  </h1>
  <span>
    <span class="h4">{badge}</span>
    <a href="{b}contributor/{user_login_lower}/" class="text-decoration-none text-reset"><b>{html_escape(user_login)}</b></a>
      wants to merge
      {commits}
      commits into
      <span class="badge">{base_label}</span>
      from
      <span class="badge">{head_label}</span>
      changing
      {changed_files}
      files
      <span class="badge"><span class="text-success">+{additions}</span> <span class="text-danger">&minus;{deletions}</span> </span>
      {tabs}
  </span>
</div>
<div class="container my-3">
  <div class="row">
    <div class="col col-lg-9">
      <ol class="timeline">
        {initial_comment}
        {events_html}
      </ol>
    </div>
    <div class="col col-lg-3">
      {sidebar}
    </div>
  </div>
</div>
</div>
"""


def _render_sidebar(
    contributors: list[dict[str, Any]],
    meta: EntryMeta,
    item: dict[str, Any],
    config: Config,
    extra_html: str = "",
) -> str:
    """Render the right sidebar: contributors, labels, milestone, optional extras."""
    b = config.base_url

    # Deduplicate contributors by login
    seen: set[str] = set()
    unique_contributors: list[dict[str, Any]] = []
    for c in contributors:
        if c is None:
            continue
        login = c.get("login", "")
        if login and login not in seen:
            seen.add(login)
            unique_contributors.append(c)

    contrib_parts: list[str] = []
    for c in unique_contributors:
        login = c.get("login", "unknown")
        avatar = c.get("avatar_url", "?")
        contrib_parts.append(
            f'<a href="{b}contributor/{login.lower()}/" class="d-inline-block text-decoration-none text-reset m-1">'
            f'<img src="{avatar}" class="img-fluid rounded-5" width=24>'
            f'<span class="text-reset text-decoration-none">{html_escape(login)}</span></a>'
        )

    labels_html = ""
    if meta.labels:
        labels_html = f"""\
      <p class="m-3">
        <span>Labels</span>
        <br>
        <span>{issue_labels(meta.labels, b)}</span>
      </p>
"""

    milestone_html = ""
    if item.get("milestone"):
        ms = item["milestone"]
        ms_state = ms.get("state", "open")
        ms_title = html_escape(ms.get("title", ""))
        milestone_html = f"""\
      <p class="m-3">
        <span>Milestone</span>
        <br>
        <span class="badge state-{ms_state}">{ms_title}</span>
      </p>
"""

    return f"""\
      <p class="m-3">
        <label>Contributors</label>
        <br>
          {"".join(contrib_parts)}
        </p>
      {extra_html}
      {labels_html}
      {milestone_html}
"""


def render_contributors_page(index: SiteIndex, config: Config) -> str:
    """Render the contributors taxonomy page (grid of contributor cards)."""
    b = config.base_url

    contributors_by_count = sorted(
        index.by_contributor.items(), key=lambda x: len(x[1]), reverse=True
    )

    card_parts: list[str] = []
    for login, entries in contributors_by_count:
        if len(entries) <= 2:
            continue
        avatar = index.contributor_avatars.get(login, "")
        pulls = sum(1 for e in entries if e.is_pr)
        issues = len(entries) - pulls
        card_parts.append(f"""\
          <div class="col my-2">
            <a href="{b}contributor/{login}/" class="text-decoration-none text-reset">
              <div class="card">
                <div class="row g-0">
                  <div class="col-md-3">
                    <img src="{avatar}" height=32 class="img-fluid rounded-start bg-light" alt="{html_escape(login)} profile picture">
                  </div>
                  <div class="col-md-9">
                    <div class="card-body">
                      <h5 class="card-title">{html_escape(login)}</h5>
                      <span>{pulls} pulls</span><br>
                      <span>{issues} issues</span>
                    </div>
                  </div>
                </div>
              </div>
            </a>
          </div>
""")

    content = f"""\
<h1>Contributors</h1>
<div class="container">
  <div class="row row-cols-1 row-cols-sm-2 row-cols-lg-3">
    {"".join(card_parts)}
  </div>
</div>
"""
    return base_page("Contributors", content, config)


def render_contributor_page(
    login: str,
    entries: list[EntryMeta],
    avatar: str,
    config: Config,
) -> str:
    """Render an individual contributor profile page."""
    b = config.base_url
    pulls = [e for e in entries if e.is_pr]
    issues = [e for e in entries if not e.is_pr]

    pulls_html = "\n".join(list_item_entry(e, b) for e in pulls)
    issues_html = "\n".join(list_item_entry(e, b) for e in issues)

    if not pulls:
        pulls_html = '<span class="list-group-item text-center" aria-disabled="true">---</span>'
    if not issues:
        issues_html = '<span class="list-group-item text-center" aria-disabled="true">---</span>'

    content = f"""\
<p>
  <img src="{avatar}" width=96 class="img-fluid rounded-5 mx-3 bg-light" alt="{html_escape(login)} profile picture">
  <span class="h2">{html_escape(login)}</span>
  <a target="_blank" rel="noopener" href="https://github.com/{login}" class="text-decoration-none fs-4 text-reset">
    {svg_icon(b, "box-arrow-up-right")}
  </a>
</p>

<div class="container">
  <div class="row">
    <div class="col-12 col-md-6">
      <div class="list-group my-3">
        <span class="list-group-item " aria-disabled="true">Pull-Requests</span>
        {pulls_html}
      </div>
    </div>
    <div class="col-12 col-md-6">
      <div class="list-group my-3">
        <span class="list-group-item" aria-disabled="true">Issues</span>
        {issues_html}
      </div>
    </div>
  </div>
</div>
"""
    return base_page(login, content, config)


def render_labels_page(index: SiteIndex, config: Config) -> str:
    """Render the labels taxonomy page (grid of label cards)."""
    b = config.base_url
    labels_by_count = sorted(index.by_label.items(), key=lambda x: len(x[1]), reverse=True)

    card_parts: list[str] = []
    for label_name, entries in labels_by_count:
        slug = urlize(label_name)
        card_parts.append(f"""\
          <div class="col my-2">
            <a href="{b}labels/{slug}/" class="text-decoration-none text-reset">
              <div class="card">
                <div class="card-body d-flex justify-content-between align-items-center">
                  {html_escape(label_name)}
                  <span class="badge text-bg-primary">{len(entries)}</span>
                </div>
              </div>
            </a>
          </div>
""")

    content = f"""\
<h1>Labels</h1>
<div class="container">
  <div class="row row-cols-3">
    {"".join(card_parts)}
  </div>
</div>
"""
    return base_page("Labels", content, config)


def render_label_page(
    label: str, entries: list[EntryMeta], config: Config,
) -> str:
    """Render a page listing all entries with a given label."""
    b = config.base_url
    entries_html = "\n".join(list_item_entry(e, b) for e in entries)

    content = f"""\
<h2>
  Labeled
  {render_label(label)}
</h2>
<div class="list-group">
  {entries_html}
</div>
"""
    return base_page(f"Label: {label}", content, config)


def render_graph_page(config: Config) -> str:
    """Render the graph visualization page."""
    content = graph_script(config)
    return base_page("Graph", content, config)
