"""Reusable HTML components: badges, labels, comments, timeline events, reviews.

Each function is pure (returns HTML string, no side effects).
"""

from __future__ import annotations

import re
from typing import Any

from mirror.body import render_body
from mirror.config import Config
from mirror.markdown import MarkdownRenderer
from mirror.models import EntryMeta
from mirror.util import (
    fnv1a_32,
    format_date_long,
    format_date_medium,
    format_time_short,
    html_escape,
    truncate,
    urlize,
)


def svg_icon(base_url: str, icon: str, width: int = 16, height: int = 16) -> str:
    return (
        f'<svg width="{width}" height="{height}" fill="currentColor">'
        f'<use xlink:href="{base_url}img/bootstrap-icons.svg#{icon}"/>'
        f"</svg>"
    )


def issue_badge(state: str, is_pr: bool) -> str:
    """State-colored badge pill (port of partials/issue-badge.html)."""
    label = "pull" if is_pr else "issue"
    return f'<span class="badge rounded-pill state-{state}">{label}</span>'


def render_label(name: str) -> str:
    """Label pill with FNV-1a color (port of partials/render-label.html)."""
    hue = fnv1a_32(name) % 360
    return (
        f'<span class="text-small p-1 mx-1 fw-light rounded-2" '
        f'style="font-size: 0.9em; color: hsl({hue} 80% 90%); '
        f'border: 1px solid hsl({hue} 10% 40%);">{html_escape(name)}</span>'
    )


def issue_labels(labels: list[str], base_url: str) -> str:
    """Render all labels for an entry (port of partials/issue-labels.html)."""
    parts: list[str] = []
    for label in labels:
        slug = urlize(label)
        parts.append(
            f'<a href="{base_url}labels/{slug}/" class="text-decoration-none mx-1">'
            f"{render_label(label)}</a>"
        )
    return "".join(parts)


def list_item_entry(entry: EntryMeta, base_url: str) -> str:
    """Entry in an issue/PR list (port of partials/list-item-entry.html)."""
    badge = issue_badge(entry.state, entry.is_pr)
    date_str = format_date_long(entry.date)
    labels = issue_labels(entry.labels, base_url)
    contributor_lower = entry.contributor.lower()
    return f"""\
<div class="list-group-item">
      <a href="{base_url}{entry.number}/" class="text-decoration-none text-reset">
        <span class="h6">{badge}</span>
        <span class="h5 text-light">
          {html_escape(entry.title)}
        </span>
        <span class="text-mute">#{entry.number}</span>
      </a>
      <br>
      <span>
        <a href="{base_url}contributor/{contributor_lower}/" class="text-decoration-none text-reset">
          <b>{html_escape(entry.contributor)}</b>
        </a>
        on
        {date_str}
        <span>{labels}</span>
      </span>
</div>
"""


def comment_card(
    author: dict[str, Any] | None,
    body: str | None,
    number: int,
    comment_id: int | str,
    created_at: str,
    author_association: str | None,
    config: Config,
    md: MarkdownRenderer,
) -> str:
    """A comment card in the timeline (port of partials/comment.html)."""
    name = "unknown"
    avatar_url = "?"
    if author is not None:
        name = author.get("login", "unknown")
        avatar_url = author.get("avatar_url", "?")

    b = config.base_url
    name_lower = name.lower()
    assoc = (author_association or "").lower()
    time_str = format_time_short(created_at)
    date_str = format_date_long(created_at)
    body_html = render_body(body, config, md)

    return f"""\
<li class="timeline-item d-block my-3">
  <span class="timeline-item-icon" style>
    <a href="{b}contributor/{name_lower}/">
      <img src="{avatar_url}" class="rounded-5 d-block img-fluid bg-light">
    </a>
  </span>
  <div class="timeline-item-description" style="margin-top: -42px;">
    <div class="card" id="issuecomment-{comment_id}">
      <div class="card-header d-flex justify-content-between">
        <span>
          <a href="{b}contributor/{name_lower}/" class="text-decoration-none text-reset"><b>{html_escape(name)}</b></a>
          commented at {time_str} on {date_str}:
        </span>
        <span>
          <span class="badge">{assoc}</span>
            <span>
              <a target="_blank" rel="noopener" href="https://github.com/{config.owner}/{config.repository}/pull/{number}#issuecomment-{comment_id}" class="text-decoration-none text-reset px-1">
                {svg_icon(b, "box-arrow-up-right", 14, 14)}
              </a>
              <a href="#issuecomment-{comment_id}" class="text-decoration-none text-reset px-1">
                {svg_icon(b, "share", 14, 14)}
              </a>
            </span>
          </span>
        </span>
      </div>
      <div class="card-body py-2 body-text text-decoration-none">
        {body_html}
      </div>
    </div>
  </div>
</li>
"""


