"""resolve_additive.py FILE...: resolve diff3 conflicts where both sides only added text, or one side extends the base.
Exits 1, leaving a file untouched, if any of its conflicts is anything else."""
import re, sys
pat = re.compile(r"<<<<<<< [^\n]*\n(.*?)\|\|\|\|\|\|\| [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n", re.S)
bad = False
for p in sys.argv[1:]:
    t = open(p).read()
    problems = []
    def res(m):
        head, base, theirs = m.groups()
        if base == "":
            if p.endswith(".py") and head.lstrip().startswith(("def ", "class ", "@")) and theirs.lstrip().startswith(("def ", "class ", "@")):
                return head.rstrip("\n") + "\n\n\n" + theirs
            return head + theirs
        if theirs.startswith(base):
            return head + theirs[len(base):]
        if head.startswith(base):
            return theirs + head[len(base):]
        if head.endswith(base):  # head added lines before a block theirs rewrote
            return head[: len(head) - len(base)] + theirs
        if theirs.endswith(base):
            return theirs[: len(theirs) - len(base)] + head
        problems.append(m.group(0)[:200]); return m.group(0)
    new, n = pat.subn(res, t)
    if problems or "<<<<<<<" in new:
        bad = True; print(f"{p}: {len(problems)} unresolved"); [print("  ", x.replace("\n", " | ")) for x in problems]
    else:
        open(p, "w").write(new); print(f"{p}: resolved {n}")
sys.exit(1 if bad else 0)
