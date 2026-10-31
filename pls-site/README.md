# PLS Accounting website

This repository contains the portable source for PLS Accounting’s static website. It needs Python 3 and its standard library only. The design uses the supplied PLS logos unchanged, logo blue `#303e9d`, and a system sans-serif font stack with Inter first when installed. No font service, npm packages, database, checkout, or payment form is required.

## Build and preview

```sh
python3 build.py
python3 -m http.server 8000 --directory public
```

Open `http://localhost:8000`. The build command writes a complete deployable website into `public/`. The output includes the homepage, professional profile, dedicated service pages, article index, eligible article pages and images, a 404 page, sitemap, robots file, and Cloudflare response headers. Do not use the source root as the hosting output: `content/` includes article source material.

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

The source retains approved release gates and actual first-publication timestamps where recorded. As at 27 October 2026:

| Article | Publication state | Date |
|---|---|---|
| UAE E-Invoicing: What Businesses Need to Do Before 2027 | Published; storage-guidance correction prepared | First published 4 October 2026 |
| Tax Planning vs Tax Evasion in the UAE: Where Is the Line? | Published | Actual first publication 17 October 2026 |
| AI and Tax Services: What the Future Means for UAE Businesses | Public; source release gate retained | 18 October 2026 |
| UAE E-Invoicing: Are You Ready? | Prepared for publication; not yet verified live | Approved 27 October 2026 |

At build time, `published` and `scheduled` articles are eligible only when their timezone-aware `publicationAt` timestamp has passed. A `draft` status excludes an article regardless of its date. Filtering happens before HTML, navigation cards, structured data, sitemap entries or images are emitted. Browser-side hiding is not used. Source statuses are never silently rewritten. A `published` source status makes an approved article eligible for the build; it does not independently verify that deployment has occurred. In a public GitHub repository, the source drafts are viewable on GitHub even before the website release date; use a private repository if source confidentiality is required.

A static host does not release articles merely because time passes: **a new build and deployment are required**. A push to the production branch or a Cloudflare Pages deploy hook can trigger that build. To automate the two approved releases, create a Pages deploy hook, save its URL as the `CLOUDFLARE_PAGES_DEPLOY_HOOK` GitHub Actions secret, and review the inactive example before copying it into the GitHub repository root’s `.github/workflows/` directory. Scheduled workflows run only from the repository’s default branch: putting an active workflow solely on the rebuild branch will not schedule it. Do not expose the hook URL in public source. The example is not activated in this package.

The example targets 08:00 UTC, which is noon Dubai time, and includes a 2026 guard against repeat annual deployments. GitHub can delay or skip scheduled runs; a deploy hook response also does not establish that the resulting deployment succeeded. Check the first live release. If an article actually becomes public on a later calendar date, add its verified timezone-aware `actualPublicationAt` value to the manifest so its visible **Published** date and structured data record the actual first publication. The original `publicationAt` remains the approved release gate. After the two October 2026 releases, remove the example’s annual October cron schedule. [GitHub scheduled-workflow limitations](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) · [Cloudflare deploy hooks](https://developers.cloudflare.com/pages/configuration/deploy-hooks/).

For isolated boundary checks, use a separate source copy and a timezone-aware override:

```sh
python3 build.py --at 2026-10-11T11:59:59+04:00
python3 build.py --at 2026-10-11T12:00:00+04:00
```

Do not set `--at` in the production build command. `build-report.json` is local build evidence and is never copied into the public site.

## Search metadata and contact

### Selected clients

The homepage displays a single looping client-logo row directly below its main introduction. “Our clients” links to the static `/clients/` gallery, also linked from the footer and included in the sitemap. Company names and their client relationship are provided through image alternative text; no separate captions or company website links appear. There is no visible pause/play button. The row pauses on hover or keyboard focus; click/tap, Space, Escape or manual browsing stops it for the current page visit. Reduced-motion preferences receive a static, horizontally scrollable row. JavaScript duplicates the visual row for a seamless loop while keeping that copy hidden from assistive technology.

`content/site.json` lists 24 original client logos and six owner-requested neutral typographic name marks for businesses without supplied artwork. `content/client-logo-sources.json` records sources, dimensions and hashes and distinguishes those name marks from official branding. Original artwork retains its colours and proportions. The build copies only referenced client images and does not publish source records, testimonials or individual engagement descriptions.

Production canonical URLs use `https://pls-uae.com`; change `baseUrl` in `content/site.json` only if the production domain changes. The build supplies topic-specific descriptions and structured data for the company, adviser, services and articles. Confirmed PLS business details are held in `content/site.json`: telephone `+971 58 595 1040`, Al Musalla Tower, Dubai, UAE, and Monday–Friday 08:00–17:00 Dubai time. These appear in the homepage contact section, global footer and company structured data. No unconfirmed street, office unit or geographic coordinates are added. Public email is `ah@pls-uae.com`.

The four dedicated service routes are `/services/accounting-bookkeeping-dubai/`, `/services/corporate-tax-dubai/`, `/services/vat-reviews-dubai/` and `/services/zoho-books-e-invoicing-uae/`. Copy attributes Dr. Ahmad Helwani’s personal VAT/Corporate Tax Tax Agent role to Bonnard Lawson Dubai and does not claim that PLS is an FTA-registered agency or an Accredited Service Provider. The user-confirmed Zoho partner wording carries no unverified tier, certification or logo.

Before publishing a previously unpublished article on a later day, update its first-publication metadata truthfully. After authenticated deployment, verify the public service pages, new article, corrected older article, sitemap and mobile navigation. Public search or ChatGPT visibility must be measured separately from deployment success.

The robots file allows crawling, including OAI-SearchBot. Search indexing and inclusion in ChatGPT results depend on external discovery and ranking systems; metadata alone does not guarantee either outcome. The sitemap includes only published eligible pages.

### Homepage portrait and layout

The homepage uses the owner-approved studio portrait with glasses (`assets/ahmad-helwani-home-approved.png`), and the professional profile uses the owner-approved modern-office portrait (`assets/ahmad-helwani-profile-approved.png`). These AI-assisted portraits were prepared from current user-supplied reference photos. Only the two approved final website images are copied into the public build; private reference photographs and unused variants are not published. The earlier unedited Bonnard Lawson portrait (`assets/ahmad-helwani-portrait.jpg`, originally from https://www.bonnard-lawson.com/wp-content/uploads/2022/10/Ahmad-Helwani-couleur-683x1024.jpg) remains in source for provenance and is excluded from the build.

Both approved portraits retain their complete proportions without a face crop. CSS supplies a soft shadow and a fully black-and-white appearance at full opacity, changing to full colour on hover. The homepage portrait link and the professional-profile enquiry links also reveal colour on keyboard focus; the profile-page image itself adds no redundant link or keyboard stop. Touch devices show full colour, and reduced-motion preferences disable transitions. Decorative service/process numbering has been removed. The introduction is justified on larger screens and left-aligned on phones; service headings reserve matching space so descriptions align within each row.
