#! /usr/bin/env python
"""
A skeleton python script which reads from an input file,
writes to an output file and parses command line arguments
"""
from __future__ import print_function
import sys
import argparse
import json
import glob
import unicodedata

class Author():
    def __init__(self):
        self.name = None
        self.avatar_url = None

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class Comment():
    def __init__(self):
        self.id = None
        self.author = Author()
        self.body = None

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class PR():
    def __init__(self):
        additions = None
        deletions = None
        changed_files = None
        commits = None
        comments = None
        draft = None
        merged = None
        merged_by = None
        merged_at = None
        base_label = None
        head_label = None
        review_comments = None

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class Entry():
    def __init__(self):
        self.number = None
        self.author = Author()
        self.title = None
        self.date = None
        self.is_pr = None
        self.state = None
        self.state_reason = None
        self.labels = list()
        self.pr = PR()

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

def remove_control_characters(s):
    return "".join(ch for ch in s if ch == "\n" or unicodedata.category(ch)[0] != "C")

def escape(s):
    return s.replace("\\", "\\\\").replace("\"", "\\\"")

def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "input", nargs="?", default="-",
        metavar="INPUT_FILE", type=argparse.FileType("r"),
        help="path to the input file (read from stdin if omitted)")

    parser.add_argument(
        "output", nargs="?", default="-",
        metavar="OUTPUT_FILE", type=argparse.FileType("w"),
        help="path to the output file (write to stdout if omitted)")

    args = parser.parse_args()

    files = glob.glob("data/bitcoin-gh-meta/issues/260xx/*.json")

    issues = dict()

    states = set()
    state_reasons = set()

    for file_path in sorted(files):
        with open(file_path, "r") as f:
            file = json.load(f)
            file_name = file_path.split("/")[-1]
            number = file_name.split("-")[0].split(".")[0]
            print(f"reading #{number}")
            if number not in issues:
                issues[number] = dict()
            if "-comments.json" in file_path:
                issues[number]["comments"] = file
            elif "-PR.json" in file_path:
                issues[number]["pr"] = file
            else:
                issues[number]["main"] = file

    for number, issue in issues.items():
        e = Entry()
        e.is_pr = "pr" in issue
        e.number = number

        if "main" in issue:
            e.title = remove_control_characters(escape(issue["main"]["title"]))
            e.date = issue["main"]["created_at"]
            if "body" in issue["main"] and issue["main"]["body"] != None:
                e.body = remove_control_characters(escape(issue["main"]["body"]))
            e.author.name = issue["main"]["user"]["login"]
            e.author.avatar_url = issue["main"]["user"]["avatar_url"]
            e.state = issue["main"]["state"]
            states.add(e.state)
            if "state_reason" in issue["main"]:
                e.state_reason = issue["main"]["state_reason"]
                state_reasons.add(e.state_reason)
            for label in issue["main"]["labels"]:
                e.labels.append(label["name"])
            print(number, json.dumps(issue["main"], indent=4))

        if e.is_pr:
            e.pr.additions = issue["pr"]["additions"]
            e.pr.deletions = issue["pr"]["deletions"]
            e.pr.changed_files = issue["pr"]["changed_files"]
            e.pr.commits = issue["pr"]["commits"]
            e.pr.comments = issue["pr"]["comments"]
            e.pr.review_comments = issue["pr"]["review_comments"]
            e.pr.draft = issue["pr"]["draft"]
            e.pr.merged = issue["pr"]["merged"]
            e.pr.merged_by = issue["pr"]["merged_by"]
            e.pr.merged_at = issue["pr"]["merged_at"]
            e.pr.base_label = issue["pr"]["base"]["label"]
            e.pr.head_label = issue["pr"]["head"]["label"]

        comments = ""
        if "comments" in issue:
            comments = "\n".join([format_comment(c) for c in issue["comments"]])

        with open(f"content/{number}.md", "w") as f:
            f.write(
f"""{e.toJSON()}

{{{{< bootstrap-container >}}}}

{{{{< issue-head >}}}}

{{{{< comment author="{e.author.name}" date="{e.date}" avatar_url="{e.author.avatar_url}">}}}}
{e.body}
{{{{</ comment >}}}}

{comments}

{{{{</ bootstrap-container >}}}}

""")
            f.close()
    print("state:", states)
    print("state reasons:", state_reasons)

def format_comment(comment):
    body = remove_control_characters(comment["body"])
    author = "unknown"
    avatar_url = ""
    if "user" in comment and comment["user"] != None:
        if "login" in comment["user"] and comment["user"]["login"] != None:
            author = comment["user"]["login"]
        if "avatar_url" in comment["user"] and comment["user"]["avatar_url"] != None:
            avatar_url = comment["user"]["avatar_url"]
    date = comment["created_at"]

    return f"""
{{{{< comment-line >}}}}
{{{{< comment author="{author}" date="{date}" avatar_url="{avatar_url}" withLine="yes">}}}}
{body}
{{{{</ comment >}}}}
    """

if __name__ == "__main__":
    main()
