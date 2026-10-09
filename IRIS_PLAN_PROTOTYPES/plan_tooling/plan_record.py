"""plan_record.py KEY PR SHA SUMMARY: record a merged item in IRIS_GLUE_GAP_PLAN.md (no commit)."""
import re, sys
key, pr, sha, summary = sys.argv[1:5]
P = "/Users/nabil/Git/glue-solar/IRIS_GLUE_GAP_PLAN.md"
s = open(P).read()
s, n = re.subn(rf"^- \[ \] \*\*\w+\*\* `{re.escape(key)}`[^\n]*\n", "", s, flags=re.M)
assert n == 1, f"item {key} not found once ({n})"
# checklist: drop the key, then any WP line left empty
s = re.sub(rf"`{re.escape(key)}`, ", "", s)
s = re.sub(rf", `{re.escape(key)}`", "", s)
s = re.sub(rf"^- WP\d+: `{re.escape(key)}`\n", "", s, flags=re.M)
# Depends lists
def dep(m):
    keys = [k.strip() for k in m.group(1).split(",") if k.strip() != key]
    return f" Depends: {', '.join(keys)}." if keys else ""
s = re.sub(r" Depends: ([^.\n]+)\.", dep, s)
# remaining prose mentions point at the PR
s = s.replace(f"`{key}`", f"#{pr}")
# empty milestone headings inside work packages, and milestone lines of the checklist with no WP left
s = re.sub(r"\n\n\n+", "\n\n", s)
s = re.sub(r"\*\*(M\d|L|OM)\*\*\n\n(?=\*\*(M\d|L|OM)\*\*|### |Notes:)", "", s)
# Current state
m = re.search(r"Main is at (\w+) \(", s)
s = s[:m.start()] + f"Main is at {sha} (#{pr} {summary}; " + s[m.end():]
s = re.sub(r"\(#107-#\d+;", f"(#107-#{pr};", s)
open(P, "w").write(s)
items = set(re.findall(r"^- \[ \] \*\*\w+\*\* `([\w-]+)`", s, re.M))
deps = {k.strip() for d in re.findall(r"Depends: ([^.\n]+)", s) for k in d.split(",")}
mentioned = set(re.findall(r"`((?:wp\d+)-[\w-]+)`", s))
print("dangling:", sorted((deps | mentioned) - items))
