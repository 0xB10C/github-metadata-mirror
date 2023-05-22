#! /usr/bin/env python
"""
A skeleton python script which reads from an input file,
writes to an output file and parses command line arguments
"""
import sys
import argparse
import json
import glob
import unicodedata
import re
from datetime import datetime

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

EVENT_COMMENT = "comment"
EVENT_REVIEW = "review"
EVENT_CLOSE = "close"

DEFAULT_COMMENT_BODY = "_No description provided._"

class User():
    def __init__(self):
        self.name = None
        self.avatar_url = None

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class Review():
    def __init__(self):
        self.type = EVENT_REVIEW
        self.hunk = None
        self.date = None
        self.path = None
        self.position = None
        self.commit = None
        self.original_position = None
        self.original_commit = None
        self.comments = list()

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class Reactions():
    def __init__(self):
        self.total = 0
        self.reactions = dict()

    def from_github_data(reactions):
        r = Reactions()
        r.total = reactions["total_count"]
        possible_reactions = ["+1", "-1", "eyes", "heart", "hooray", "laugh", "rocket"]
        for reaction in possible_reactions:
            if reactions[reaction] > 0:
                r.reactions[reaction] = reactions[reaction]
        return r

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class Comment():
    def __init__(self):
        self.id = None
        self.type = EVENT_COMMENT
        self.author = User()
        self.body = DEFAULT_COMMENT_BODY
        self.date = None
        self.date_updated = None
        self.author_association = None
        self.reactions = Reactions()

    def from_github_data(comment):
        c = Comment()
        c.id = comment["id"]
        c.body = comment["body"].replace("```suggestion\r\n", "```diff\r\n@ suggestion:\n")
        c.date = comment["created_at"]
        c.date_updated = comment["updated_at"]
        if "reactions" in comment:
            c.reactions = Reactions.from_github_data(comment["reactions"])
        if "author_association" in comment:
            c.author_association = comment["author_association"]
        if "user" in comment and comment["user"] != None:
            if "login" in comment["user"] and comment["user"]["login"] != None:
                c.author.name = comment["user"]["login"]
            if "avatar_url" in comment["user"] and comment["user"]["avatar_url"] != None:
                c.author.avatar_url = comment["user"]["avatar_url"]
        return c

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class Close():
    def __init__(self, user, date):
        self.type = EVENT_CLOSE
        self.user = user
        self.date = date

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class Milestone():
    def __init__(self):
        self.number = None
        self.title = None
        self.state = None

    def from_github_data(milestone):
        m = Milestone()
        m.number = milestone["number"]
        m.title = milestone["title"]
        m.state = milestone["state"]
        return m

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
        requested = list()
        merge_commit_sha = None
        base_label = None
        head_label = None
        review_comments = None

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class Entry():
    def __init__(self, number):
        self.number = number
        self.user = User()
        self.contributor = None # used in hugo as a category
        self.title = None
        self.date = None
        self.is_pr = None
        self.state = None
        self.state_reason = None
        self.labels = list()
        self.closed_at = None
        self.closed_by = None
        self.milestone = None
        self.milestone_info = None
        self.pr = PR()
        self.timeline = list()
        self.url = f"/{self.number}"

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


# https://stackoverflow.com/a/34482761/8896600
def progressbar(it, prefix="", size=60, out=sys.stdout): # Python3.6+
    count = len(it)
    def show(j):
        x = int(size*j/count)
        print(f"{prefix}[{u'█'*x}{('.'*(size-x))}] {j}/{count}", end='\r', file=out, flush=True)
    show(0)
    for i, item in enumerate(it):
        yield item
        show(i+1)
    print("\n", flush=True, file=out)


