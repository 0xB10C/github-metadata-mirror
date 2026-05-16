"""Plain-markdown renderer for issue/PR entry pages.

Emits one `index.md` per entry alongside the existing `index.html`. Raw
markdown bodies from the backup JSON are passed through verbatim -- no link
rewriting (no `#NN` substitution, no `@user` → `/contributor/...`, no GitHub
URL → local URL rewriting). The output is intended for LLM consumption.
"""

from __future__ import annotations

import json
from typing import Any

from mirror.config import Config
from mirror.models import EntryMeta


DIFF_HUNK_TAIL_LINES = 12


SILENT_EVENTS = frozenset({
    "subscribed", "unsubscribed", "mentioned", "review_dismissed",
    "connected", "disconnected", "line-commented",
})


def render_llms_txt(config: Config) -> str:
    """Render a root-level llms.txt descriptor pointing LLM agents at the markdown layout."""
    repo_url = f"https://github.com/{config.owner}/{config.repository}"
    return f"""# {config.title}

> A mirror of GitHub issues and pull requests for [{config.owner}/{config.repository}]({repo_url}).

## Layout

- Each issue or PR has a plain-markdown document at `{config.base_url}{{number}}/index.md`.
- Each document opens with YAML front matter (number, type, state, author, dates, labels, linked, participants, source URL).
- The issue/PR body and every comment are preserved verbatim -- no link rewriting, no rendering.

## Resources

- [Search index]({config.base_url}index.json) -- MiniSearch JSON of every entry.
- [Cross-reference graph]({config.base_url}graph.json) -- issue/PR link graph.
- [Generator source](https://github.com/0xB10C/github-metadata-mirror) -- code that produced this mirror.
"""


def render_entry_markdown(
    meta: EntryMeta,
    data: dict[str, Any],
    config: Config,
    linked_entries: list[EntryMeta],
) -> str:
    """Render a single issue/PR as a plain-markdown document."""
    entry = data["pull"] if meta.is_pr else data["issue"]
    title = entry.get("title", "")
    body = entry.get("body") or ""

    parts: list[str] = []
    parts.append(_front_matter(meta, data, config, linked_entries))
    parts.append("")
    parts.append(f"# {title} (#{meta.number})")
    parts.append("")

    if body.strip():
        parts.append(body.rstrip())
        parts.append("")

    events = data.get("events", []) or []
    timeline_blocks = [
        block for block in (_render_event(ev) for ev in events) if block
    ]
    if timeline_blocks:
        parts.append("## Timeline")
        parts.append("")
        parts.extend(timeline_blocks)

    return "\n".join(parts).rstrip() + "\n"


def _front_matter(
    meta: EntryMeta,
    data: dict[str, Any],
    config: Config,
    linked_entries: list[EntryMeta],
) -> str:
    is_pr = meta.is_pr
    entry = data["pull"] if is_pr else data["issue"]

    lines: list[str] = ["---"]
    lines.append(f"number: {meta.number}")
    lines.append(f"type: {'pull' if is_pr else 'issue'}")
    lines.append(f"title: {_yaml_str(entry.get('title', ''))}")
    lines.append(f"state: {meta.state}")
    lines.append(f"source: {_yaml_str(_source_url(meta, config))}")

    if not is_pr:
        state_reason = entry.get("state_reason")
        if state_reason:
            lines.append(f"state_reason: {state_reason}")

    author = (entry.get("user") or {}).get("login", "")
    lines.append(f"author: {_yaml_str(author)}")

    assoc = entry.get("author_association")
    lines.append(f"author_association: {(assoc or 'NONE').lower()}")

    lines.append(f"created_at: {_yaml_str(entry.get('created_at', ''))}")
    if entry.get("updated_at"):
        lines.append(f"updated_at: {_yaml_str(entry['updated_at'])}")
    if entry.get("closed_at"):
        lines.append(f"closed_at: {_yaml_str(entry['closed_at'])}")

    labels = [label["name"] for label in (entry.get("labels") or [])]
    if labels:
        lines.append("labels:")
        for label in labels:
            lines.append(f"  - {_yaml_str(label)}")
    else:
        lines.append("labels: []")

    milestone = entry.get("milestone")
    if milestone and milestone.get("title"):
        lines.append(f"milestone: {_yaml_str(milestone['title'])}")

    if is_pr:
        lines.extend(_pr_front_matter_fields(entry))

    if linked_entries:
        lines.append("linked:")
        for le in linked_entries:
            lines.append(f"  - number: {le.number}")
            lines.append(f"    title: {_yaml_str(le.title)}")
    else:
        lines.append("linked: []")

    participants = _collect_participants(entry, data.get("events") or [])
    if participants:
        lines.append("participants:")
        for p in participants:
            lines.append(f"  - {_yaml_str(p)}")
    else:
        lines.append("participants: []")

    lines.append("---")
    return "\n".join(lines)