def _timeline_icon_circle(base_url: str, icon: str, extra_class: str = "") -> str:
    cls = f"timeline-item-icon-circle {extra_class}".strip()
    return (
        f'<span class="timeline-item-icon">'
        f'<span class="{cls}">'
        f"{svg_icon(base_url, icon)}"
        f"</span></span>"
    )


def timeline_event(
    event: dict[str, Any],
    number: int,
    config: Config,
    md: MarkdownRenderer,
) -> str:
    """Render a single timeline event (port of partials/render-event.html)."""
    b = config.base_url
    ev = event.get("event", "")

    name = "unknown"
    if event.get("actor") is not None:
        name = event["actor"].get("login", "unknown")
    elif event.get("user") is not None:
        name = event["user"].get("login", "unknown")

    # Silent events — no output
    if ev in ("subscribed", "unsubscribed", "mentioned", "review_dismissed",
              "connected", "disconnected", "line-commented"):
        return ""

    if ev == "commented":
        body = event.get("body", "")
        if not body:
            return ""
        return comment_card(
            author=event.get("actor"),
            body=body,
            number=number,
            comment_id=event.get("id", ""),
            created_at=event.get("created_at", ""),
            author_association=event.get("author_association"),
            config=config,
            md=md,
        )

    if ev == "code_review":
        return review_card(
            comments=event.get("data", []),
            number=number,
            config=config,
            md=md,
        )

    date_str = ""
    if event.get("created_at"):
        date_str = f"on {format_date_medium(event['created_at'])}"

    if ev == "committed":
        msg = event.get("message", "")
        sha = truncate(event.get("sha", ""), 10)
        lines = msg.split("\n")
        head_line = lines[0] if lines else ""
        if len(lines) > 1:
            rest = "\n".join(lines[1:])
            body = (
                f"<details>"
                f"<summary class='font-monospace'>{html_escape(head_line)}</summary>"
                f"<code><pre>{html_escape(rest)}</pre></code>"
                f"</details>"
            )
        else:
            body = f"<span class='font-monospace'>{html_escape(head_line)}</span>"
        return f"""\
<li class="timeline-item mb-4">
  {_timeline_icon_circle(b, "node-plus-fill")}
  <div class="timeline-item-description d-flex justify-content-between w-100">
      {body}
      <span class="">{sha}</span>
  </div>
</li>
"""

    if ev == "head_ref_force_pushed":
        return _simple_event(b, "fast-forward-fill", f"<b>{html_escape(name)}</b> force-pushed {date_str}")

    if ev == "base_ref_force_pushed":
        return _simple_event(b, "fast-forward-fill", f"<b>{html_escape(name)}</b> force-pushed the base branch {date_str}")

    if ev == "marked_as_duplicate":
        return _simple_event(b, "layers-fill", f"<b>{html_escape(name)}</b> marked this as duplicate {date_str}")

    if ev == "pinned":
        return _simple_event(b, "geo-fill", f"<b>{html_escape(name)}</b> pinned this {date_str}")

    if ev == "unpinned":
        return _simple_event(b, "geo", f"<b>{html_escape(name)}</b> unpinned this {date_str}")

    if ev == "comment_deleted":
        return _simple_event(b, "trash-fill", f"<b>{html_escape(name)}</b> deleted a comment {date_str}")

    if ev == "closed":
        return (
            f'<li class="timeline-item my-1">'
            f'{_timeline_icon_circle(b, "x", "state-closed")}'
            f'<div class="timeline-item-description">'
            f"<b>{html_escape(name)}</b> closed this {date_str}"
            f"</div><hr></li>"
        )

    if ev == "added_to_project":
        col = event.get("project_card", {}).get("column_name", "?")
        return _simple_event(b, "kanban-fill", f'<b>{html_escape(name)}</b> added this to the "{html_escape(col)}" column in a project') + "<hr>"

    if ev == "removed_from_project":
        col = event.get("project_card", {}).get("column_name", "?")
        return _simple_event(b, "kanban-fill", f'<b>{html_escape(name)}</b> removed this from the "{html_escape(col)}" column in a project') + "<hr>"

    if ev == "moved_columns_in_project":
        pc = event.get("project_card", {})
        prev = pc.get("previous_column_name", "?")
        curr = pc.get("column_name", "?")
        return _simple_event(b, "kanban-fill", f'<b>{html_escape(name)}</b> moved this from the "{html_escape(prev)}" to the "{html_escape(curr)}" column in a project') + "<hr>"

    if ev == "reopened":
        return (
            f'<li class="timeline-item my-1">'
            f'{_timeline_icon_circle(b, "arrow-clockwise", "state-open")}'
            f'<div class="timeline-item-description">'
            f"<b>{html_escape(name)}</b> reopened this {date_str}"
            f"</div><hr></li>"
        )

    if ev == "merged":
        return (
            f'<li class="timeline-item my-1">'
            f'{_timeline_icon_circle(b, "diagram-2-fill", "state-merged")}'
            f'<div class="timeline-item-description">'
            f"<b>{html_escape(name)}</b> merged this {date_str}"
            f"</div></li>"
        )

    if ev == "reviewed":
        state_lower = (event.get("state") or "").lower()
        parts: list[str] = []

        if state_lower != "commented":
            if state_lower == "approved":
                icon = "check-lg"
            elif state_lower == "changes_requested":
                icon = "plus-slash-minus"
            else:
                icon = "question-square-fill"
            parts.append(_simple_event(b, icon, f"<b>{html_escape(name)}</b> {state_lower}"))

        review_body = event.get("body")
        if review_body:
            parts.append(comment_card(
                author=event.get("user"),
                body=review_body,
                number=number,
                comment_id=event.get("id", ""),
                created_at=event.get("submitted_at", event.get("created_at", "")),
                author_association=event.get("author_association"),
                config=config,
                md=md,
            ))
        return "".join(parts)

    if ev == "assigned":
        assignee = event.get("assignee", {}).get("login", "?")
        return _simple_event(b, "signpost-fill", f"<b>{html_escape(name)}</b> assigned <b>{html_escape(assignee)}</b> {date_str}")

    if ev == "unassigned":
        assignee = event.get("assignee", {}).get("login", "?")
        return _simple_event(b, "signpost-fill", f"<b>{html_escape(name)}</b> unassigned <b>{html_escape(assignee)}</b> {date_str}")

    if ev == "base_ref_changed":
        return _simple_event(b, "signpost-fill", f"<b>{html_escape(name)}</b> changed the base branch {date_str}")

    if ev == "milestoned":
        title = event.get("milestone", {}).get("title", "?")
        return _simple_event(b, "signpost-fill", f"<b>{html_escape(name)}</b> added this to the milestone {html_escape(title)} {date_str}")

    if ev == "demilestoned":
        title = event.get("milestone", {}).get("title", "?")
        return _simple_event(b, "signpost", f"<b>{html_escape(name)}</b> removed this from the milestone {html_escape(title)} {date_str}")

    if ev == "labeled":
        label_name = event.get("label", {}).get("name", "?")
        return _simple_event(b, "tag-fill", f"<b>{html_escape(name)}</b> added the label {render_label(label_name)} {date_str}")

    if ev == "unlabeled":
        label_name = event.get("label", {}).get("name", "?")
        return _simple_event(b, "tag", f"<b>{html_escape(name)}</b> removed the label {render_label(label_name)} {date_str}")

    if ev == "convert_to_draft":
        return _simple_event(b, "file-earmark", f"<b>{html_escape(name)}</b> marked this as a draft {date_str}")

    if ev == "ready_for_review":
        return _simple_event(b, "file-earmark-fill", f"<b>{html_escape(name)}</b> marked this as ready for review {date_str}")

    if ev == "review_requested":
        requester = event.get("review_requester", {}).get("login", "?")
        reviewer = event.get("requested_reviewer", {}).get("login", "?")
        return _simple_event(b, "person-lines-fill", f"<b>{html_escape(requester)}</b> requested review from <b>{html_escape(reviewer)}</b> {date_str}")

    if ev == "review_request_removed":
        requester = event.get("review_requester", {}).get("login", "?")
        reviewer = event.get("requested_reviewer", {}).get("login", "?")
        return _simple_event(b, "person-x-fill", f"{html_escape(requester)} removed review request from {html_escape(reviewer)} {date_str}")

    if ev == "renamed":
        old = event.get("rename", {}).get("from", "?")
        new = event.get("rename", {}).get("to", "?")
        return _simple_event(b, "card-heading",
            f"<b>{html_escape(name)}</b> renamed this:<br>"
            f"<s>{html_escape(old)}</s><br>{html_escape(new)}<br>{date_str}")

    if ev == "locked":
        return _simple_event(b, "lock-fill", f"<b>{html_escape(name)}</b> locked this {date_str}")

    if ev == "unlocked":
        return _simple_event(b, "unlock-fill", f"<b>{html_escape(name)}</b> unlocked this {date_str}")

    if ev == "head_ref_deleted":
        return _simple_event(b, "trash-fill", f"<b>{html_escape(name)}</b> deleted the branch {date_str}")

    if ev == "head_ref_restored":
        return _simple_event(b, "arrow-clockwise", f"<b>{html_escape(name)}</b> restored the branch {date_str}")

    if ev == "referenced":
        commit_url = event.get("commit_url", "")
        # Rewrite API URL to web URL
        commit_url = commit_url.replace("api.", "").replace("/repos", "").replace("commits", "commit")
        commit_id = truncate(event.get("commit_id", ""), 10)
        return _simple_event(b, "link-45deg",
            f'<b>{html_escape(name)}</b> referenced this in commit '
            f'<a href="{commit_url}">{commit_id}</a> {date_str}')

    if ev == "cross-referenced":
        source = event.get("source", {})
        source_type = source.get("type", "")
        source_issue = source.get("issue", {})
        source_number = source_issue.get("number", "?")
        source_title = source_issue.get("title", "?")
        source_user = source_issue.get("user", {}).get("login", "?")
        return _simple_event(b, "box-arrow-in-down-right",
            f"<b>{html_escape(name)}</b> cross-referenced this {date_str} "
            f'from {source_type} <a class="text-decoration-none" href="{b}{source_number}/">'
            f"<b>{html_escape(source_title)}</b></a> "
            f"by <b>{html_escape(source_user)}</b>")

    # Unknown event type
    return (
        f'<li class="timeline-item my-1">'
        f'<span class="timeline-item-icon"><span class="badge text-bg-info">?</span></span>'
        f'<div class="timeline-item-description">{ev} {html_escape(name)}</div>'
        f"</li>"
    )


