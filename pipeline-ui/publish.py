"""Build a static site you can host anywhere, including Netlify and Vercel.

    python publish.py            # writes publish/
    python publish.py --out dist

What goes in: the finished report and the multi-page results website. Both are
already self-contained HTML with relative links, so they need no server at all.

What does NOT go in, and cannot: the studio itself. Running the pipeline needs
a process that stays alive for the length of an analysis and a disk it can
write to. Serverless hosts give you neither - a function is torn down in
seconds to minutes and its filesystem does not survive the request. So this
publishes the RESULTS. Runs stay on a machine you control.

Nothing here is generated or re-rendered: the files are copied byte for byte
from web/site/, which is what the pipeline actually produced.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "web" / "site"

LANDING = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DNA Methylation in Breast Cancer — Results</title>
<style>
:root{--ink:#0d0d0d;--muted:#6b6b6b;--line:#e4e4e4;--bg:#f6f6f6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  display:flex;min-height:100vh;align-items:center;justify-content:center;padding:32px}
.wrap{max-width:760px;width:100%}
.logo{display:grid;place-items:center;width:46px;height:46px;border-radius:12px;
  background:var(--ink);color:#fff;font-weight:800;letter-spacing:.5px;margin-bottom:20px}
h1{font-size:30px;letter-spacing:-.6px;margin:0 0 6px}
.lede{color:var(--muted);margin:0 0 4px;font-size:16px}
.facts{display:flex;gap:26px;flex-wrap:wrap;margin:22px 0 26px;padding:16px 0;
  border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.fact b{display:block;font-size:22px;font-variant-numeric:tabular-nums;letter-spacing:-.4px}
.fact span{color:var(--muted);font-size:12.5px}
a.card{display:block;text-decoration:none;color:inherit;background:#fff;
  border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:10px}
a.card:hover{border-color:var(--ink)}
a.card b{display:block;font-size:17px;margin-bottom:2px}
a.card span{color:var(--muted);font-size:13.5px}
.note{margin-top:22px;padding:14px 16px;background:#ececec;border-left:4px solid var(--muted);
  border-radius:8px;font-size:13px;color:#3f3f3f}
footer{margin-top:20px;color:var(--muted);font-size:12px}
</style>
</head>
<body>
<div class="wrap">
  <div class="logo">CpG</div>
  <h1>DNA Methylation in Breast Cancer</h1>
  <p class="lede">Tumour tissue against adjacent normal tissue, TCGA-BRCA.</p>

  <div class="facts">
    <div class="fact"><b>888</b><span>samples</span></div>
    <div class="fact"><b>486,427</b><span>DNA sites tested</span></div>
    <div class="fact"><b>30,827</b><span>sites changed</span></div>
    <div class="fact"><b>0.996</b><span>classifier AUC</span></div>
  </div>

  <a class="card" href="website/index.html">
    <b>Results website</b>
    <span>Ten sections: cohort, differential testing, validation, annotation,
      direction of effect, the marker panel, pathways and the atlas.</span></a>

  <a class="card" href="report.html">
    <b>Single-page report</b>
    <span>The whole analysis in one scrolling document. Print or save as PDF.</span></a>

  <div class="note">
    <b>Association only.</b> Not a clinical diagnostic, and a methylation
    difference is not evidence of causation. The classifier is cross-validated
    within this cohort and has not been tested on an independent one.
  </div>

  <footer>Static results. The pipeline that produced them runs separately.</footer>
</div>
</body>
</html>
"""

# Netlify and Vercel both serve a plain directory with no configuration. These
# exist only so a redeploy does not need the flags typed again.
NETLIFY_TOML = """# Static publish — no build step, no server.
[build]
  publish = "."
  command = ""
"""

VERCEL_JSON = """{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "cleanUrls": true,
  "trailingSlash": false
}
"""

README = """# Static results site

Everything in this folder is plain HTML with relative links. No build step, no
server, no environment variables.

## Deploy

**Netlify** — drag this folder onto https://app.netlify.com/drop. Done.
For a repeatable deploy: `npx netlify deploy --dir . --prod`.

**Vercel** — `npx vercel --prod` from inside this folder, and accept the
defaults (framework: Other, no build command).

**Cloudflare Pages** — `npx wrangler pages deploy .`

## Keeping it private

A static site is public by default on every one of these hosts. To restrict it:

- **Cloudflare Pages + Cloudflare Access** — email allowlist, one-time codes,
  free for a small number of users. This is the cheapest private option.
- **Netlify** — site-wide password protection is a paid plan feature.
- **Vercel** — production password protection is a paid plan feature. Team-only
  access on preview deployments is available on the free plan.

## What is not here

The studio — the interface that runs the pipeline — is deliberately absent. It
needs a process that survives the length of an analysis and a writable disk,
and serverless hosts provide neither. Run it on a machine you control:

    pip install -r requirements.txt
    python server/app_v3.py
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "publish"))
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    report = SITE / "Results_Presentation.html"
    website = SITE / "website_v2"
    missing = [str(p) for p in (report, website) if not p.exists()]
    if missing:
        raise SystemExit("Cannot publish - not found: %s" % ", ".join(missing))

    shutil.copy2(report, out / "report.html")
    shutil.copytree(website, out / "website")
    (out / "index.html").write_text(LANDING, encoding="utf-8")
    (out / "netlify.toml").write_text(NETLIFY_TOML, encoding="utf-8")
    (out / "vercel.json").write_text(VERCEL_JSON, encoding="utf-8")
    (out / "README.md").write_text(README, encoding="utf-8")

    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    files = sum(1 for p in out.rglob("*") if p.is_file())
    print("wrote %s" % out)
    print("  %d files, %.1f MB" % (files, total / 1e6))
    print("  index.html          landing page")
    print("  report.html         single-page report")
    print("  website/            %d-page results site"
          % len(list((out / 'website').glob('*.html'))))
    print("\nDeploy: drag the folder onto https://app.netlify.com/drop,")
    print("        or run  npx vercel --prod  from inside it.")


if __name__ == "__main__":
    main()
