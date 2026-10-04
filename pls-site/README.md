# PLS Accounting website

This repository contains the portable source for PLS Accounting’s static website. It needs Python 3 and its standard library only. The design uses the supplied PLS logos unchanged, logo blue `#303e9d`, and a system sans-serif font stack with Inter first when installed. No font service, npm packages, database, checkout, or payment form is required.

## Build and preview

```sh
python3 build.py
python3 -m http.server 8000 --directory public
```

Open `http://localhost:8000`. The build command writes a complete deployable website into `public/`. The output includes the homepage, professional profile, article index, eligible article pages and images, a 404 page, sitemap, robots file, and Cloudflare response headers. Do not use the source root as the hosting output: `content/` includes the approved future article drafts.

## Source files

- `content/site.json`: approved website copy, links, services, FAQ, and company settings.
- `content/articles.json`: all approved article metadata, source publication statuses, release timestamps, image captions/alt text, citations, and verification hashes.
- `content/articles/`: approved article body fragments, including future articles.
- `assets/`: supplied logos, site styles and menu script. `assets/articles/` contains every approved cover image; the builder copies only eligible ones into `public/`.
- `build.py`: the complete deterministic rendering and release filtering logic, with no sibling-directory dependencies.
- `examples/scheduled-deploy.yml`: an inactive optional GitHub Actions example. It does not run from this directory.

The body and cover hashes protect the approved article package. After an intentional article edit, update its corresponding SHA-256 value in `content/articles.json` before building. `sourceHtmlSha256` records the original reviewed document and is reference metadata, not a runtime dependency.

## Free Cloudflare Pages setup

1. Add this package in a separate `pls-site/` folder on the rebuild branch of the existing GitHub repository. This preserves the old root website while the new free hosting is prepared. Keep that branch unconfigured for GitHub Pages. This package does not activate GitHub Pages and contains no Pages deployment workflow or `CNAME` file. It also works as a standalone repository root if desired.
2. In Cloudflare, open **Workers & Pages → Create application → Pages → Connect to Git** and select the GitHub repository and production branch.
3. Use **Framework preset: None**, **Root directory: `pls-site`**, **Build command: `python3 build.py`**, and **Build output directory: `public`**. The output path is relative to the selected root directory. Leave the root directory blank only when this package is at the repository root. Python 3 is the only runtime required.
4. Deploy and review the generated `pages.dev` preview. Its canonical URLs intentionally point at the intended production domain, `https://pls-uae.com`.
5. Add `pls-uae.com` and the desired `www` hostname through the Pages project’s **Custom domains** screen. Follow Cloudflare’s domain verification and DNS instructions. For an apex domain, Cloudflare Pages generally requires its zone on Cloudflare; preserve all existing email/MX, TXT, and other DNS records while setting up the zone. Custom domain connection is a separate live action.
6. Review the live homepage, email link, profile, article and references. Confirm HTTPS, custom-domain canonical URLs, `/sitemap.xml`, `/robots.txt`, and the intended redirect from the alternate hostname.

Cloudflare’s Free Pages plan can host the static site with a custom domain. Existing domain registration and renewal remain separate. Check the current platform limits before enabling automated builds. Official references: [Git integration](https://developers.cloudflare.com/pages/configuration/git-integration/), [build configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/), [custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/), and [Pages limits](https://developers.cloudflare.com/pages/platform/limits/).

## Article publication and scheduling

The source retains the following approved statuses and Dubai timestamps:

| Article | Source status | Eligible from |
|---|---|---|
| UAE E-Invoicing: What Businesses Need to Do Before 2027 | Published | 4 October 2026, 16:23 Dubai |
| Tax Planning vs Tax Evasion in the UAE: Where Is the Line? | Scheduled | 11 October 2026, 12:00 Dubai |
| AI and Tax Services: What the Future Means for UAE Businesses | Scheduled | 18 October 2026, 12:00 Dubai |

At build time, `published` and `scheduled` articles are eligible only when their timezone-aware `publicationAt` timestamp has passed. A `draft` status excludes an article regardless of its date. Filtering happens before HTML, navigation cards, structured data, sitemap entries or images are emitted. Neither scheduled article appears in today’s public website output. Browser-side hiding is not used. Source statuses are never silently rewritten. In a public GitHub repository, the source drafts are viewable on GitHub even before the website release date; use a private repository if source confidentiality is required.

A static host does not release articles merely because time passes: **a new build and deployment are required**. A push to the production branch or a Cloudflare Pages deploy hook can trigger that build. To automate the two approved releases, create a Pages deploy hook, save its URL as the `CLOUDFLARE_PAGES_DEPLOY_HOOK` GitHub Actions secret, and review the inactive example before copying it into the GitHub repository root’s `.github/workflows/` directory. Scheduled workflows run only from the repository’s default branch: putting an active workflow solely on the rebuild branch will not schedule it. Do not expose the hook URL in public source. The example is not activated in this package.

The example targets 08:00 UTC, which is noon Dubai time, and includes a 2026 guard against repeat annual deployments. GitHub can delay or skip scheduled runs; a deploy hook response also does not establish that the resulting deployment succeeded. Check the first live release. If an article actually becomes public on a later calendar date, add its verified timezone-aware `actualPublicationAt` value to the manifest so its visible **Published** date and structured data record the actual first publication. The original `publicationAt` remains the approved release gate. After the two October 2026 releases, remove the example’s annual October cron schedule. [GitHub scheduled-workflow limitations](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) · [Cloudflare deploy hooks](https://developers.cloudflare.com/pages/configuration/deploy-hooks/).

For isolated boundary checks, use a separate source copy and a timezone-aware override:

```sh
python3 build.py --at 2026-10-11T11:59:59+04:00
python3 build.py --at 2026-10-11T12:00:00+04:00
```

Do not set `--at` in the production build command. `build-report.json` is local build evidence and is never copied into the public site.

## Search metadata and contact

Production canonical URLs use `https://pls-uae.com`; change `baseUrl` in `content/site.json` only if the production domain changes. The build supplies topic-specific article descriptions, `AccountingService`, `Person`, `ProfilePage`, `CollectionPage` and `BlogPosting` structured data. The company address and phone are omitted because they were not confirmed. Public contact is `ah@pls-uae.com` only.

The robots file allows crawling, including OAI-SearchBot. Search indexing and inclusion in ChatGPT results depend on external discovery and ranking systems; metadata alone does not guarantee either outcome. The sitemap includes only published eligible pages.
