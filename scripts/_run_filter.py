"""Run shared filter on all crawled authors and report breakdown."""
import logging
from collections import Counter

from findit.ai.filter_rules import SharedFilter
from findit.config import settings
from findit.db import Database

logging.basicConfig(level=logging.WARNING, format="%(message)s")

db = Database(settings.db_path)
flt = SharedFilter()

# Reset all filter flags so we re-evaluate from scratch
with db._conn() as c:
    c.execute("UPDATE authors SET is_filtered_out=0, filter_reason=NULL")

batch = 0
reasons: Counter[str] = Counter()
kept = 0
total = 0
while True:
    authors = db.get_unfiltered_authors(limit=500)
    if not authors:
        break
    batch += 1
    for a in authors:
        total += 1
        posts = db.get_author_posts(a["id"])
        keep, reason = flt.evaluate(a, posts=posts)
        if keep:
            db.update_author_scores(a["id"], is_real_person=0.5)
            kept += 1
        else:
            db.update_author_scores(a["id"], is_filtered_out=True, filter_reason=reason)
            reasons[reason or "unknown"] += 1

print(f"\n=== filter run on {total} authors ===")
print(f"  kept   : {kept} ({kept*100//total}%)")
print(f"  dropped: {sum(reasons.values())} ({sum(reasons.values())*100//total}%)")
print()
print("=== drop reasons (top) ===")
for reason, n in reasons.most_common():
    print(f"  {n:>4}  {reason}")
