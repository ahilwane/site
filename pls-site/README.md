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

The homepage displays a single looping client-logo row directly below its main introduction. Its first six logos load eagerly; later logos and the complete `/clients/` gallery use native lazy loading. “Our clients” links to that gallery, also linked from the footer and included in the sitemap. Company names and their client relationship are provided through image alternative text; no separate captions or company website links appear. There is no visible pause/play button. The row pauses on hover or keyboard focus; click/tap, Space, Escape or manual browsing stops it for the current page visit. Reduced-motion preferences receive a static, horizontally scrollable row. JavaScript duplicates the visual row for a seamless loop while keeping that copy hidden from assistive technology.

`content/site.json` lists 24 original client logos and six owner-requested neutral typographic name marks for businesses without supplied artwork. `content/client-logo-sources.json` records sources, dimensions and hashes and distinguishes those name marks from official branding. Original artwork retains its colours and proportions. The build copies only referenced client images and does not publish source records, testimonials or individual engagement descriptions.

Production canonical URLs use `https://pls-uae.com`; change `baseUrl` in `content/site.json` only if the production domain changes. The build supplies topic-specific descriptions and structured data for the company, adviser, services and articles. Confirmed PLS business details are held in `content/site.json`: telephone `+971 58 595 1040`, Al Musalla Tower, Dubai, UAE, and Monday–Friday 08:00–17:00 Dubai time. These appear in the homepage contact section, global footer and company structured data. No unconfirmed street, office unit or geographic coordinates are added. Public email is `ah@pls-uae.com`.

The four dedicated service routes are `/services/accounting-bookkeeping-dubai/`, `/services/corporate-tax-dubai/`, `/services/vat-reviews-dubai/` and `/services/zoho-books-e-invoicing-uae/`. Copy attributes Dr. Ahmad Helwani’s personal VAT/Corporate Tax Tax Agent role to Bonnard Lawson Dubai and does not claim that PLS is an FTA-registered agency or an Accredited Service Provider. The user-confirmed Zoho partner wording carries no unverified tier, certification or logo.

Before publishing a previously unpublished article on a later day, update its first-publication metadata truthfully. After authenticated deployment, verify the public service pages, new article, corrected older article, sitemap and mobile navigation. Public search or ChatGPT visibility must be measured separately from deployment success.

The robots file allows crawling, including OAI-SearchBot. Search indexing and inclusion in ChatGPT results depend on external discovery and ranking systems; metadata alone does not guarantee either outcome. The sitemap includes only published eligible pages.

Breadcrumb markup and its visible navigation are generated from the same page hierarchy on services, profile, articles and client pages; the homepage and 404 omit it. Indexable pages permit large image previews, while the 404 retains `noindex, follow`. Dr. Ahmad’s `Person` graph and profile-page preferred/sharing image use the approved profile portrait. The sitemap includes only standard image-location entries for published article covers, both approved website portraits and gallery logos, without future article assets.

Homepage service links use descriptive visible text. The professional profile links to all four dedicated service pages, and each current article ends with a relevant accounting, Corporate Tax or Zoho/e-invoicing service link. These links sit outside the approved, hash-verified article body fragments.

### Homepage portrait and layout

