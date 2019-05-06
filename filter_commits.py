import collections


def get_login(commit):
    if commit.author:
        return commit.author.login
    if commit.committer:
        return commit.committer.login
    source = commit.commit.author
    return f"{source['name']} <{source['email']}>"
    return commit.commit.author['name']


def except_merges(commits):
    users = collections.defaultdict(list)
    for commit in commits:
        if len(commit.parents) > 1:
            # Merge commit
            continue
        users[get_login(commit)].append(commit)
    return users


def summarize(users):
    summary = []
    for name, commits in users.items():
        summary.append((name, len(commits)))
    return sorted(summary, key=lambda x : x[1], reverse=True)
