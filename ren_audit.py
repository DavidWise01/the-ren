#!/usr/bin/env python3
"""
REN · THE NAME — the register auditor. Part 5/5 of THE VESSEL is in charge of the register.
Runs in the daily cascade: audits every UD0 sphere's register name, diffs against the last
baseline, and reports NEW / DROPPED / DRIFTED names + hex6 collisions + a self-check.

REAL: recomputes each sphere's REGISTER moniker with the same SHA-256 as the-ren page
(sha256(title | uniform register-seal | domain-origin)[:6]).  It is the register's own
naming, NOT each sphere's per-record birth-cert hex (see the-ren's honest layer).
Writes register.json (the new baseline) + register-audit.md (the report).
"""
import ast, hashlib, json, os, re, datetime

HERE   = os.path.dirname(os.path.abspath(__file__))
BUILD  = r"C:\Davids files\ud0\build.py"
BASE   = os.path.join(HERE, "register.json")          # persistent baseline
REPORT = os.path.join(HERE, "register-audit.md")
PAGE   = os.path.join(HERE, "index.html")             # for the seed baseline (the minted 1,153 snapshot)
REGSEAL = "Named in the register of UD0; the name is what keeps it."

def moniker_hex(title, dom):
    key = f"{title}|{REGSEAL}|UD0 · {dom}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:6]

def load_current():
    src = open(BUILD, encoding="utf-8").read()
    tree = ast.parse(src); G = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in ("DOMAIN_OF", "BANDS"):
                    try: G[t.id] = ast.literal_eval(node.value)
                    except Exception: pass
    DOMAIN_OF, BANDS = G["DOMAIN_OF"], G["BANDS"]
    seen, cur = set(), {}
    for band in BANDS:
        for s in band[2]:
            slug = s[0]
            if slug in seen: continue
            seen.add(slug)
            dom = DOMAIN_OF.get(slug, "?")
            cur[slug] = {"title": s[1], "dom": dom, "hex6": moniker_hex(s[1], dom)}
    return cur

def seed_baseline_from_page():
    """First run: baseline = the-ren's embedded SPH (the snapshot the register was minted from)."""
    try:
        html = open(PAGE, encoding="utf-8").read()
        m = re.search(r"var SPH=(\[\[.*?\]\]);", html, re.S)
        if not m: return None
        arr = json.loads(m.group(1))
        return {slug: {"title": title, "dom": dom, "hex6": moniker_hex(title, dom)}
                for slug, title, dom in arr}
    except Exception:
        return None

def main():
    cur = load_current()
    first = not os.path.exists(BASE)
    base = json.load(open(BASE, encoding="utf-8")) if not first else (seed_baseline_from_page() or {})

    cur_s, base_s = set(cur), set(base)
    new     = sorted(cur_s - base_s)
    dropped = sorted(base_s - cur_s)
    drifted = sorted(k for k in (cur_s & base_s) if cur[k]["hex6"] != base[k]["hex6"])

    # hex6 collision buckets (a 6-hex truncation is a fingerprint, not a key)
    buckets = {}
    for slug, r in cur.items():
        buckets.setdefault(r["hex6"], []).append(slug)
    collisions = {h: sorted(v) for h, v in buckets.items() if len(v) > 1}

    # orphans: a sphere with no domain route
    orphans = sorted(s for s, r in cur.items() if r["dom"] in ("?", None))

    ok = (len(orphans) == 0)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    def p(x=""): lines.append(x); print(x)
    p(f"REN · THE REGISTER AUDIT — {ts}")
    p("=" * 52)
    p(f"named in the register : {len(cur)} spheres")
    p(f"baseline compared to  : {'the minted page snapshot (first audit)' if first else 'last audit'} ({len(base)})")
    p(f"NEW since last        : {len(new)}")
    p(f"DROPPED since last    : {len(dropped)}")
    p(f"name-DRIFT (title/dom changed -> new hex) : {len(drifted)}")
    p(f"hex6 collisions       : {sum(len(v) for v in collisions.values())} spheres in {len(collisions)} buckets ({len(cur)-sum(len(v)-1 for v in collisions.values())} distinct names)")
    p(f"orphans (no domain)   : {len(orphans)}")
    p(f"self-check            : the-sealing-bench -> {moniker_hex('THE SEALING BENCH · SEA','aci')} (expect 067349) : {'OK' if moniker_hex('THE SEALING BENCH · SEA','aci')=='067349' else 'FAIL'}")
    p(f"VERDICT               : {'REGISTER SOUND' if ok else 'ATTENTION — orphans present'}")
    if new:     p("\nNEW names:   " + ", ".join(new[:40]) + (" …" if len(new) > 40 else ""))
    if dropped: p("DROPPED:     " + ", ".join(dropped[:40]) + (" …" if len(dropped) > 40 else ""))
    if drifted: p("DRIFTED:     " + ", ".join(drifted[:40]) + (" …" if len(drifted) > 40 else ""))
    if collisions:
        p("\ncollision buckets (hex6 -> slugs):")
        for h, v in sorted(collisions.items()):
            p(f"  {h}: " + ", ".join(v))

    # write the report + the new baseline
    md = [f"# REN · THE REGISTER AUDIT", "", f"_last run: {ts} · the-ren is in charge of the register in the daily cascade_", ""]
    md += ["| metric | value |", "|---|---|",
           f"| named in the register | **{len(cur)}** spheres |",
           f"| new since last audit | {len(new)} |",
           f"| dropped since last audit | {len(dropped)} |",
           f"| name-drift (hex changed) | {len(drifted)} |",
           f"| hex6 collisions | {sum(len(v) for v in collisions.values())} spheres / {len(collisions)} buckets |",
           f"| orphans (no domain) | {len(orphans)} |",
           f"| self-check (sealing-bench = 067349) | {'✓ OK' if moniker_hex('THE SEALING BENCH · SEA','aci')=='067349' else '✗ FAIL'} |",
           f"| verdict | **{'REGISTER SOUND' if ok else 'ATTENTION'}** |", ""]
    if new:     md += ["**New names:** " + ", ".join(f"`{x}`" for x in new), ""]
    if dropped: md += ["**Dropped:** " + ", ".join(f"`{x}`" for x in dropped), ""]
    if collisions:
        md += ["**Collision buckets** (a six-hex truncation is a fingerprint, not a key):", ""]
        md += [f"- `{h}` — " + ", ".join(f"`{s}`" for s in v) for h, v in sorted(collisions.items())]
    open(REPORT, "w", encoding="utf-8").write("\n".join(md) + "\n")
    json.dump(cur, open(BASE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    p(f"\nwrote {os.path.basename(BASE)} (new baseline) + {os.path.basename(REPORT)}")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