The homepage uses the owner-approved studio portrait with glasses (`assets/ahmad-helwani-home-approved.png`), and the professional profile uses the owner-approved modern-office portrait (`assets/ahmad-helwani-profile-approved.png`). These AI-assisted portraits were prepared from current user-supplied reference photos. Only these two approved portraits and their responsive variants are used in the public build; private reference photographs and unused portrait options are not published. The earlier unedited Bonnard Lawson portrait (`assets/ahmad-helwani-portrait.jpg`, originally from https://www.bonnard-lawson.com/wp-content/uploads/2022/10/Ahmad-Helwani-couleur-683x1024.jpg) remains in source for provenance and is excluded from the build.

Both approved portraits retain their complete proportions without a face crop. CSS supplies a soft shadow and a fully black-and-white appearance at full opacity, changing to full colour on hover. The homepage portrait link and the professional-profile enquiry links also reveal colour on keyboard focus; the profile-page image itself adds no redundant link or keyboard stop. Touch devices show full colour, and reduced-motion preferences disable transitions. Decorative service/process numbering has been removed. The introduction is justified on larger screens and left-aligned on phones; service headings reserve matching space so descriptions align within each row.

### Responsive image delivery

`content/image-variants.json` optionally maps each original portrait or article-cover path to a list of WebP variants. Each list entry records its local `path`, positive integer `width`, `height` and `bytes`, with dimensions in ascending order. For example:

```json
{
  "assets/ahmad-helwani-home-approved.png": [
    {"path": "assets/optimized/ahmad-helwani-home-approved-400.webp", "width": 400, "height": 500, "bytes": 18246},
    {"path": "assets/optimized/ahmad-helwani-home-approved-800.webp", "width": 800, "height": 1000, "bytes": 66376}
  ]
}
```

The standard-library-only builder validates every listed file beneath `assets/optimized/`, rejects missing files, traversal, outside paths, non-WebP variants, invalid dimensions and byte-count mismatches, and emits `src`, `srcset` and layout-specific `sizes` for portraits, article cards and full article covers. An image without a manifest entry uses its original URL. The smallest variant is the default `src`; the browser can select a larger one from `srcset` for its viewport and pixel density. Original dimensions, alternative text, loading priorities and portrait CSS classes are preserved.

The approved full-resolution originals remain unchanged and are used in sharing metadata, structured data and the image sitemap. During page rendering the builder records which responsive variants are actually used, then copies only those files into `public/`. Future article images and their optimized variants remain excluded until the article passes its publication gate. Preparing derivatives is separate from the build; production does not require Pillow or any image-processing dependency.


## Republished LinkedIn archive — 2 November 2026

Seven articles adapt Dr. Ahmad Helwani’s genuine earlier LinkedIn publications: US GAAP/IFRS (8 June 2023), Corporate Tax readiness (6 July 2023), transfer pricing (10 October 2023), OECD treaty updates (26 November 2025), IFRS 18 (10 February 2026), family foundations (11 June 2026), and free-zone substance (7 September 2026). The three 2023 dates are explicit on the original article pages; the four post timestamps come from the original LinkedIn `SocialMediaPosting.datePublished` JSON-LD, with matching author identity. Times are only represented as publication evidence where the source supplied them.

These are expanded, technically reviewed website editions. Their bylines label the verified original LinkedIn date and separately show the current update date. `originalPublicationAt` holds the source date or exact timestamp, `originalSource` is linked in the article and `isBasedOn` structured data, and `republishedAt` gates the archive’s first inclusion in website builds. This prevents a historical build from implying the archive was already present on the website. Existing article dates and release gates remain unchanged.

The owner excluded e-invoicing from this batch; CapEx/OpEx and VAT Profit Margin were also excluded because those topics already have articles. The seven new covers are AI-generated illustrative editorial photographs, individually generated for their subjects. Alt text and captions identify their illustrative purpose. Original photos were retained in the work package; the deployable site uses optimized JPEGs and responsive WebP variants.

`content/archive-publication.json` records the reviewed copy, official references, original publication evidence and the corresponding UAE Taxes publishing edition. It is source-only and is never copied to the public output. All archive body files retain linked primary sources, hypothetical examples and the current review date. The homepage shows the four latest articles; the article index lists the complete archive.


## Accounting service detail — 5 November 2026

The existing accounting and bookkeeping service page now explains recurring deliverables, reporting frequency, onboarding and opening-balance review, adviser handover, catch-up work, quotation factors and practical FAQs. These are agreed-scope descriptions: no fixed prices, submission outcomes or response-time guarantees are implied. The homepage stays concise. Its legal-role wording, address, client logos and gallery behaviour remain unchanged.

Confirmed PLS company profiles are held separately in `content/site.json` under `companyProfiles`, displayed in the global footer and included in the `AccountingService.sameAs` list. These are distinct from Dr. Ahmad Helwani’s personal biography/LinkedIn references. The verified company LinkedIn, Instagram and Facebook profiles are included; TikTok needs exact public profile confirmation before inclusion.


## Current VAT refund and accounting-controls articles — 5 November 2026

Two new PLS articles explain VAT-refund bookkeeping preparation and practical accounting controls that reduce tax-penalty risk. They use current official FTA/Ministry of Finance references, a current publication gate and generic article metadata. They are new website articles, not LinkedIn archive republications. Their accounting workflow focus differs from the corresponding UAE Taxes editions.

Each article uses an approved AI-generated illustrative cover, with an unchanged JPEG and a full-resolution WebP format variant. The body and original-cover hashes are validated by the normal builder. Both articles link to the existing accounting service; the refund checklist also links to VAT review support. The original eleven article bodies, dates and release metadata are preserved.


### Professional identity verification — 5 November 2026

The FTA’s public Registered Tax Agents directory was checked for “Helwani” on 5 November 2026. It lists Ahmad Abdulmomen Helwani, TAAN 20004461, with Bonnard Lawson (Dubai Branch), Dubai. The public profile explains how to find this record; the person graph records the full-name alias and professional TAAN. These fields describe Dr. Ahmad’s individual professional identity and do not identify PLS as a registered tax agency. No expiry or renewal date is asserted.

### FTA Tax Agent landing page — 6 November 2026

`/fta-tax-agent/` is a dedicated tax-services landing page for search enquiries. It contains original service copy covering VAT, Corporate Tax, FTA correspondence and focused specialist advice, followed by deliverables, process, professional verification, FAQs and direct phone/email actions. The page uses the approved homepage portrait and its responsive WebP variants; it includes no client-logo carousel, new form backend or third-party advertising tag.

Dr. Ahmad Helwani’s personal FTA tax-agent role is attributed to Bonnard Lawson Dubai in the hero and service scope. PLS accounting support is distinguished from formal tax-agent work. The service structured data identifies Dr. Ahmad as provider, with the existing professional affiliation; it does not identify PLS as a registered tax agency. Visible verification information matches the existing profile, including the 5 November directory-check date and TAAN 20004461.

The page is linked from the Services menu, footer and homepage specialist-tax section and is included in the sitemap with its approved portrait. Its metadata, visible FAQs and schema are generated together. Existing service URLs, article publication gates, business contacts and location details remain unchanged. Page publication does not itself activate a paid advertising campaign or conversion tracking.

### Arabic tax-agent counterpart — 11 November 2026

`/ar/fta-tax-agent/` is the Arabic counterpart of `/fta-tax-agent/`. Its approved copy is held in `content/fta-tax-agent-ar.json`; the builder supplies the existing PLS design, portrait, contact details, translated navigation and footer. The page uses `lang="ar"`, `dir="rtl"`, scoped RTL layout rules, a self-canonical and reciprocal `en`, `ar` and `x-default` language alternates on both counterparts. The Arabic route and existing portrait are included in the sitemap. Language switches connect the two pages.

The Arabic visible verification information and Person/Service data retain Ahmad Abdulmomen Helwani’s individual TAAN 20004461 and Bonnard Lawson Dubai role. The 5 November directory-check date remains an explicitly dated reference; no new credential expiry or verification date is invented. Existing article bodies, dates, release gates, company contacts and address are preserved.

Both tax-agent pages now include a short resource section connecting service enquiries and accounting support at PLS with Dr. Ahmad Helwani’s detailed tax guidance on UAE Taxes. It links to the existing `/tax-insights`, `/vat` and `/corporate-tax` destinations without duplicating those articles. The PLS homepage remains focused on accounting and bookkeeping. Validate the two published language pages, navigation, contact actions and resource links after deployment; a successful local build does not establish live publication or search indexing.