def _simple_event(base_url: str, icon: str, description: str) -> str:
    return (
        f'<li class="timeline-item my-1">'
        f"{_timeline_icon_circle(base_url, icon)}"
        f'<div class="timeline-item-description">{description}</div>'
        f"</li>"
    )


def review_card(
    comments: list[dict[str, Any]],
    number: int,
    config: Config,
    md: MarkdownRenderer,
) -> str:
    """Code review card with diff hunk (port of partials/review.html)."""
    if not comments:
        return ""

    b = config.base_url
    first = comments[0]

    # Extract line number from hunk header: @@ -48,6 +61,33 @@
    hunk = first.get("diff_hunk", "")
    line_number = _extract_hunk_line_number(hunk)

    # Determine if outdated
    is_current = first.get("original_commit_id") == first.get("commit_id")
    outdated_badge = "" if is_current else '<span class="badge">outdated</span>'
    open_attr = "open" if is_current else ""

    path = first.get("path", "?")
    original_line = first.get("original_line", "?")
    original_commit = truncate(first.get("original_commit_id", ""), 10)

    # Render hunk as plain <pre> with line numbers and +/- coloring
    hunk_html = _render_diff_hunk(hunk, line_number)

    # Render individual review comments
    comment_parts: list[str] = []
    for comment in comments:
        c_name = "unknown"
        c_avatar = "?"
        if comment.get("user") is not None:
            c_name = comment["user"].get("login", "unknown")
            c_avatar = comment["user"].get("avatar_url", "?")

        c_name_lower = c_name.lower()
        c_id = comment.get("id", "")
        c_date = comment.get("created_at", "")
        time_str = format_time_short(c_date) if c_date else ""
        date_str = format_date_long(c_date) if c_date else ""
        body_html = render_body(comment.get("body"), config, md)

        comment_parts.append(f"""\
        <div class="row">
          <div class="col-1"></div>
          <div class="col-11">
            <hr width="1" size="20" style="border: 1px solid gray; margin: 0em 2em;" />
          </div>
        </div>
        <div class="row" id="discussion_r{c_id}">
          <div class="col-1 px-0 px-md-3">
            <img src="{c_avatar}" class="rounded-5 d-block float-end img-fluid bg-light">
          </div>
          <div class="col-11">
            <div class="card">
              <div class="card-header d-flex justify-content-between">
                <span>
                  <a href="{b}contributor/{c_name_lower}/" class="text-decoration-none text-reset"><b>{html_escape(c_name)}</b></a>
                  commented at {time_str} on {date_str}:
                </span>
                <span>
                  <a target="_blank" rel="noopener" href="https://github.com/{config.owner}/{config.repository}/pull/{number}#discussion_r{c_id}" class="text-decoration-none text-reset px-1">
                    {svg_icon(b, "box-arrow-up-right", 14, 14)}
                  </a>
                  <a href="#discussion_r{c_id}" class="text-decoration-none text-reset px-1">
                    {svg_icon(b, "share", 14, 14)}
                  </a>
                </span>
              </div>
            <div class="card-body body-text text-decoration-none">
              {body_html}
            </div>
          </div>
        </div>
      </div>
""")

    comments_html = "\n".join(comment_parts)

    return f"""\
<li class="timeline-item my-1 d-block">
  <span class="timeline-item-icon">
    <span class="timeline-item-icon-circle">
      {svg_icon(b, "braces")}
    </span>
  </span>

  <div class="timeline-item-description" style="margin-top: -58px;">
  <details class="card my-2 px-0" {open_attr}>
    <summary class="card-header justify-content-between">
      <span class="text-wrap">
        in
        <span class="font-monospace text-wrap">{html_escape(path)}:{original_line}</span>
        in
        <span class="font-monospace text-wrap">{original_commit}</span>
      </span>
      {outdated_badge}
    </summary>
    <div class="card-body">
      {hunk_html}
      <hr class="p-0 m-0">
      {comments_html}
  </details>
</div>
</li>
"""


