"""Data processing: read backup JSON, extract metadata, build timelines.

Ported from the original generate-data.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mirror.models import EntryMeta

KEYS_TO_REMOVE = frozenset([
    "diff_url", "node_id", "issue_url", "comments_url", "commits_url",
    "patch_url", "statuses_url", "review_comment_url", "review_comments_url",
    "repo", "_links", "url", "gravatar_id", "gists_url", "received_events_url",
    "repos_url", "events_url", "subscriptions_url", "organizations_url",
    "html_url", "followers_url", "following_url", "starred_url",
    "pull_request_url", "site_admin",
])


def drop_private_events(data: dict[str, Any]) -> dict[str, Any]:
    """Remove timeline events that GitHub shows only to some users, modifying data in place.

    A backup made with a user's token gets events that are not public:
    - that user's own unsubmitted reviews ("reviewed", state PENDING, submitted_at null);
    - "referenced" events from commits in private repos the user can access. If the
      token itself cannot read that repo, commit_id and commit_url are null.
    Neither is shown to the public on GitHub, and neither has the data the renderers
    expect, so both are dropped before anything reads the events.

    This is a backstop, not a privacy boundary. It can only catch leaks where GitHub
    itself withheld the payload from the backup token, which is what leaves the nulls
    to key on. Token scope does not keep these events out of a backup: they are listed
    for any token whose *account* can read the private repository, and restricting the
    token to public repositories nulls the payload rather than hiding the event. A
    token whose account can read that repository instead receives fully populated
    events, indistinguishable from public ones, which are still published: a
    "referenced" event then carries the private commit's sha and url, and a
    "cross-referenced" event from a private repository carries that issue's number,
    title and author. The reliable control is to back up with an account that cannot
    see the private repositories at all.
    """
    events = data.get("events")
    if events:
        data["events"] = [e for e in events if not _is_private_event(e)]
    return data


def _is_private_event(e: dict[str, Any]) -> bool:
    if e.get("event") == "reviewed" and e.get("state") == "PENDING":
        return True
    return e.get("event") == "referenced" and e.get("commit_id") is None


def remove_nested_keys(obj: Any) -> Any:
    """Remove unneeded API keys to reduce size, modifying obj in place."""
    if isinstance(obj, dict):
        for key in list(obj.keys()):
            if key in KEYS_TO_REMOVE:
                del obj[key]
            else:
                remove_nested_keys(obj[key])
    elif isinstance(obj, list):
        for v in obj:
            remove_nested_keys(v)
    return obj


def determine_issue_state(issue: dict[str, Any]) -> str:
    """Determine issue state: open, closed, or complete."""
    if issue["state"] == "closed":
        if issue.get("state_reason") == "completed":
            return "complete"
        return "closed"
    return "open"


def determine_pull_state(pull: dict[str, Any]) -> str:
    """Determine PR state: open, closed, merged, or draft."""
    if pull.get("merged_at") is not None:
        return "merged"
    if pull.get("closed_at") is not None:
        return "closed"
    if pull.get("draft", False):
        return "draft"
    return "open"


def extract_issue_meta(data: dict[str, Any], json_path: Path) -> EntryMeta:
    """Extract lightweight metadata from a raw issue JSON structure."""
    issue = data["issue"]
    return EntryMeta(
        number=issue["number"],
        title=issue["title"],
        state=determine_issue_state(issue),
        is_pr=False,
        contributor=issue["user"]["login"],
        avatar_url=issue["user"]["avatar_url"],
        labels=[label["name"] for label in issue.get("labels", [])],
        date=issue["created_at"],
        json_path=json_path,
    )


def extract_pull_meta(data: dict[str, Any], json_path: Path) -> EntryMeta:
    """Extract lightweight metadata from a raw pull request JSON structure."""
    pull = data["pull"]
    return EntryMeta(
        number=pull["number"],
        title=pull["title"],
        state=determine_pull_state(pull),
        is_pr=True,
        contributor=pull["user"]["login"],
        avatar_url=pull["user"]["avatar_url"],
        labels=[label["name"] for label in pull.get("labels", [])],
        date=pull["created_at"],
        json_path=json_path,
    )


def build_pull_timeline(data: dict[str, Any]) -> None:
    """Merge code review comments into the events timeline, modifying data in place.

    Groups review comments by diff_hunk, creates synthetic 'code_review' events,
    and inserts them chronologically into the events list.
    """
    if "comments" not in data:
        return

    hunk_to_comments: dict[str, list[dict[str, Any]]] = {}
    for review in data["comments"]:
        hunk = review["diff_hunk"]
        if hunk not in hunk_to_comments:
            hunk_to_comments[hunk] = []
        hunk_to_comments[hunk].append(review)

    code_review_events: list[dict[str, Any]] = []
    for comments in hunk_to_comments.values():
        code_review_events.append({
            "event": "code_review",
            "data": comments,
            "created_at": comments[0]["created_at"],
        })

    code_review_events.sort(key=lambda x: x["created_at"])

    events = data.get("events", [])
    i = 0
    while i < len(events) and code_review_events:
        date = _get_event_date(events[i])
        if date is not None and date > code_review_events[0]["created_at"]:
            events.insert(i, code_review_events.pop(0))
        i += 1

    # Append any remaining code review events at the end
    events.extend(code_review_events)

    del data["comments"]


def _get_event_date(entry: dict[str, Any]) -> str | None:
    """Get the date string for a timeline event."""
    if entry.get("created_at") is not None:
        return entry["created_at"]
    if entry.get("submitted_at") is not None:
        return entry["submitted_at"]
    return None
