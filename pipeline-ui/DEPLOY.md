# Sharing the results

## Live now

**https://sanskritiaripineni.github.io/Methylation/**

Served from the `gh-pages` branch of this repository: a landing page, the
single-page report, and the 11-page results website. GitHub enabled Pages
automatically when the branch was pushed.

> **This is public.** Anyone with the link can read it, and search engines can
> index it. Nothing gates it. See *Making it private* below.

### Updating it

```bash
python deploy_gh_pages.py            # shows the plan, publishes nothing
python deploy_gh_pages.py --push     # publishes
```

The push is opt-in on purpose. The script works in a temp clone, so your
working tree and current branch are never touched.

### What is published

Only the finished results, copied byte for byte from `web/site/` — the same
files the pipeline wrote. The published numbers can never drift from the real
ones because nothing is re-rendered.

The studio itself is **not** published, and cannot be: running the pipeline
needs a process that stays alive for the length of an analysis and a disk it
can write to. Static hosting provides neither.

---

## Making it private

Pick based on what you need.

### Cloudflare Pages + Cloudflare Access — free, private, needs a login

The only free option that actually restricts who can view. You add specific
email addresses; they get a one-time code; nobody else gets in.

Requires Node.js (not currently installed on this machine) and a Cloudflare
account. Both steps below are yours to do — the login is a browser flow.

```bash
npm install -g wrangler
wrangler login                                    # opens your browser
python publish.py
cd publish
wrangler pages deploy . --project-name methylation-results
```

Then in the Cloudflare dashboard:

1. **Zero Trust → Access → Applications → Add an application → Self-hosted**
2. Domain: the `*.pages.dev` hostname the deploy printed
3. **Add policy** → Action **Allow** → Include → **Emails** → list the people
   who should see it
4. Save. The site now asks for an email, sends a code, and lets nobody else in.

Free for a small number of users at time of writing.

### GitHub Pages on a private repository

If you make this repo private, Pages on a private repo requires a paid GitHub
plan, and even then the published site stays publicly reachable unless you are
on Enterprise. **So: making the repo private will break the link above**, and
will not make the site private. Move to Cloudflare Access first if privacy
matters.

### Netlify / Vercel

Both host this folder with no configuration:

```bash
npx netlify deploy --dir publish --prod
npx vercel --prod            # run from inside publish/
```

Password protection is a paid plan feature on both. Vercel's free
team-only access applies to preview deployments, not production.

---

## Sharing the runnable studio

Not a hosting problem — hand people the folder:

```bash
pip install -r requirements.txt
python server/app_v3.py
```

Their data stays on their own machine and nothing is exposed. For a handful of
collaborators this is the right answer.

If you need it always-on for many people, it belongs on a container host with a
persistent disk (Render, Railway, Fly — roughly $7–15/month), and it needs
three things added first, because that machine would be reachable from the
internet:

1. **A login.** There is none today.
2. **A path jail.** The advanced console's "Local path" field is designed to
   read any path on the host, which is fine on your laptop and not fine on a
   public server.
3. **Per-visitor workspaces.** Everyone currently shares one `workspace/`
   folder and would overwrite each other's uploads.