def remove_control_characters(s):
    return "".join(ch for ch in s if ch == "\n" or unicodedata.category(ch)[0] != "C").strip()

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

    files = glob.glob("data/bitcoin-gh-meta/issues/20*/*.json")

    issues = dict()

    states = set()
    state_reasons = set()

    for file_path in progressbar(sorted(files), "Reading files: "):
        with open(file_path, "r") as f:
            file = json.load(f)
            file_name = file_path.split("/")[-1]
            number = file_name.split("-")[0].split(".")[0]
            if number not in issues:
                issues[number] = dict()
            if "-comments.json" in file_path:
                issues[number]["comments"] = file
            elif "-PR.json" in file_path:
                issues[number]["pr"] = file
            else:
                issues[number]["main"] = file

    for number, issue in progressbar(issues.items(), "Processing: "):
        e = Entry(number)
        e.is_pr = "pr" in issue
        op = Comment()
        # mapping from diff_hunk to code reviews with multiple comments
        code_reviews = dict()

        if "main" in issue:
            e.title = remove_control_characters(escape(issue["main"]["title"]))
            e.date = issue["main"]["created_at"]
            if "body" in issue["main"] and issue["main"]["body"] != None:
                op.body = remove_control_characters(escape(issue["main"]["body"]))
            e.user.name = issue["main"]["user"]["login"]
            e.contributor = issue["main"]["user"]["login"]
            e.user.avatar_url = issue["main"]["user"]["avatar_url"]
            e.state = issue["main"]["state"]
            if issue["main"]["milestone"] != None:
                e.milestone = Milestone.from_github_data(issue["main"]["milestone"])
            if e.state == "closed":
                e.closed_at = issue["main"]["closed_at"]
                e.closed_by = User()
                if issue["main"]["closed_by"] != None:
                    e.closed_by.name = issue["main"]["closed_by"]["login"]
                    e.closed_by.avatar_url = issue["main"]["closed_by"]["avatar_url"]

            states.add(e.state)
            if "state_reason" in issue["main"]:
                state_reason = issue["main"]["state_reason"]
                if state_reason == "completed":
                    e.state == state_reason
                if state_reason == "reopened":
                    e.state == "open"
                state_reasons.add(state_reason)
            for label in issue["main"]["labels"]:
                e.labels.append(label["name"])
        else:
            print(f"No 'main' for {number}. Skipping..")
            continue

        op.author = e.user
        op.date = e.date
        op.id = issue["main"]["id"]
        if "author_association" in issue["main"]:
            op.author_association = issue["main"]["author_association"]
        if "reactions" in issue["main"]:
            op.reactions = Reactions.from_github_data(issue["main"]["reactions"])
        e.timeline.append(op)

        if e.is_pr:
            e.pr.additions = issue["pr"]["additions"]
            e.pr.deletions = issue["pr"]["deletions"]
            e.pr.changed_files = issue["pr"]["changed_files"]
            e.pr.commits = issue["pr"]["commits"]
            e.pr.merge_commit_sha = issue["pr"]["merge_commit_sha"]
            e.pr.requested = list()
            if "requested_reviewers" in issue["pr"]:
                for reviewer in issue["pr"]["requested_reviewers"]:
                    u = User()
                    u.name = reviewer["login"]
                    u.avatar_url = reviewer["avatar_url"]
                    e.pr.requested.append(u)
            if issue["pr"]["milestone"] != None:
                e.milestone_info = Milestone.from_github_data(issue["pr"]["milestone"])
                e.milestone = e.milestone_info.title
            if "draft" in issue["pr"]:
                e.pr.draft = issue["pr"]["draft"]
                if e.pr.draft:
                    e.state = "draft"
            else:
                e.pr.draft = False
            e.pr.merged = issue["pr"]["merged"]
            if e.pr.merged:
                e.state = "merged"
            e.pr.merged_by = issue["pr"]["merged_by"]
            e.pr.merged_at = issue["pr"]["merged_at"]
            e.pr.base_label = issue["pr"]["base"]["label"]
            e.pr.head_label = issue["pr"]["head"]["label"]

        if "comments" in issue:
            for comment in issue["comments"]:
                # There can be normal commments or code review comments related
                # to a specific code hunk. We tread them differently.
                if "diff_hunk" in comment:
                    diff_hunk = comment["diff_hunk"]
                    if diff_hunk not in code_reviews:
                        r = Review()
                        r.path = comment["path"]
                        r.position = comment["position"]
                        r.commit = comment["commit_id"]
                        r.original_position = comment["original_position"]
                        r.original_commit = comment["original_commit_id"]
                        r.date = comment["created_at"]
                        r.hunk = comment["diff_hunk"]
                        code_reviews[diff_hunk] = r
                    c = Comment.from_github_data(comment)
                    code_reviews[diff_hunk].comments.append(c)
                else:
                    c = Comment.from_github_data(comment)
                    e.timeline.append(c)

        # add close event to timeline (if closed)
        if e.state == "closed":
            e.timeline.append(Close(e.closed_by, e.closed_at))
        # adding code reviews to timeline
        for (hunk, review) in code_reviews.items():
            e.timeline.append(review)

        # sorting timeline
        e.timeline.sort(key=lambda event: datetime.strptime(event.date, DATE_FORMAT))

        with open(f"content/entries/{number}.md", "w") as f:
            f.write(
f"""{e.toJSON()}

{{{{< issue >}}}}

""")
            f.close()
    print("state:", states)
    print("state reasons:", state_reasons)

if __name__ == "__main__":
    main()
