#! /usr/bin/env python
"""
A python script that transforms GitHub REST API JSON exports of issues and
pull-requestes to hugo markdown files with the JSON data as hugo frontmatter.
"""
import sys
import argparse
import json
import glob
import unicodedata
import re
from datetime import datetime

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DEFAULT_COMMENT_BODY = "_No description provided._"
SUBSET_SIZE = 100

class Frontmatter():
    def __init__(self, title, number, date, author, avatar_url, labels, state, is_pr):
        self.title = title
        self.number = number
        self.date = date
        self.labels = labels
        self.state = state
        self.is_pr = is_pr
        self.contributor = author
        self.avatar_url = avatar_url
        self.url = f"/{number}"

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)

# https://stackoverflow.com/a/34482761/8896600
def progressbar(it, prefix="", size=60, out=sys.stdout):
    count = len(it)
    if count < 1:
        return
    def show(j):
        x = int(size*j/count)
        print(f"{prefix}[{u'█'*x}{('.'*(size-x))}] {j}/{count}", end='\r', file=out, flush=True)
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    print("\n", flush=True, file=out)

def read_file(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

def remove_nested_keys(obj):
    """ remove unneeded keys to reduce size and JSON de/serialization cost """
    keys_to_remove = [ "diff_url", "node_id", "issue_url", "comments_url", "commits_url", "patch_url", "statuses_url", "review_comment_url", "review_comments_url", "repo", "_links", "url", "gravatar_id", "gists_url", "received_events_url", "repos_url", "events_url", "subscriptions_url", "organizations_url", "gists_url", "html_url", "followers_url", "following_url", "starred_url", "pull_request_url", "site_admin" ]

    if isinstance(obj, dict):
        keys = list(obj.keys())
        for key in keys:
            if key in keys_to_remove:
                del obj[key]
            else:
                remove_nested_keys(obj[key])
    elif isinstance(obj, list):
        for v in obj:
            remove_nested_keys(v)
    return obj

def build_pull_timeline(data):
    hunk_to_comments = dict()
    for review in data["comments"]:
        hunk = review["diff_hunk"]
        if hunk not in hunk_to_comments:
            hunk_to_comments[hunk] = list()
        hunk_to_comments[hunk].append(review)

    # build code_review 'events'
    code_review_events = list()
    for hunk in hunk_to_comments.keys():
        code_review_events.append({
            "event": "code_review",
            "data": hunk_to_comments[hunk],
            "created_at": hunk_to_comments[hunk][0]["created_at"]
        })

    code_review_events.sort(key=lambda x: x["created_at"])

    def get_event_date(entry):
        if "created_at" in entry and entry["created_at"] is not None:
            return entry["created_at"]
        elif "submitted_at" in entry and entry["submitted_at"] is not None:
            return entry["submitted_at"]
        else:
            if entry["event"] != "committed" and entry["event"] != "line-commented":
                print("no date for:", entry)
            return None

    # interate existing events and insert code_review_events
    # at the right time in the timeline
    i = 0
    while i < len(data["events"]) and len(code_review_events) > 0:
        date = get_event_date(data["events"][i])
        if date is not None and date > code_review_events[0]["created_at"]:
            data["events"].insert(i, code_review_events.pop(0))
        i += 1

    del data["comments"]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to the github metadata backup directory.")
    parser.add_argument("output", help="Path to the hugo content directory were the markdown files should be written to.")
    parser.add_argument("ownerrepo", help="GitHub owner/repository. Used in the graph.json generation. Needs to be exaclty <owner>/<repository>.")
    parser.add_argument('-s', '--subset', action='store_true', help="Only process a small subset of the issues and pulls. Useful for testing purposes.")
    args = parser.parse_args()

    print(f"Reading GitHub metadata from {args.input} and writing to {args.output}")

    issue_files = glob.glob(f"{args.input}/issues/*.json")
    pull_files = glob.glob(f"{args.input}/pulls/*.json")

    if args.subset:
        print(f"Only processing a subset of the avaliable GitHub metadata for testing purposes")
        issue_files = issue_files[:min(len(issue_files), SUBSET_SIZE)]
        pull_files = pull_files[:min(len(pull_files), SUBSET_SIZE)]

    graph = dict()
    graph["nodes"] = list()
    graph["links"] = list()

    for issue_file in progressbar(issue_files, "issues"):
        issue = read_file(issue_file)
        frontmatter, data = process_issue(issue)
        graph["nodes"].append(frontmatter)
        if "events" in data:
            for event in data["events"]:
                if event["event"] == "cross-referenced":
                    if args.ownerrepo in event["source"]["issue"]["repository_url"]:
                        graph["links"].append({"source": frontmatter.number, "target": event["source"]["issue"]["number"]})
        write(frontmatter, data, args.output)
    
    for pull_file in progressbar(pull_files, "pulls"):
        pull = read_file(pull_file)
        frontmatter, data = process_pull(pull)
        graph["nodes"].append(frontmatter)
        if "events" in data:
            for event in data["events"]:
                if event["event"] == "cross-referenced":
                    if args.ownerrepo in event["source"]["issue"]["repository_url"]:
                        graph["links"].append({"source": frontmatter.number, "target": event["source"]["issue"]["number"]})
        write(frontmatter, data, args.output)

    # write graph
    write_graph(graph, args.output)

    
def process_issue(i):
    issue = i["issue"]
    state = "open"
    if issue["state"] == "closed":
        state = "closed"
        if issue["state_reason"] == "completed":
            state = "complete"

    cleaned_data = remove_nested_keys(i)

    front = Frontmatter(
        issue["title"],
        issue["number"],
        issue["created_at"],
        issue["user"]["login"],
        issue["user"]["avatar_url"],
        [ l["name"] for l in issue["labels"] ],
        state,
        False,
    )
    return front, cleaned_data


def process_pull(p):
    pull = p["pull"]
    state = "open"
    if "merged_at" in pull and pull["merged_at"] != None:
        state = "merged"
    elif "closed_at" in pull and pull["closed_at"] != None:
        state = "closed"
    elif pull["draft"]:
        state = "draft"

    cleaned_data = remove_nested_keys(p)
    build_pull_timeline(cleaned_data)

    front = Frontmatter(
        pull["title"],
        pull["number"],
        pull["created_at"],
        pull["user"]["login"],
        pull["user"]["avatar_url"],
        [ l["name"] for l in pull["labels"] ],
        state,
        True,
    )
    return front, cleaned_data

def write(front, data, output):
    with open(f"{output}/content/entries/{front.number}.md", "w") as f:
        f.write(f"""{front.toJSON()}\n{{{{< render >}}}}""")
        f.close()
    with open(f"{output}/data/{front.number}.json", "w") as f:
        json_data = json.dumps(data, default=lambda o: o.__dict__, sort_keys=True)
        f.write(json_data)
        f.close()

def write_graph(graph, output):
    graph_json = json.dumps(graph, default=lambda o: o.__dict__, sort_keys=True, indent=2)
    with open(f"{output}/static/graph.json", "w") as f:
        f.write(graph_json)
        f.close()

if __name__ == "__main__":
    main()