def _source_url(meta: EntryMeta, config: Config) -> str:
    kind = "pull" if meta.is_pr else "issues"
    return f"https://github.com/{config.owner}/{config.repository}/{kind}/{meta.number}"


def _collect_participants(
    entry: dict[str, Any],
    events: list[dict[str, Any]],
) -> list[str]:
    """Return unique substantive participants in appearance order.

    Includes the original author and anyone who left a comment, review, or
    code-review comment. Excludes purely actor-driven events (labeled, closed,
    etc.) -- "participant" here means "left content," not "took an action."
    """
    seen: dict[str, None] = {}

    author = (entry.get("user") or {}).get("login")
    if author:
        seen[author] = None

    for ev in events:
        kind = ev.get("event", "")
        if kind == "commented":
            login = _actor_login(ev)
            if login != "unknown":
                seen.setdefault(login, None)
        elif kind == "reviewed":
            if (ev.get("body") or "").strip():
                login = _actor_login(ev)
                if login != "unknown":
                    seen.setdefault(login, None)
        elif kind == "code_review":
            for c in ev.get("data") or []:
                login = (c.get("user") or {}).get("login")
                if login:
                    seen.setdefault(login, None)

    return list(seen.keys())


def _pr_front_matter_fields(pull: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    merged_at = pull.get("merged_at")
    if merged_at:
        lines.append(f"merged_at: {_yaml_str(merged_at)}")

    base = (pull.get("base") or {}).get("label")
    if base:
        lines.append(f"base: {_yaml_str(base)}")
    head = (pull.get("head") or {}).get("label")
    if head:
        lines.append(f"head: {_yaml_str(head)}")

    for key in ("commits", "changed_files", "additions", "deletions"):
        if pull.get(key) is not None:
            lines.append(f"{key}: {pull[key]}")

    lines.append(f"draft: {'true' if pull.get('draft') else 'false'}")

    reviewers = [
        r.get("login", "")
        for r in (pull.get("requested_reviewers") or [])
        if r.get("login")
    ]
    if reviewers:
        lines.append("requested_reviewers:")
        for r in reviewers:
            lines.append(f"  - {_yaml_str(r)}")

    return lines


def _render_event(event: dict[str, Any]) -> str:
    ev = event.get("event", "")
    if ev in SILENT_EVENTS:
        return ""

    if ev == "commented":
        return _render_comment(event)
    if ev == "code_review":
        return _render_code_review(event)
    if ev == "reviewed":
        return _render_reviewed(event)

    name = _actor_login(event)
    when = event.get("created_at") or event.get("submitted_at") or ""

    if ev == "committed":
        sha10 = (event.get("sha") or "")[:10]
        msg = (event.get("message") or "").split("\n", 1)[0]
        author_name = (event.get("author") or {}).get("name")
        who = f"{author_name} " if author_name else ""
        return _italic(f"{who}committed {sha10}: {msg}")

    if ev == "closed":
        return _italic(f"@{name} closed this -- {when}")
    if ev == "reopened":
        return _italic(f"@{name} reopened this -- {when}")
    if ev == "merged":
        return _italic(f"@{name} merged this -- {when}")

    if ev == "labeled":
        label_name = (event.get("label") or {}).get("name", "?")
        return _italic(f"@{name} added label `{label_name}` -- {when}")
    if ev == "unlabeled":
        label_name = (event.get("label") or {}).get("name", "?")
        return _italic(f"@{name} removed label `{label_name}` -- {when}")

    if ev == "assigned":
        assignee = (event.get("assignee") or {}).get("login", "?")
        return _italic(f"@{name} assigned @{assignee} -- {when}")
    if ev == "unassigned":
        assignee = (event.get("assignee") or {}).get("login", "?")
        return _italic(f"@{name} unassigned @{assignee} -- {when}")

    if ev == "milestoned":
        title = (event.get("milestone") or {}).get("title", "?")
        return _italic(f"@{name} added to milestone `{title}` -- {when}")
    if ev == "demilestoned":
        title = (event.get("milestone") or {}).get("title", "?")
        return _italic(f"@{name} removed from milestone `{title}` -- {when}")

    if ev == "renamed":
        rename = event.get("rename") or {}
        old = rename.get("from", "?")
        new = rename.get("to", "?")
        return _italic(f'@{name} renamed: "{old}" -> "{new}" -- {when}')

    if ev == "head_ref_force_pushed":
        sha10 = (event.get("commit_id") or "")[:10]
        target = f" to {sha10}" if sha10 else ""
        return _italic(f"@{name} force-pushed{target} -- {when}")
    if ev == "base_ref_force_pushed":
        sha10 = (event.get("commit_id") or "")[:10]
        target = f" to {sha10}" if sha10 else ""
        return _italic(f"@{name} force-pushed the base branch{target} -- {when}")
    if ev == "base_ref_changed":
        return _italic(f"@{name} changed the base branch -- {when}")

    if ev == "convert_to_draft":
        return _italic(f"@{name} marked this as draft -- {when}")
    if ev == "ready_for_review":
        return _italic(f"@{name} marked this as ready for review -- {when}")

    if ev == "review_requested":
        requester = (event.get("review_requester") or {}).get("login", "?")
        reviewer = (event.get("requested_reviewer") or {}).get("login", "?")
        return _italic(f"@{requester} requested review from @{reviewer} -- {when}")
    if ev == "review_request_removed":
        requester = (event.get("review_requester") or {}).get("login", "?")
        reviewer = (event.get("requested_reviewer") or {}).get("login", "?")
        return _italic(f"@{requester} removed review request from @{reviewer} -- {when}")

    if ev == "head_ref_deleted":
        return _italic(f"@{name} deleted the branch -- {when}")
    if ev == "head_ref_restored":
        return _italic(f"@{name} restored the branch -- {when}")
    if ev == "comment_deleted":
        return _italic(f"@{name} deleted a comment -- {when}")

    if ev == "marked_as_duplicate":
        return _italic(f"@{name} marked this as duplicate -- {when}")
    if ev == "pinned":
        return _italic(f"@{name} pinned this -- {when}")
    if ev == "unpinned":
        return _italic(f"@{name} unpinned this -- {when}")
    if ev == "locked":
        return _italic(f"@{name} locked this -- {when}")
    if ev == "unlocked":
        return _italic(f"@{name} unlocked this -- {when}")
    if ev == "user_blocked":
        return _italic(f"@{name} blocked a user -- {when}")

    if ev == "referenced":
        sha10 = (event.get("commit_id") or "")[:10]
        url = _api_commit_url_to_web(event.get("commit_url") or "")
        tail = f" ({url})" if url else ""
        return _italic(f"@{name} referenced this in commit {sha10}{tail} -- {when}")

    if ev == "cross-referenced":
        source_issue = (event.get("source") or {}).get("issue") or {}
        src_num = source_issue.get("number", "?")
        src_title = source_issue.get("title", "?")
        src_user = (source_issue.get("user") or {}).get("login", "?")
        return _italic(
            f"@{name} cross-referenced this from #{src_num} "
            f"({src_title}) by @{src_user} -- {when}"
        )

    if ev == "added_to_project":
        col = (event.get("project_card") or {}).get("column_name", "?")
        return _italic(f'@{name} added this to the "{col}" column in a project -- {when}')
    if ev == "removed_from_project":
        col = (event.get("project_card") or {}).get("column_name", "?")
        return _italic(f'@{name} removed this from the "{col}" column in a project -- {when}')
    if ev == "moved_columns_in_project":
        pc = event.get("project_card") or {}
        prev = pc.get("previous_column_name", "?")
        curr = pc.get("column_name", "?")
        return _italic(
            f'@{name} moved this from the "{prev}" to the "{curr}" '
            f"column in a project -- {when}"
        )

    if ev == "added_to_project_v2":
        return _italic(f"@{name} added this to a project -- {when}")
    if ev == "removed_from_project_v2":
        return _italic(f"@{name} removed this from a project -- {when}")
    if ev == "project_v2_item_status_changed":
        return _italic(f"@{name} changed the project status -- {when}")

    return _italic(f"[unknown event: {ev}] @{name} -- {when}")


def _render_comment(event: dict[str, Any]) -> str:
    body = event.get("body") or ""
    if not body.strip():
        return ""
    login = _actor_login(event)
    when = event.get("created_at", "")
    header = f"### Comment -- @{login} -- {when}"
    return f"{header}\n\n{body.rstrip()}\n"


def _render_code_review(event: dict[str, Any]) -> str:
    comments = event.get("data") or []
    if not comments:
        return ""

    first = comments[0]
    path = first.get("path", "?")
    line = first.get("line") or first.get("original_line") or "?"
    when = first.get("created_at", "")
    diff_hunk = first.get("diff_hunk", "")

    out: list[str] = []
    out.append(f"### Code review on `{path}:{line}` -- {when}")
    out.append("")
    out.append("```diff")
    out.append(_trim_diff_hunk(diff_hunk, DIFF_HUNK_TAIL_LINES))
    out.append("```")
    out.append("")

    for c in comments:
        login = (c.get("user") or {}).get("login", "unknown")
        cwhen = c.get("created_at", "")
        cbody = (c.get("body") or "").rstrip()
        out.append(f"#### Review comment -- @{login} -- {cwhen}")
        out.append("")
        if cbody:
            out.append(cbody)
            out.append("")

    return "\n".join(out)


def _render_reviewed(event: dict[str, Any]) -> str:
    state = (event.get("state") or "").lower()
    login = _actor_login(event)
    when = event.get("submitted_at") or event.get("created_at") or ""
    body = (event.get("body") or "").strip()
    has_state = state and state != "commented"

    if body:
        suffix = f" ({state})" if has_state else ""
        return f"### Review -- @{login}{suffix} -- {when}\n\n{body.rstrip()}\n"

    if has_state:
        return _italic(f"@{login} {state} -- {when}")

    return ""


def _api_commit_url_to_web(api_url: str) -> str:
    """Convert an api.github.com /repos/<o>/<r>/commits/<sha> URL to its web form."""
    if not api_url:
        return ""
    return api_url.replace("api.", "").replace("/repos", "").replace("/commits/", "/commit/")


def _trim_diff_hunk(hunk: str, tail_lines: int) -> str:
    """Keep the @@ header line and the last `tail_lines` lines of the hunk.

    GitHub's `diff_hunk` runs from the hunk header down to the commented line,
    so the commented line is at the tail. For large hunks we elide the middle
    and emit a marker, keeping the document compact for LLM consumption.
    """
    if not hunk:
        return hunk

    lines = hunk.split("\n")
    if len(lines) <= tail_lines + 1:
        return hunk

    has_header = lines[0].startswith("@@")
    body = lines[1:] if has_header else lines

    if len(body) <= tail_lines:
        return hunk

    elided = len(body) - tail_lines
    tail = body[-tail_lines:]
    result: list[str] = []
    if has_header:
        result.append(lines[0])
    result.append(f"... ({elided} earlier lines elided) ...")
    result.extend(tail)
    return "\n".join(result)


def _actor_login(event: dict[str, Any]) -> str:
    actor = event.get("actor")
    if actor and actor.get("login"):
        return actor["login"]
    user = event.get("user")
    if user and user.get("login"):
        return user["login"]
    return "unknown"


def _italic(text: str) -> str:
    return f"*{text}*\n"


def _yaml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)
