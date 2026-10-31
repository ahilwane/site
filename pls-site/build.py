#!/usr/bin/env python3
"""Build PLS's static website using Python 3's standard library only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import shutil
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent

SERVICE_LINKS = (
    ('/services/accounting-bookkeeping-dubai/', 'Accounting and bookkeeping', 'Accounting and Bookkeeping Services in Dubai'),
    ('/services/corporate-tax-dubai/', 'Corporate Tax', 'Corporate Tax Advisory and Compliance in Dubai'),
    ('/services/vat-reviews-dubai/', 'VAT services', 'VAT Registration, Returns and Reviews in Dubai'),
    ('/services/zoho-books-e-invoicing-uae/', 'Zoho Books and e-invoicing', 'Zoho Books and UAE E-Invoicing Readiness'),
)

# Record substantial page changes; shared navigation updates do not refresh dates.
SERVICE_MODIFIED = {
    '/services/accounting-bookkeeping-dubai/': '2026-10-29',
    '/services/corporate-tax-dubai/': '2026-10-29',
    '/services/vat-reviews-dubai/': '2026-10-29',
    '/services/zoho-books-e-invoicing-uae/': '2026-10-27',
}


def h(value):
    return escape(str(value), quote=True)


def parse_time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Publication and build times must include a UTC offset.")
    return parsed


def icon(name="arrow"):
    paths = {
        "arrow": '<path d="M5 12h14m-6-6 6 6-6 6"/>',
        "external": '<path d="M14 4h6v6M20 4 10 14M20 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h5"/>',
        "ledger": '<path d="M3 4h5a6 6 0 0 1 4 2 6 6 0 0 1 4-2h5v15h-5a6 6 0 0 0-4 2 6 6 0 0 0-4-2H3ZM12 6v15"/>',
        "document": '<path d="M14 3H5v18h14V8ZM14 3v5h5M8 12h8M8 16h6"/>',
        "chart": '<path d="M3 3v18h18M7 16v-5M12 16V7M17 16V4"/>',
        "compass": '<circle cx="12" cy="12" r="9"/><path d="m16 8-3 5-5 3 3-5Z"/>',
        "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c5 6 5 12 0 18-5-6-5-12 0-18"/>',
        "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 6 9 7 9-7"/>',
        "check": '<path d="m5 12 4 4L19 6"/>',
        "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    }
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths[name]}</svg>'


def link(url, label, css="text-link", glyph="arrow"):
    return f'<a class="{h(css)}" href="{h(url)}">{h(label)}{icon(glyph)}</a>'


def published_time(article):
    # Optional actual first-live timestamp takes precedence after publication is verified.
    return parse_time(article.get("actualPublicationAt") or article["publicationAt"])


def publication_label(article):
    date = published_time(article).astimezone(timezone.utc).astimezone(parse_time(article["publicationAt"]).tzinfo)
    return f"{date.day} {date.strftime('%B %Y')}"


class Builder:
    def __init__(self, at):
        self.at = at
        self.site = json.loads((ROOT / "content/site.json").read_text(encoding="utf-8"))
        self.manifest = json.loads((ROOT / "content/articles.json").read_text(encoding="utf-8"))
        self.base = self.site["baseUrl"].rstrip("/")
        # A new asset URL prevents returning visitors from mixing old styles/scripts with new HTML.
        self.asset_urls = {
            name: f"/assets/{Path(name).stem}.{hashlib.sha256((ROOT / 'assets' / name).read_bytes()).hexdigest()[:12]}{Path(name).suffix}"
            for name in ("site.css", "site.js")
        }
        if urlparse(self.base).scheme != "https" or not urlparse(self.base).netloc:
            raise ValueError("baseUrl must be an absolute HTTPS URL.")
        self.articles = []
        self.excluded = []
        for article in self.manifest["articles"]:
            if article["status"] in {"published", "scheduled"} and parse_time(article["publicationAt"]) <= at:
                if article.get("actualPublicationAt") and published_time(article) > at:
                    self.excluded.append(article["id"])
                    continue
                self.articles.append(article)
            else:
                self.excluded.append(article["id"])
        self.articles.sort(key=published_time, reverse=True)

    def company(self):
        return {
            "@type": "AccountingService", "@id": self.base + "/#company",
            "name": self.site["name"], "alternateName": self.site["legalName"],
            "url": self.base + "/", "logo": self.base + "/assets/pls-logo.png",
            "email": self.site["email"], "areaServed": {"@type": "Country", "name": "United Arab Emirates"},
            "description": self.site["homeDescription"],
            "telephone": self.site["telephone"],
            "address": {"@type": "PostalAddress", "streetAddress": self.site["address"]["building"], "addressLocality": self.site["address"]["city"], "addressCountry": self.site["address"]["countryCode"]},
            "openingHoursSpecification": [{"@type": "OpeningHoursSpecification", "dayOfWeek": self.site["businessHours"]["days"], "opens": self.site["businessHours"]["opens"], "closes": self.site["businessHours"]["closes"]}],
            "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Accounting and business services in the UAE", "itemListElement": [
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": item["title"], "description": item["text"]}}
                for item in self.site["services"]
            ]},
        }

    def person(self):
        return {
            "@type": "Person", "@id": self.base + "/ahmad-helwani/#person",
            "name": "Dr. Ahmad Helwani", "url": self.base + "/ahmad-helwani/",
            "jobTitle": "Managing Partner", "worksFor": {"@id": self.base + "/#company"},
            "email": self.site["email"], "description": self.site["biography"],
            "knowsLanguage": ["English", "Arabic"],
            "knowsAbout": ["UAE VAT", "UAE Corporate Tax", "Accounting", "Zoho Books"],
            "affiliation": {"@type": "Organization", "name": "Bonnard Lawson Dubai", "url": "https://www.bonnard-lawson.com/"},
            "sameAs": [self.site["links"]["biography"], self.site["links"]["linkedin"]],
        }

    def header(self, active):
        profile_current = ' aria-current="page"' if active == "profile" else ""
        articles_current = ' aria-current="page"' if active == "articles" else ""
        service_menu = ''.join(f'<a href="{h(path)}">{h(label)}</a>' for path, label, _ in SERVICE_LINKS)
        services_class = ' service-nav-current' if active == 'services' else ''
        return f'''<a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="wrap nav-wrap">
<a class="brand" href="/" aria-label="PLS Accounting home"><img src="/assets/pls-logo-compact.jpg" width="569" height="154" alt="PLS Accounting"></a>
<button class="nav-toggle" type="button" aria-controls="site-navigation" aria-expanded="false" aria-label="Open navigation">{icon('menu')}</button>
<nav class="nav" id="site-navigation" aria-label="Main navigation"><details class="service-nav{services_class}"><summary>Services</summary><div class="service-nav-menu"><a href="/#services">All services</a>{service_menu}</div></details><a href="/ahmad-helwani/"{profile_current}>Dr. Ahmad Helwani</a><a href="/articles/"{articles_current}>Articles</a><a class="nav-contact" href="/#contact">Contact</a></nav>
</div></header>'''

    def footer(self):
        clients_link = '<a href="/clients/">Clients</a>' if self.site.get('clients') else ''
        return f'''<footer class="site-footer"><div class="wrap"><div class="footer-grid"><div class="footer-brand"><a href="/" aria-label="PLS Accounting home"><img src="/assets/pls-logo.png" width="570" height="183" alt="PLS Accounting — Prime Ledger Solution for Accounting Services" loading="lazy"></a></div><nav class="footer-links" aria-label="Footer navigation"><a href="/#services">Services</a>{clients_link}<a href="/ahmad-helwani/">Dr. Ahmad Helwani</a><a href="/articles/">Articles</a><a href="{h(self.site['links']['taxes'])}">UAE Taxes</a><a href="mailto:{h(self.site['email'])}">Email PLS</a></nav></div><div class="footer-contact"><p>{h(self.site['address']['building'])}, {h(self.site['address']['city'])}, UAE</p><p><a href="tel:{h(self.site['telephone'])}">{h(self.site['phoneDisplay'])}</a></p><p>{h(self.site['businessHours']['display'])}</p></div><div class="footer-base"><p>© {self.at.year} PLS Accounting. All rights reserved.</p><p>Prime Ledger Solution for Accounting Services</p></div></div></footer>'''

    def client_logo_path(self, client):
        logo = client.get('logo')
        if not logo:
            return None
        path = Path(logo)
        if path.is_absolute() or '..' in path.parts or path.parts[:2] != ('assets', 'clients') or path.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp', '.svg'}:
            raise ValueError('Client logos must use local image paths under assets/clients/.')
        source = (ROOT / path).resolve()
        client_root = (ROOT / 'assets' / 'clients').resolve()
        if ROOT not in source.parents or client_root not in source.parents or not source.is_file():
            raise ValueError(f'Client logo is missing or outside assets/clients/: {logo}')
        return path

    def client_items(self, loading='eager'):
        clients = self.site.get('clients', [])
        if not clients:
            return ''
        items = []
        for client in clients:
            name = client['name']
            logo = self.client_logo_path(client)
            if logo:
                width, height = int(client.get('logoWidth', 320)), int(client.get('logoHeight', 160))
                if width <= 0 or height <= 0:
                    raise ValueError('Client logo dimensions must be positive.')
                logo_class = 'client-logo client-logo-dark' if client.get('logoBackground') == 'dark' else 'client-logo'
                image = f'<span class="{logo_class}"><img src="/{h(logo.as_posix())}" alt="{h(name)} — PLS Accounting client" width="{width}" height="{height}" loading="{h(loading)}" decoding="async"></span>'
            else:
                image = f'<span class="client-wordmark">{h(name)}</span>'
            items.append(f'<li class="client-item">{image}</li>')
        return ''.join(items)

    def clients_section(self):
        if not self.site.get('clients'):
            return ''
        return '''<section class="clients-section" id="clients" aria-labelledby="clients-title"><div class="wrap"><div class="clients-header"><h2 id="clients-title"><a href="/clients/">Our clients''' + icon('arrow') + '''</a></h2></div><p id="clients-instructions" class="clients-instructions">The logos move automatically. Click or tap the row, or press Space or Escape, to stop the motion. Swipe or use the left and right arrow keys to browse. Follow Our clients to view the full gallery.</p><div class="clients-viewport" tabindex="0" role="region" aria-label="Client logos" aria-describedby="clients-instructions"><div class="clients-track"><ul class="client-list">''' + self.client_items() + '</ul></div></div></div></section>'

    def clients_page(self):
        path = '/clients/'
        description = 'Explore businesses that work with PLS Accounting in Dubai and across the UAE, with our client logo gallery.'
        content = '''<section class="page-hero"><div class="wrap"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">PLS Accounting</a><span aria-hidden="true">/</span><span aria-current="page">Our clients</span></nav><h1>Our clients</h1><p class="page-lead">A selection of businesses that work with PLS Accounting in Dubai and across the UAE.</p></div></section><section class="section clients-gallery" aria-label="PLS Accounting client gallery"><div class="wrap"><ul class="client-gallery-list">''' + self.client_items('lazy') + '</ul></div></section>'
        collection = {'@type': 'CollectionPage', '@id': self.base + path + '#page', 'url': self.base + path, 'name': 'Our clients | PLS Accounting', 'description': description, 'about': {'@id': self.base + '/#company'}}
        return self.page('Our Clients | PLS Accounting', description, path, content, [self.company(), collection])

    def page(self, title, description, path, content, graph=None, active="", image=None, image_alt="PLS Accounting logo", article=False, noindex=False):
        url = self.base + path
        image = image or self.base + "/assets/pls-logo.png"
        canonical = "" if noindex else f'<link rel="canonical" href="{h(url)}">'
        robots = '<meta name="robots" content="noindex, follow">' if noindex else ""
        verification = '<meta name="google-site-verification" content="zUTLfmqYzChhmWgAQjYGrYNKUWl5BHOes7OxhkO8JHI"><meta name="msvalidate.01" content="5369E22398CA740655C138DAD554D86F">' if path == "/" else ""
        graph = graph or [self.company()]
        structured = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("<", "\\u003c")
        return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)}</title><meta name="description" content="{h(description)}"><meta name="theme-color" content="#303e9d">{canonical}{robots}{verification}
<meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:title" content="{h(title)}"><meta property="og:description" content="{h(description)}"><meta property="og:url" content="{h(url)}"><meta property="og:image" content="{h(image)}"><meta property="og:image:alt" content="{h(image_alt)}"><meta property="og:site_name" content="PLS Accounting"><meta name="twitter:card" content="{'summary_large_image' if article else 'summary'}">
<link rel="icon" href="/assets/pls-logo.png" type="image/png"><link rel="stylesheet" href="{h(self.asset_urls['site.css'])}"><script src="{h(self.asset_urls['site.js'])}" defer></script>
<script type="application/ld+json">{structured}</script></head><body>{self.header(active)}<main id="main">{content}</main>{self.footer()}</body></html>\n'''

    def faq(self):
        return '<div class="faq">' + "".join(f'<details><summary>{h(item["question"])}</summary><p>{h(item["answer"])}</p></details>' for item in self.site["faq"]) + '</div>'

    def article_card(self, article, featured=False):
        path = f'/articles/{article["slug"]}/'
        image_path = "/" + article["coverImage"]
        return f'''<article class="article-card{' featured' if featured else ''}"><a class="article-image" href="{h(path)}" tabindex="-1" aria-hidden="true"><img src="{h(image_path)}" width="{article['imageWidth']}" height="{article['imageHeight']}" alt="{h(article['imageAlt'])}" loading="lazy"></a><div class="article-card-copy"><p class="article-meta"><time datetime="{published_time(article).date().isoformat()}">{h(publication_label(article))}</time><span>By Dr. Ahmad Helwani</span></p><h3><a href="{h(path)}">{h(article['title'])}</a></h3><p>{h(article['description'])}</p>{link(path,'Read article')}</div></article>'''

    def external_articles(self):
        cards = "".join(f'''<article class="external-card"><p class="eyebrow">UAE Taxes</p><h3><a href="{h(item['url'])}">{h(item['title'])}</a></h3><p>{h(item['description'])}</p><p class="byline">By Dr. Ahmad Helwani</p>{link(item['url'],'Read article',glyph='external')}</article>''' for item in self.site['externalArticles'])
        return f'''<section class="section related-section" aria-labelledby="more-articles-title"><div class="wrap"><div class="section-header"><div><p class="eyebrow">Further reading</p><h2 id="more-articles-title">More articles by Dr. Ahmad Helwani</h2></div><p>Practical explanations of UAE tax topics, published on UAE Taxes.</p></div><div class="external-grid">{cards}</div><div class="section-action">{link(self.site['links']['taxArticles'],'Read more articles','button secondary','external')}</div></div></section>'''

    def home(self):
        s, urls = self.site, self.site['links']
        def service_card(item):
            action = ''
            if item.get('url'):
                action = f'<a class="text-link service-action" href="{h(item["url"])}" aria-label="Explore {h(item["title"])}">Explore service{icon("arrow")}</a>'
            return f'''<article class="service-card"><div class="service-top"><span class="service-icon">{icon(item['icon'])}</span></div><h3>{h(item['title'])}</h3><p>{h(item['text'])}</p><ul class="service-tags">{''.join(f'<li>{h(tag)}</li>' for tag in item['tags'])}</ul>{action}</article>'''
        services = ''.join(service_card(item) for item in s['services'])
        cards = "".join(self.article_card(a,len(self.articles)==1) for a in self.articles)
        if not cards:
            cards = '<p>Explore Dr. Ahmad Helwani’s existing articles on <a href="https://uae-taxes.com/tax-insights">UAE Taxes</a>.</p>'
        content = f'''<section class="hero" aria-labelledby="hero-title"><div class="wrap hero-grid"><div class="hero-copy"><p class="eyebrow">Prime Ledger Solution for Accounting Services</p><h1 id="hero-title">{h(s['heroTitle'])}</h1><p class="hero-intro">{h(s['heroIntro'])}</p><div class="button-row">{link('/#services','Explore our services','button')}{link('/ahmad-helwani/','Meet Dr. Ahmad','button secondary')}</div><p class="hero-note">{icon('globe')}UAE business support · English &amp; Arabic enquiries</p></div><div class="hero-art"><p class="art-label">A considered approach</p><div class="document"><div class="document-heading"><span class="document-symbol">{icon('ledger')}</span><p class="eyebrow">From records to decisions</p><h2>Bring the details together.</h2></div><div class="document-row"><div><strong>Understand your records</strong><small>Accounts, invoices &amp; supporting documents</small></div></div><div class="document-row"><div><strong>Clarify the question</strong><small>Business context &amp; information gaps</small></div></div><div class="document-row"><div><strong>Identify the next step</strong><small>A scope shaped around your needs</small></div></div><div class="document-footer">PLS Accounting <span>Records → context → decisions</span></div></div></div></div></section>
{self.clients_section()}
<div class="intro-band"><div class="wrap intro-grid"><div>{icon('ledger')}<span><strong>Accounting &amp; bookkeeping</strong><small>Organised records and useful information</small></span></div><div>{icon('document')}<span><strong>VAT &amp; Corporate Tax</strong><small>Registration, filing and advisory</small></span></div><div>{icon('globe')}<span><strong>English &amp; Arabic</strong><small>Enquiries in either language</small></span></div></div></div>
<section class="section" id="services" aria-labelledby="services-title"><div class="wrap"><div class="section-header"><div><p class="eyebrow">How we can help</p><h2 id="services-title">Accounting, Zoho Books and tax support</h2></div><p>Choose the service you need, then agree the scope, records and deliverables for your business.</p></div><div class="services-grid">{services}</div><p class="services-note">Start with our <a href="/services/accounting-bookkeeping-dubai/">accounting and bookkeeping services</a> or <a href="/services/zoho-books-e-invoicing-uae/">Zoho Books implementation</a>. For specialist tax advice, explore Dr. Ahmad Helwani’s <a href="{h(urls['taxes'])}">UAE Taxes website</a>.</p></div></section>
<section class="section profile-section" id="meet-dr-ahmad" aria-labelledby="profile-title"><div class="wrap profile-grid"><div class="profile-panel"><a class="profile-portrait-link" href="/ahmad-helwani/" aria-label="View Dr. Ahmad Helwani’s professional profile"><img class="profile-portrait adviser-portrait" src="/assets/ahmad-helwani-home-approved.png" width="1122" height="1402" alt="Dr. Ahmad Helwani, Managing Partner of PLS Accounting" loading="lazy" decoding="async"></a><div class="profile-panel-caption"><p class="eyebrow">Managing Partner</p><h3>Dr. Ahmad Helwani</h3><p>UAE accounting, finance &amp; tax</p><span class="language">{icon('globe')} English &amp; Arabic</span></div></div><div class="profile-copy"><p class="eyebrow">Meet Dr. Ahmad Helwani</p><h2 id="profile-title">Experience with the details that matter.</h2><p>{h(s['biography'])}</p><p>His experience includes healthcare, real estate and industrial businesses. His Bonnard Lawson biography sets out his professional background and VAT and Corporate Tax tax-agent memberships.</p>{link('/ahmad-helwani/','Explore his professional profile')}<div class="profile-links">{link(urls['biography'],'Professional biography',glyph='external')}{link(urls['linkedin'],'LinkedIn profile',glyph='external')}</div></div></div></section>
<section class="section" id="approach" aria-labelledby="approach-title"><div class="wrap"><div class="section-header"><div><p class="eyebrow">Start with your business question</p><h2 id="approach-title">Context first. Then the detail.</h2></div><p>A useful first discussion starts with your business, the question you are facing and the records available.</p></div><div class="process-grid"><article class="process-step"><h3>Describe the question</h3><p>Share a short business overview, the relevant period and the issue you want to discuss.</p></article><article class="process-step"><h3>Identify the records</h3><p>Explain which accounts, invoices or supporting documents are available and what information is still missing.</p></article><article class="process-step"><h3>Discuss the scope</h3><p>Agree what needs to be reviewed and the next information to gather before an engagement begins.</p></article></div></div></section>
<section class="section tax-section" aria-labelledby="tax-title"><div class="wrap tax-grid"><div class="tax-copy"><p class="eyebrow">Specialist tax advice</p><h2 id="tax-title">Connect your accounts with the tax question.</h2><p>PLS coordinates accounting records and tax-return preparation. Dr. Ahmad Helwani’s UAE Taxes website explains his specialist VAT and Corporate Tax advisory services.</p><div class="button-row">{link(urls['vat'],'VAT advisory on UAE Taxes','button secondary')}{link(urls['corporateTax'],'Corporate Tax advisory on UAE Taxes','text-link')}</div></div><div class="deliverable"><p class="eyebrow">What you receive from a VAT review</p><h3>A written explanation and next steps.</h3><p>{h(s['vatDeliverable'])}</p><ul><li>{icon('check')}The issue and information reviewed</li><li>{icon('check')}Any unresolved information gaps</li><li>{icon('check')}Recommended next steps</li></ul></div></div></section>
<section class="section" id="articles" aria-labelledby="articles-title"><div class="wrap"><div class="section-header"><div><p class="eyebrow">PLS insights</p><h2 id="articles-title">Accounting and tax articles</h2></div><p>Practical guidance by Dr. Ahmad Helwani, with references to the sources behind each topic.</p></div><div class="articles-grid{' single-article' if len(self.articles)==1 else ''}">{cards}</div><div class="section-action">{link('/articles/','View all PLS articles','button secondary')}</div></div></section>
{self.external_articles()}
<section class="section faq-section" aria-labelledby="faq-title"><div class="wrap faq-grid"><div><p class="eyebrow">Before you get in touch</p><h2 id="faq-title">Accounting and tax questions</h2><p>A few useful details for your first enquiry.</p></div>{self.faq()}</div></section>
<section class="contact-section" id="contact" aria-labelledby="contact-title"><div class="wrap contact-grid"><div><p class="eyebrow">Contact PLS</p><h2 id="contact-title">Discuss your business question</h2><p>Share a short description of your business, the service or question involved, the relevant period and any approaching deadline.</p></div><div class="contact-box">{link('mailto:'+s['email'],s['email'],'email-link','mail')}<p class="contact-phone"><a href="tel:{h(s['telephone'])}">{h(s['phoneDisplay'])}</a></p><p>{h(s['address']['building'])}, {h(s['address']['city'])}, UAE<br>{h(s['businessHours']['display'])}</p><p>Enquiries are welcome in English or Arabic.</p></div></div></section>'''
        return self.page(s['homeTitle'],s['homeDescription'],'/',content,[self.company(),self.person()])

    def service_page(self, path, title, description, lead, body, enquiry_hint, service_types):
        related = ''.join(f'<li>{link(other_path, other_title)}</li>' for other_path, _, other_title in SERVICE_LINKS if other_path != path)
        content = f'''<section class="page-hero service-hero"><div class="wrap"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">PLS Accounting</a><span aria-hidden="true">/</span><a href="/#services">Services</a></nav><p class="eyebrow">Dubai and the UAE</p><h1>{h(title)}</h1><p class="page-lead">{h(lead)}</p><div class="button-row">{link('mailto:'+self.site['email'],'Discuss your requirements','button','mail')}{link('/ahmad-helwani/','Meet Dr. Ahmad','button secondary')}</div></div></section>
<section class="section service-detail-section"><div class="wrap service-layout"><div class="service-copy">{body}<section class="service-section service-professional"><h2>Your adviser</h2><p>Dr. Ahmad Helwani is Managing Partner at PLS Accounting and an FTA Tax Agent for VAT and Corporate Tax with Bonnard Lawson Dubai. Read his <a href="{h(self.site['links']['biography'])}">professional biography</a> for his background and check the <a href="https://tax.gov.ae/en/tax.support/tax.agents/registered.tax.agents.aspx">FTA registered tax-agent directory</a> to verify current registered tax-agent details.</p><p>Enquiries are welcome in English or Arabic. The work, responsibilities and written deliverables are agreed around your business and the records available.</p></section></div><aside class="service-enquiry" aria-labelledby="service-enquiry-title"><p class="eyebrow">Start an enquiry</p><h2 id="service-enquiry-title">Tell us what you need.</h2><p>{h(enquiry_hint)}</p>{link('mailto:'+self.site['email'],self.site['email'],'text-link','mail')}<p class="service-language">English and Arabic enquiries</p><nav class="service-related" aria-label="Other services"><h3>Explore other services</h3><ul>{related}</ul></nav></aside></div></section>'''
        service_id = self.base+path+'#service'
        service = {'@type':'Service','@id':service_id,'name':title,'serviceType':service_types,'description':description,'url':self.base+path,'provider':{'@id':self.base+'/#company'},'areaServed':{'@type':'Country','name':'United Arab Emirates'},'availableLanguage':['English','Arabic']}
        breadcrumb_id = self.base+path+'#breadcrumb'
        breadcrumb = {'@type':'BreadcrumbList','@id':breadcrumb_id,'itemListElement':[
            {'@type':'ListItem','position':1,'name':self.site['name'],'item':self.base+'/'},
            {'@type':'ListItem','position':2,'name':title,'item':self.base+path},
        ]}
        webpage = {'@type':'WebPage','@id':self.base+path+'#page','url':self.base+path,'name':title,'description':description,'mainEntity':{'@id':service_id},'author':{'@id':self.base+'/ahmad-helwani/#person'},'dateModified':SERVICE_MODIFIED[path],'inLanguage':'en','breadcrumb':{'@id':breadcrumb_id}}
        return self.page(title+' | PLS Accounting',description,path,content,[self.company(),self.person(),service,webpage,breadcrumb],active='services')

    def accounting_service(self):
        body = '''<section class="service-section"><h2>Keep your records ready for decisions</h2><p>PLS provides accounting and bookkeeping support for businesses in Dubai and across the UAE. We agree the records, reporting period, transaction volumes and responsibilities before work begins.</p><ul><li><strong>Bookkeeping.</strong> Organise sales, purchases, expenses and supporting documents in the agreed accounting system.</li><li><strong>Reconciliations.</strong> Review bank balances, customer and supplier accounts, and identify missing records or differences.</li><li><strong>Reporting.</strong> Prepare agreed financial reports and explain balances that need management review.</li></ul></section>
<section class="service-section"><h2>What you receive</h2><p>Your scope can include updated ledgers, reconciliation workings, a balance sheet and profit-and-loss report, and a list of outstanding questions. We agree the reporting frequency and review process with your team.</p><p>For software setup or migration, explore our <a href="/services/zoho-books-e-invoicing-uae/">Zoho Books implementation support</a>. VAT and Corporate Tax preparation can be coordinated under an agreed scope.</p></section>
<section class="service-section"><h2>Start with the records available</h2><p>Share your business activity, current software, latest accounts, bank statements and approximate monthly transaction volume. Explain any reporting deadline and who prepares invoices and payments. You can enquire before every document is ready.</p></section>'''
        return self.service_page('/services/accounting-bookkeeping-dubai/','Accounting and Bookkeeping Services in Dubai','Accounting and bookkeeping services in Dubai: ledgers, bank reconciliations, financial reports and Zoho Books support from PLS Accounting.','Bring your business records together with PLS Accounting. We support bookkeeping, reconciliations and financial reporting, with a clear scope and practical information for your team.',body,'Tell us your business activity, current software, monthly transaction volume and reporting needs.',['Bookkeeping','Account reconciliations','Financial reporting'])

    def corporate_tax_service(self):
        body = '''<section class="service-section"><h2>Corporate Tax support from records to return</h2><p>PLS helps businesses prepare for Corporate Tax registration and annual compliance by connecting their accounting records, business activities and supporting documents. An engagement can cover registration, a specific advisory question, annual tax calculations or Corporate Tax return filing support.</p><ul><li><strong>Registration and tax-period review.</strong> Review the entity details, business activities, financial year and existing FTA registration or correspondence.</li><li><strong>Accounts and tax calculations.</strong> Reconcile the trial balance and financial statements, identify relevant accounting-to-tax adjustments and prepare supporting calculations.</li><li><strong>Return preparation and filing support.</strong> Prepare the return information and relevant schedules, review outstanding questions and agree the submission responsibilities and authorisation.</li><li><strong>Transaction-specific advice.</strong> Review the facts behind a deduction, income item, related-party arrangement or proposed transaction. Free-zone, grouping or restructuring questions can be included in an agreed advisory scope.</li></ul></section>
<section class="service-section"><h2>How the engagement works</h2><ol><li><strong>Establish the position.</strong> Confirm the legal entity, tax period, registration status, records available and relevant filing or payment dates.</li><li><strong>Prepare and explain.</strong> Work through the accounts and transaction documents, record the proposed treatment and identify information needed to complete the calculations.</li><li><strong>Review and complete.</strong> Discuss the workings and return information with you, resolve the agreed review points and retain a clear record of the completed work.</li></ol></section>
<section class="service-section"><h2>What you receive</h2><p>The deliverables are set out in the engagement. For annual compliance work, these can include a Corporate Tax computation, supporting adjustment schedules, a return-preparation summary and a list of matters requiring your confirmation. An advisory review provides a written explanation of the question considered, the information reviewed and the recommended next steps.</p></section>
<section class="service-section"><h2>Records for your first discussion</h2><ul><li>Business activities, legal structure, trade licence and financial-year dates.</li><li>Corporate Tax registration details, previous returns and relevant FTA correspondence.</li><li>Available financial statements, trial balance and general ledger.</li><li>Contracts and records for the transactions you want reviewed.</li><li>Details of related parties, other group entities and any proposed changes.</li></ul></section>
<section class="service-section"><h2>Common questions</h2><div class="faq service-faq"><details><summary>Can you work with our existing accountant?</summary><p>Yes. We can agree how the accounting team will provide records, address reconciliation questions and review proposed adjustments. The respective preparation, approval and submission responsibilities are established at the start.</p></details><details><summary>Can I enquire before the accounts are complete?</summary><p>Yes. Share the records available and your financial-year dates. We can identify the information still needed and agree whether accounting preparation, a targeted review or annual filing support is the appropriate starting point.</p></details><details><summary>Can you review one transaction without preparing the whole return?</summary><p>Yes. Describe the transaction, the parties and the question to be resolved. We can agree a separate advisory review and explain how its conclusions should be reflected in the wider accounting or tax process.</p></details></div></section>
<section class="service-section service-resources"><h2>Further guidance</h2><p>The FTA publishes the official <a href="https://tax.gov.ae/en/services/corporate.tax.registration.aspx">Corporate Tax registration requirements</a> and <a href="https://www.tax.gov.ae/Datafolder/Files/Guides/CT/CT-Returns-EN-11-11-2024.pdf">Corporate Tax Return Guide</a>. For specialist advice and practical explanations by Dr. Ahmad Helwani, explore <a href="https://uae-taxes.com/corporate-tax">Corporate Tax advisory on UAE Taxes</a>.</p></section>'''
        return self.service_page('/services/corporate-tax-dubai/','Corporate Tax Advisory and Compliance in Dubai','Corporate Tax registration, advisory, annual calculations and return filing support in Dubai and across the UAE, led by Dr. Ahmad Helwani.','PLS supports businesses in Dubai and across the UAE with Corporate Tax registration, accounting preparation, tax calculations and annual return filing support. Start with your business activities, financial year and the question or filing requirement you need to address.',body,'Include your business activities, financial-year dates, registration status and the Corporate Tax question or filing support you need.',['Corporate Tax registration support','Corporate Tax advisory','Corporate Tax calculations and return filing support'])

    def vat_review_service(self):
        body = '''<section class="service-section"><h2>Review the transaction behind the invoice</h2><p>A VAT question often depends on the contract, what was supplied, the parties involved and the supporting records. PLS combines invoice and transaction reviews with accounting and compliance support so the treatment can be understood and reflected in your records.</p><ul><li><strong>VAT invoice and credit-note reviews.</strong> Check the available document details, supporting records and treatment used in the accounts.</li><li><strong>Transaction analysis.</strong> Review domestic and cross-border transactions, imports, exports, reverse-charge questions and the evidence supporting the proposed VAT treatment.</li><li><strong>Input VAT and reconciliations.</strong> Review purchase records, supporting invoices and the relationship between the ledgers and VAT workings.</li><li><strong>Registration and return filing support.</strong> Review the business activities and registration position, prepare VAT return workings and agree the review and submission process.</li></ul></section>
<section class="service-section"><h2>How a VAT review works</h2><ol><li><strong>Describe the issue.</strong> Identify the invoice or transaction, the relevant period, the parties and the VAT question.</li><li><strong>Bring the records together.</strong> Compare invoices and credit notes with contracts, orders, delivery or service records, payment information and the accounting entries.</li><li><strong>Explain the findings.</strong> Set out the information reviewed, the proposed treatment, any remaining questions and the accounting or compliance actions to consider.</li></ol><p>For ongoing VAT return work, we also agree how sales, purchases, imports and adjustments will be reconciled and reviewed for each relevant VAT period.</p></section>
<section class="service-section"><h2>What you receive</h2><p>A transaction review provides a written explanation of the issue considered, the supporting information reviewed, unresolved information gaps and recommended next steps. Where return preparation forms part of the engagement, the deliverables include the agreed VAT workings and a summary of items requiring your review or confirmation.</p></section>
<section class="service-section"><h2>Useful records to prepare</h2><ul><li>A short description of your business and the supply being reviewed.</li><li>VAT registration details, the relevant period and previous workings where applicable.</li><li>Invoices, credit notes and the related contracts or purchase orders.</li><li>Delivery, service, customs and payment records relevant to the transaction.</li><li>Supplier and customer details, including the countries involved.</li><li>Relevant FTA correspondence or earlier advice on the issue.</li></ul></section>
<section class="service-section"><h2>Common questions</h2><div class="faq service-faq"><details><summary>Can you review a single invoice?</summary><p>Yes. Send a description of the transaction and explain the point you want reviewed. We identify the related documents needed to understand the invoice and its VAT treatment.</p></details><details><summary>Can you help with both registration and VAT returns?</summary><p>Yes. The scope can include a registration-position review, preparation of the required information and VAT return workings. We confirm the relevant periods, review responsibilities and submission arrangements for the engagement.</p></details><details><summary>Can our bookkeeping team use the findings?</summary><p>Yes. A written review can identify the records, tax coding or reconciliations that need attention. We can agree how to coordinate the resulting actions with your accountant or bookkeeping team.</p></details></div></section>
<section class="service-section service-resources"><h2>Further guidance</h2><p>The FTA's <a href="https://tax.gov.ae/en/taxes/Vat/vat.topics.aspx">VAT Topics</a> and <a href="https://tax.gov.ae/en/taxes/Vat/elearning.aspx">VAT learning resources</a> provide official guidance. For specialist VAT advice and Dr. Ahmad Helwani's approach to transaction reviews, explore <a href="https://uae-taxes.com/vat">VAT advisory on UAE Taxes</a>.</p></section>'''
        return self.service_page('/services/vat-reviews-dubai/','VAT Registration, Returns and Reviews in Dubai','VAT registration, return preparation and filing support, plus invoice and transaction reviews for businesses in Dubai and across the UAE.','PLS supports Dubai and UAE businesses with VAT registration, VAT return preparation and filing support, and invoice and transaction reviews. We examine the transaction and its supporting records, explain the review findings and agree the next steps with your team.',body,'Describe the VAT question, relevant period and transaction. Explain which invoices, contracts and accounting records are available.',['VAT invoice and transaction reviews','VAT registration support','VAT return preparation and filing support'])

    def zoho_readiness_service(self):
        body = '''<section class="service-section"><h2>Connect the software with the accounting work</h2><p>As a Zoho partner, PLS helps businesses set up and use Zoho Books for invoicing, bookkeeping and financial reporting. The work starts with how your business operates: who prepares invoices, which records are available, how payments are reconciled and what your team needs to review.</p><ul><li><strong>Zoho Books setup.</strong> Configure the chart of accounts, opening balances, customer and supplier records, items and relevant accounting settings.</li><li><strong>Invoicing workflows.</strong> Review invoice information, credit notes, approval responsibilities, payment records and the connection to the ledger.</li><li><strong>Migration and reconciliation.</strong> Plan the transfer of agreed records from an existing system or spreadsheets, then review opening balances and imported information.</li><li><strong>Bookkeeping and team support.</strong> Agree the ongoing recordkeeping, reconciliations, reporting and user guidance your business needs.</li></ul></section>
<section class="service-section"><h2>Prepare for UAE e-invoicing</h2><p>The UAE framework uses structured invoice data exchanged electronically through Accredited Service Providers, with tax data reported to the FTA. A PDF or scanned invoice alone does not meet the Ministry of Finance's e-invoice definition. <a href="https://mof.gov.ae/en/about-us/initiatives/einvoicing/">MoF eInvoicing portal</a></p><p>PLS can review your transaction types and implementation phase, identify invoice-data gaps and coordinate the accounting workflow with your chosen provider. We confirm the relevant software edition, available functions and provider arrangements before agreeing the implementation steps.</p><p>For the current phases, October 2026 changes and a practical checklist, read <a href="/articles/uae-e-invoicing-are-you-ready/">UAE E-Invoicing: Are You Ready?</a></p></section>
<section class="service-section"><h2>A practical implementation process</h2><ol><li><strong>Review the current setup.</strong> Understand your software, transaction volumes, invoicing process and records.</li><li><strong>Configure and prepare.</strong> Agree the settings, data cleanup, migration work and responsibilities needed for the chosen scope.</li><li><strong>Test the workflow.</strong> Trace outgoing and incoming invoices, credit notes, corrections and rejection handling through the provider connection and accounting entries.</li><li><strong>Hand over and support.</strong> Explain the agreed workflow to your team, record outstanding actions and establish the ongoing bookkeeping or review arrangements.</li></ol></section>
<section class="service-section"><h2>What you receive</h2><p>The agreed work can include a configuration record, migration and reconciliation workings, an invoice-data action list and an implementation plan with named responsibilities. We agree how testing results, remaining questions and user guidance will be documented before completion.</p></section>
<section class="service-section"><h2>Information for your first enquiry</h2><ul><li>Your business activities and approximate annual revenue.</li><li>The accounting software and edition you currently use.</li><li>Approximate invoice volumes and the main types of customer and supplier transactions.</li><li>Sample invoice and credit-note formats, with an explanation of the current approval process.</li><li>Any selected ASP, planned implementation date and migration requirements.</li></ul></section>
<section class="service-section"><h2>Common questions</h2><div class="faq service-faq"><details><summary>How does PLS work with our service provider?</summary><p>PLS supports accounting setup, data preparation and workflow review. Your selected Accredited Service Provider performs the required electronic exchange and reporting functions. We coordinate the responsibilities and testing relevant to the agreed project.</p></details><details><summary>Do we need to replace our accounting software?</summary><p>We first review your current system, available features and provider connection. That review informs whether configuration, a different edition or migration should form part of the project.</p></details><details><summary>Can you provide bookkeeping after setup?</summary><p>Yes. Ongoing bookkeeping, reconciliations and reporting can be included in a separate or continuing agreed scope, with clear responsibility for the records and reviews needed each period.</p></details></div></section>
<section class="service-section service-resources"><h2>Further guidance</h2><p>Visit the <a href="https://mof.gov.ae/en/about-us/initiatives/einvoicing/">Ministry of Finance eInvoicing portal</a> for official system and provider information. Zoho publishes its current UAE product information on the <a href="https://www.zoho.com/ae/books/">Zoho Books website</a>.</p></section>'''
        return self.service_page('/services/zoho-books-e-invoicing-uae/','Zoho Books and UAE E-Invoicing Readiness','Zoho Books setup, migration, invoicing workflows and UAE e-invoicing readiness support from PLS Accounting, a Zoho partner in Dubai.','As a Zoho partner, PLS supports Zoho Books setup, invoicing workflows and ongoing bookkeeping. We help businesses in Dubai and across the UAE prepare their invoice data and accounting processes for e-invoicing and coordinate with their chosen Accredited Service Provider.',body,'Include your business activities, approximate revenue, current accounting software and the setup or e-invoicing support you need.',['Zoho Books setup and migration','Accounting and invoicing workflows','UAE e-invoicing readiness support'])

    def profile(self):
        s, urls = self.site, self.site['links']
        content = f'''<section class="page-hero profile-page-hero"><div class="wrap"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">PLS Accounting</a><span aria-hidden="true">/</span><span>Professional profile</span></nav><div class="profile-hero-grid"><div class="profile-hero-copy"><p class="eyebrow">Managing Partner, PLS Accounting · Tax Agent, Bonnard Lawson Dubai</p><h1>Dr. Ahmad Helwani</h1><p class="page-lead">{h(s['biography'])}</p><div class="button-row">{link('mailto:'+s['email'],'Discuss your requirements','button','mail')}{link(urls['taxes'],'Explore UAE Taxes','button secondary','external')}</div></div><figure class="profile-hero-portrait"><img class="adviser-portrait" src="/assets/ahmad-helwani-profile-approved.png" width="1122" height="1402" alt="Dr. Ahmad Helwani, Managing Partner of PLS Accounting, in a modern office" decoding="async" fetchpriority="high"></figure></div></div></section>
<section class="section"><div class="wrap profile-detail"><div class="profile-main"><section class="detail-block"><h2>Professional roles and background</h2><p>At PLS Accounting, Ahmad supports businesses with accounting, bookkeeping, financial reporting and Zoho-based processes. PLS is a Zoho partner, providing Zoho Books setup and UAE e-invoicing readiness support.</p><p>His VAT and Corporate Tax tax-agent role is with Bonnard Lawson Dubai. The engagement identifies the relevant service provider, responsibilities and any required FTA appointment arrangements.</p><p>His <a href="{h(urls['biography'])}">Bonnard Lawson professional biography</a> describes his education, professional memberships and experience across healthcare, real estate and industrial businesses. Current registered tax-agent details can be checked through the <a href="{h(urls['ftaDirectory'])}">FTA directory</a>.</p></section><section class="detail-block"><h2>Tax and accounting support</h2><div class="profile-services"><article><h3>Corporate Tax advisory and filing</h3><p>Registration, review of accounting-to-tax adjustments, annual computations, return preparation and filing support.</p>{link('/services/corporate-tax-dubai/','Explore Corporate Tax services')}</article><article><h3>VAT returns and transaction reviews</h3><p>Registration and return support, with invoice and transaction reviews explaining the records, proposed treatment and next steps.</p>{link('/services/vat-reviews-dubai/','Explore VAT services')}</article><article><h3>Zoho Books and e-invoicing</h3><p>Accounting setup, migration, invoicing workflows, reconciliations and preparation for coordination with an Accredited Service Provider.</p>{link('/services/zoho-books-e-invoicing-uae/','Explore Zoho and e-invoicing support')}</article></div></section><section class="detail-block"><h2>Education and working languages</h2><ul><li>Doctor of Business Administration, SBS Swiss Business School (2023).</li><li>Master of Applied Business Research, SBS Swiss Business School.</li><li>Master of Business Administration, major in Banking and Finance, Geneva Business School.</li><li>English and Arabic.</li></ul></section><section class="detail-block"><h2>Prepare for a discussion</h2><p>Describe your business activity, the service you need, the relevant period and any approaching deadline. Explain which accounts, invoices, contracts or other supporting records are available. You can enquire before every document has been gathered.</p>{link('mailto:'+s['email'],s['email'],'button','mail')}</section></div><aside class="profile-sidebar" aria-labelledby="references-title"><p class="eyebrow">Professional references</p><h2 id="references-title">Work and background</h2><p>Explore the professional biography, registered-agent verification route and practical guidance.</p><ul><li>{link(urls['biography'],'Bonnard Lawson biography',glyph='external')}</li><li>{link(urls['ftaDirectory'],'FTA tax-agent directory',glyph='external')}</li><li>{link(urls['linkedin'],'LinkedIn profile',glyph='external')}</li><li>{link(urls['taxes'],'UAE Taxes',glyph='external')}</li><li>{link('/articles/','PLS articles')}</li></ul><p class="sidebar-note">English &amp; Arabic enquiries<br><a href="mailto:{h(s['email'])}">{h(s['email'])}</a></p></aside></div></section>'''
        profile = {"@type":"ProfilePage","@id":self.base+'/ahmad-helwani/#profile',"url":self.base+'/ahmad-helwani/',"name":"Dr. Ahmad Helwani | PLS Accounting","mainEntity":{"@id":self.base+'/ahmad-helwani/#person'}}
        return self.page('Dr. Ahmad Helwani | UAE Tax Agent & PLS Accounting','Dr. Ahmad Helwani, FTA Tax Agent for VAT and Corporate Tax with Bonnard Lawson Dubai and Managing Partner of PLS Accounting. English and Arabic enquiries.','/ahmad-helwani/',content,[self.company(),self.person(),profile],active='profile')

    def article_index(self):
        cards = ''.join(self.article_card(a,len(self.articles)==1) for a in self.articles)
        if not cards:
            cards='<p>Explore the existing articles on UAE Taxes below.</p>'
        content=f'''<section class="page-hero"><div class="wrap"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">PLS Accounting</a><span aria-hidden="true">/</span><span>Articles</span></nav><p class="eyebrow">PLS insights</p><h1>Accounting and tax articles</h1><p class="page-lead">Practical UAE guidance by Dr. Ahmad Helwani, with clear authorship and references to primary sources.</p></div></section><section class="section"><div class="wrap"><div class="articles-grid{' single-article' if len(self.articles)==1 else ''}">{cards}</div></div></section>{self.external_articles()}'''
        collection={"@type":"CollectionPage","@id":self.base+'/articles/#page',"url":self.base+'/articles/',"name":"Accounting and tax articles","mainEntity":{"@type":"ItemList","itemListElement":[{"@type":"ListItem","position":i,"url":self.base+'/articles/'+a['slug']+'/','name':a['title']} for i,a in enumerate(self.articles,1)]}}
        return self.page('Accounting & Tax Articles | PLS Accounting','Read practical UAE accounting and tax articles by Dr. Ahmad Helwani, including e-invoicing readiness and referenced guidance for businesses.','/articles/',content,[self.company(),self.person(),collection],active='articles')

    def article_page(self, article):
        path=f'/articles/{article["slug"]}/'
        body=(ROOT/article['bodyFragment']).read_text(encoding='utf-8')
        actual=published_time(article)
        image=self.base+'/'+article['coverImage']
        updated = ''
        if article.get('dateModified') and parse_time(article['dateModified']) > actual:
            modified = parse_time(article['dateModified'])
            modified_label = f"{modified.day} {modified.strftime('%B %Y')}"
            updated = f'<small class="article-updated">Updated <time datetime="{h(modified.isoformat())}">{h(modified_label)}</time></small>'
        content=f'''<article class="article-page"><header class="article-header"><div class="reading-wrap"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">PLS Accounting</a><span aria-hidden="true">/</span><a href="/articles/">Articles</a></nav><p class="eyebrow">UAE accounting &amp; tax insights</p><h1>{h(article['title'])}</h1><p class="article-deck">{h(article['description'])}</p><div class="article-byline"><span>By <a href="/ahmad-helwani/">Dr. Ahmad Helwani</a><small>Managing Partner, PLS Accounting</small></span><span>Published <time datetime="{h(actual.isoformat())}">{h(publication_label(article))}</time>{updated}</span></div></div></header><figure class="article-cover reading-wide"><img src="/{h(article['coverImage'])}" width="{article['imageWidth']}" height="{article['imageHeight']}" alt="{h(article['imageAlt'])}" fetchpriority="high"><figcaption>{h(article['imageCaption'])}</figcaption></figure><div class="article-body reading-wrap">{body}</div><footer class="article-end reading-wrap"><p class="eyebrow">About the author</p><h2>Dr. Ahmad Helwani</h2><p>{h(self.site['biography'])}</p>{link('/ahmad-helwani/','View professional profile')}<div class="article-return">{link('/articles/','More PLS articles')}{link(self.site['links']['taxArticles'],'Read more articles on UAE Taxes',glyph='external')}</div></footer></article>'''
        posting={"@type":"BlogPosting","@id":self.base+path+'#article',"headline":article['title'],"description":article['description'],"url":self.base+path,"mainEntityOfPage":{"@type":"WebPage","@id":self.base+path},"datePublished":actual.isoformat(),"dateModified":article.get('dateModified',actual.isoformat()),"author":{"@id":self.base+'/ahmad-helwani/#person'},"publisher":{"@id":self.base+'/#company'},"image":{"@type":"ImageObject","url":image,"width":article['imageWidth'],"height":article['imageHeight']},"inLanguage":"en","isAccessibleForFree":True,"citation":article['sourceLinks']}
        page_title = article['title'] + ' | PLS Accounting'
        if len(page_title) > 70:
            page_title = article['title']
        return self.page(page_title,article['description'],path,content,[self.company(),self.person(),posting],active='articles',image=image,image_alt=article['imageAlt'],article=True)

    def not_found(self):
        content=f'''<section class="section not-found"><div class="wrap"><p class="eyebrow">Page not found</p><h1>Let’s get you back on track.</h1><p>The page you’re looking for may have moved. Explore PLS’s services or browse our latest articles.</p><div class="button-row">{link('/','Return home','button')}{link('/articles/','Browse articles','button secondary')}</div></div></section>'''
        return self.page('Page Not Found | PLS Accounting','Return to PLS Accounting’s services, professional profile and UAE tax articles.','/404.html',content,noindex=True)

    def build(self, output):
        output=output.resolve()
        # The builder never deletes or replaces a source directory, even if a bad output is supplied.
        if output == ROOT or output in ROOT.parents or (ROOT in output.parents and output != ROOT/'public') or output.name != 'public':
            raise ValueError('Output must be a directory named public, separate from all source directories.')
        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True)
        (output/'assets').mkdir()
        for filename in ['pls-logo.png','pls-logo-compact.jpg','ahmad-helwani-home-approved.png','ahmad-helwani-profile-approved.png','site.css','site.js']:
            shutil.copy2(ROOT/'assets'/filename,output/'assets'/filename)
        for filename, asset_url in self.asset_urls.items():
            shutil.copy2(ROOT/'assets'/filename, output/asset_url.lstrip('/'))
        for client in self.site.get('clients', []):
            logo = self.client_logo_path(client)
            if logo:
                target = output / logo
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / logo, target)
        pages={'index.html':self.home(),'ahmad-helwani/index.html':self.profile(),'articles/index.html':self.article_index(),'404.html':self.not_found(),
               'services/accounting-bookkeeping-dubai/index.html':self.accounting_service(),
               'services/corporate-tax-dubai/index.html':self.corporate_tax_service(),
               'services/vat-reviews-dubai/index.html':self.vat_review_service(),
               'services/zoho-books-e-invoicing-uae/index.html':self.zoho_readiness_service()}
        if self.site.get('clients'):
            pages['clients/index.html'] = self.clients_page()
        for article in self.articles:
            for filename,hash_key in [('bodyFragment','bodyFragmentSha256'),('coverImage','coverImageSha256')]:
                source=(ROOT/article[filename]).resolve()
                if ROOT not in source.parents:
                    raise ValueError('Article source paths must remain within the repository.')
                if hashlib.sha256(source.read_bytes()).hexdigest()!=article[hash_key]:
                    raise ValueError(f'Approved content hash mismatch: {article["id"]} {filename}')
            target=output/article['coverImage']
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/article['coverImage'],target)
            pages[f'articles/{article["slug"]}/index.html']=self.article_page(article)
        for filename,html in pages.items():
            destination=output/filename
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(html,encoding='utf-8')
        locations=[('/',None),('/ahmad-helwani/',None),('/articles/',None)]+[(path,SERVICE_MODIFIED[path]) for path,_,_ in SERVICE_LINKS]+[(f'/articles/{a["slug"]}/',parse_time(a.get('dateModified',published_time(a).isoformat())).date().isoformat()) for a in self.articles]
        if self.site.get('clients'):
            locations.append(('/clients/', '2026-10-30'))
        sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{h(self.base+path)}</loc>{"<lastmod>"+date+"</lastmod>" if date else ""}</url>\n' for path,date in locations)+'</urlset>\n'
        (output/'sitemap.xml').write_text(sitemap,encoding='utf-8')
        (output/'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nUser-agent: OAI-SearchBot\nAllow: /\n\nSitemap: {self.base}/sitemap.xml\n',encoding='utf-8')
        (output/'_headers').write_text('/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  X-Frame-Options: SAMEORIGIN\n\n/assets/*\n  Cache-Control: public, max-age=86400\n',encoding='utf-8')
        report={'buildAt':self.at.isoformat(),'canonicalBase':self.base,'includedArticles':[a['id'] for a in self.articles],'excludedArticles':self.excluded,'output':str(output),'htmlPages':len(pages)}
        (ROOT/'build-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(f'Built {len(pages)} pages and {len(self.articles)} eligible article(s) in {output.name}/.')
        return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--at',help='Timezone-aware ISO timestamp for isolated release-boundary checks. Omit in production.')
    parser.add_argument('--output',type=Path,default=ROOT/'public',help='Destination directory (must be named public).')
    args=parser.parse_args()
    at=parse_time(args.at) if args.at else datetime.now(timezone.utc)
    Builder(at).build(args.output)


if __name__=='__main__':
    main()
