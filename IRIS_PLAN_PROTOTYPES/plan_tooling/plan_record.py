"""plan_record.py KEY PR SHA: drop a merged item from IRIS_GLUE_GAP_PLAN.md and set 'Main is at SHA (#PR).' (no commit).

Current state keeps no per-PR line: the PR and git history are the record.
"""
import re, sys
key, pr, sha = sys.argv[1:4]
P = "/Users/nabil/Git/glue-solar/IRIS_GLUE_GAP_PLAN.md"
s = open(P).read()
s, n = re.subn(rf"^- \[ \] \*\*\w+\*\* `{re.escape(key)}`[^\n]*\n(?:  [^\n]*\n)*", "", s, flags=re.M)  # with its sub-bullets
assert n == 1, f"item {key} not found once ({n})"
# checklist: drop the key, then any WP line left empty
def drop(m):
    return m.group(0).replace(f"`{key}`, ", "").replace(f", `{key}`", "")
s = re.sub(r"^- WP\d+: [^\n]*", drop, s, flags=re.M)
s = re.sub(rf"^- WP\d+: `{re.escape(key)}`\n", "", s, flags=re.M)
# Depends lists
def dep(m):
    keys = [k.strip() for k in m.group(1).split(",") if k.strip() != key]
    return f" Depends: {', '.join(keys)}." if keys else ""
s = re.sub(r" Depends: ([^.\n]+)\.", dep, s)
# remaining prose mentions point at the PR
s = s.replace(f"`{key}`", f"#{pr}")
# empty milestone headings, in work packages and in the checklist
s = re.sub(r"\n\n\n+", "\n\n", s)
s = re.sub(r"\*\*(M\d|L|OM|Later|Other missions)\*\*\n\n(?=\*\*(M\d|L|OM|Later|Other missions)\*\*|### |## |Notes:)", "", s)
s, n = re.subn(r"Main is at \w+ \(#\d+\)\.", f"Main is at {sha} (#{pr}).", s, count=1)
assert n == 1, "no 'Main is at <sha> (#N).' in Current state"
open(P, "w").write(s)
items = set(re.findall(r"^- \[ \] \*\*\w+\*\* `([\w-]+)`", s, re.M))
deps = {k.strip() for d in re.findall(r"Depends: ([^.\n]+)", s) for k in d.split(",")}
mentioned = set(re.findall(r"`((?:wp\d+)-[\w-]+)`", s))
print("dangling:", sorted((deps | mentioned) - items))