def _extract_hunk_line_number(hunk: str) -> int:
    """Extract the start line number from a diff hunk header like @@ -48,6 +61,33 @@."""
    m = re.search(r"@@\s+[^\s]+\s+\+(\d+)", hunk)
    if m:
        return max(0, int(m.group(1)) - 1)
    return 0


def _render_diff_hunk(hunk: str, line_start: int) -> str:
    """Render a diff hunk as <pre> with line numbers and +/- coloring."""
    if not hunk:
        return ""

    lines = hunk.split("\n")
    # Trim to last 6 lines if >10 lines (matching Hugo template behavior)
    if len(lines) > 10:
        line_start += len(lines) - 6
        lines = lines[-6:]

    parts: list[str] = ['<pre style="overflow-x: auto;">']
    for i, line in enumerate(lines):
        ln = line_start + i
        escaped = html_escape(line)
        if line.startswith("+"):
            parts.append(f'<span style="color: var(--bs-success);">{ln:4d} | {escaped}</span>')
        elif line.startswith("-"):
            parts.append(f'<span style="color: var(--bs-danger);">{ln:4d} | {escaped}</span>')
        elif line.startswith("@@"):
            parts.append(f'<span style="color: var(--bs-info);">{ln:4d} | {escaped}</span>')
        else:
            parts.append(f"{ln:4d} | {escaped}")
    parts.append("</pre>")
    return "\n".join(parts)
