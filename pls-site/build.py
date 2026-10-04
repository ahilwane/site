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
            "sameAs": [self.site["links"]["biography"], self.site["links"]["linkedin"]],
        }

    def header(self, active):
        profile_current = ' aria-current="page"' if active == "profile" else ""
        articles_current = ' aria-current="page"' if active == "articles" else ""
        return f'''<a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="wrap nav-wrap">
<a class="brand" href="/" aria-label="PLS Accounting home"><img src="/assets/pls-logo-compact.jpg" width="569" height="154" alt="PLS Accounting"></a>
<button class="nav-toggle" type="button" aria-controls="site-navigation" aria-expanded="false" aria-label="Open navigation">{icon('menu')}</button>
<nav class="nav" id="site-navigation" aria-label="Main navigation"><a href="/#services">Services</a><a href="/ahmad-helwani/"{profile_current}>Dr. Ahmad Helwani</a><a href="/articles/"{articles_current}>Articles</a><a class="nav-contact" href="/#contact">Contact</a></nav>
</div></header>'''

    def footer(self):
        return f'''<footer class="site-footer"><div class="wrap"><div class="footer-grid"><div class="footer-brand"><a href="/" aria-label="PLS Accounting home"><img src="/assets/pls-logo.png" width="570" height="183" alt="PLS Accounting — Prime Ledger Solution for Accounting Services" loading="lazy"></a></div><nav class="footer-links" aria-label="Footer navigation"><a href="/#services">Services</a><a href="/ahmad-helwani/">Dr. Ahmad Helwani</a><a href="/articles/">Articles</a><a href="{h(self.site['links']['taxes'])}">UAE Taxes</a><a href="mailto:{h(self.site['email'])}">Email PLS</a></nav></div><div class="footer-base"><p>© {self.at.year} PLS Accounting. All rights reserved.</p><p>Prime Ledger Solution for Accounting Services</p></div></div></footer>'''

    def page(self, title, description, path, content, graph=None, active="", image=None, image_alt="PLS Accounting logo", article=False, noindex=False):
        url = self.base + path
        image = image or self.base + "/assets/pls-logo.png"
        canonical = "" if noindex else f'<link rel="canonical" href="{h(url)}">'
        robots = '<meta name="robots" content="noindex, follow">' if noindex else ""
        graph = graph or [self.company()]
        structured = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("<", "\\u003c")
        return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)}</title><meta name="description" content="{h(description)}"><meta name="theme-color" content="#303e9d">{canonical}{robots}
<meta property="og:type" content="{'article' if article else 'website'}"><meta property="og:title" content="{h(title)}"><meta property="og:description" content="{h(description)}"><meta property="og:url" content="{h(url)}"><meta property="og:image" content="{h(image)}"><meta property="og:image:alt" content="{h(image_alt)}"><meta property="og:site_name" content="PLS Accounting"><meta name="twitter:card" content="{'summary_large_image' if article else 'summary'}">
<link rel="icon" href="/assets/pls-logo.png" type="image/png"><link rel="stylesheet" href="/assets/site.css"><script src="/assets/site.js" defer></script>
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
        services = "".join(f'''<article class="service-card"><div class="service-top"><span class="service-icon">{icon(item['icon'])}</span><span class="service-number">0{i}</span></div><h3>{h(item['title'])}</h3><p>{h(item['text'])}</p><ul class="service-tags">{''.join(f'<li>{h(tag)}</li>' for tag in item['tags'])}</ul></article>''' for i,item in enumerate(s['services'],1))
        cards = "".join(self.article_card(a,len(self.articles)==1) for a in self.articles)
        if not cards:
            cards = '<p>Explore Dr. Ahmad Helwani’s existing articles on <a href="https://uae-taxes.com/tax-insights">UAE Taxes</a>.</p>'
        content = f'''<section class="hero" aria-labelledby="hero-title"><div class="wrap hero-grid"><div class="hero-copy"><p class="eyebrow">Prime Ledger Solution for Accounting Services</p><h1 id="hero-title">{h(s['heroTitle'])}</h1><p class="hero-intro">{h(s['heroIntro'])}</p><div class="button-row">{link('/#services','Explore our services','button')}{link('/ahmad-helwani/','Meet Dr. Ahmad','button secondary')}</div><p class="hero-note">{icon('globe')}UAE business support · English &amp; Arabic enquiries</p></div><div class="hero-art"><p class="art-label">A considered approach</p><div class="document"><div class="document-heading"><span class="document-symbol">{icon('ledger')}</span><p class="eyebrow">From records to decisions</p><h2>Bring the details together.</h2></div><div class="document-row"><span>01</span><div><strong>Understand your records</strong><small>Accounts, invoices &amp; supporting documents</small></div></div><div class="document-row"><span>02</span><div><strong>Clarify the question</strong><small>Business context &amp; information gaps</small></div></div><div class="document-row"><span>03</span><div><strong>Identify the next step</strong><small>A scope shaped around your needs</small></div></div><div class="document-footer">PLS Accounting <span>Records → context → decisions</span></div></div></div></div></section>
<div class="intro-band"><div class="wrap intro-grid"><div>{icon('ledger')}<span><strong>Accounting &amp; bookkeeping</strong><small>Organised records and useful information</small></span></div><div>{icon('document')}<span><strong>VAT &amp; Corporate Tax</strong><small>Guidance by Dr. Ahmad Helwani</small></span></div><div>{icon('globe')}<span><strong>English &amp; Arabic</strong><small>Enquiries in either language</small></span></div></div></div>
<section class="section" id="services" aria-labelledby="services-title"><div class="wrap"><div class="section-header"><div><p class="eyebrow">How we can help</p><h2 id="services-title">Accounting and business services in the UAE</h2></div><p>Start with the question you need to answer. We can discuss the information available and the support that fits your requirements.</p></div><div class="services-grid">{services}</div><p class="services-note">For specialist tax guidance, explore Dr. Ahmad Helwani’s <a href="{urls['vat']}">VAT reviews</a> and <a href="{urls['corporateTax']}">Corporate Tax guidance</a> on UAE Taxes.</p></div></section>
<section class="section profile-section" aria-labelledby="profile-title"><div class="wrap profile-grid"><div class="profile-panel"><img src="/assets/pls-logo.png" width="570" height="183" alt="PLS Accounting — Prime Ledger Solution for Accounting Services" loading="lazy"><div><p class="eyebrow">Managing Partner</p><h3>Dr. Ahmad Helwani</h3><p>UAE accounting, finance &amp; tax</p><span class="language">{icon('globe')} English &amp; Arabic</span></div></div><div class="profile-copy"><p class="eyebrow">Meet Dr. Ahmad Helwani</p><h2 id="profile-title">Experience with the details that matter.</h2><p>{h(s['biography'])}</p><p>Through UAE Taxes, he shares practical guidance on VAT and Corporate Tax questions.</p>{link('/ahmad-helwani/','Explore his professional profile')}<div class="profile-links">{link(urls['biography'],'Professional biography',glyph='external')}{link(urls['linkedin'],'LinkedIn profile',glyph='external')}</div></div></div></section>
<section class="section" id="approach" aria-labelledby="approach-title"><div class="wrap"><div class="section-header"><div><p class="eyebrow">Start with your business question</p><h2 id="approach-title">Context first. Then the detail.</h2></div><p>A useful first discussion starts with your business, the question you are facing and the records available.</p></div><div class="process-grid"><article class="process-step"><span class="step-number">01</span><h3>Describe the question</h3><p>Share a short business overview, the relevant period and the issue you want to discuss.</p></article><article class="process-step"><span class="step-number">02</span><h3>Identify the records</h3><p>Explain which accounts, invoices or supporting documents are available and what information is still missing.</p></article><article class="process-step"><span class="step-number">03</span><h3>Discuss the scope</h3><p>Agree what needs to be reviewed and the next information to gather before an engagement begins.</p></article></div></div></section>
<section class="section tax-section" aria-labelledby="tax-title"><div class="wrap tax-grid"><div class="tax-copy"><p class="eyebrow">Dr. Ahmad’s UAE tax guidance</p><h2 id="tax-title">A question about VAT or Corporate Tax?</h2><p>Dr. Ahmad Helwani’s UAE Taxes website explains his tax guidance and document review services. Explore the relevant service page and prepare a short summary of your question.</p><p>For VAT reviews, relevant records may include invoices, credit notes, contracts, purchase orders and payment information.</p><div class="button-row">{link(urls['vat'],'Explore VAT reviews','button secondary','external')}{link(urls['corporateTax'],'Corporate Tax guidance','text-link','external')}</div></div><div class="deliverable"><p class="eyebrow">What you receive from a VAT review</p><h3>A written explanation and next steps.</h3><p>{h(s['vatDeliverable'])}</p><ul><li>{icon('check')}The issue and information reviewed</li><li>{icon('check')}Any unresolved information gaps</li><li>{icon('check')}Recommended next steps</li></ul></div></div></section>
<section class="section" id="articles" aria-labelledby="articles-title"><div class="wrap"><div class="section-header"><div><p class="eyebrow">PLS insights</p><h2 id="articles-title">Accounting and tax articles</h2></div><p>Practical guidance by Dr. Ahmad Helwani, with references to the sources behind each topic.</p></div><div class="articles-grid{' single-article' if len(self.articles)==1 else ''}">{cards}</div><div class="section-action">{link('/articles/','View all PLS articles','button secondary')}</div></div></section>
{self.external_articles()}
<section class="section faq-section" aria-labelledby="faq-title"><div class="wrap faq-grid"><div><p class="eyebrow">Before you get in touch</p><h2 id="faq-title">Accounting and tax questions</h2><p>A few useful details for your first enquiry.</p></div>{self.faq()}</div></section>
<section class="contact-section" id="contact" aria-labelledby="contact-title"><div class="wrap contact-grid"><div><p class="eyebrow">Contact PLS</p><h2 id="contact-title">Discuss your business question</h2><p>Share a short description of your business, the service or question involved, the relevant period and any approaching deadline.</p></div><div class="contact-box">{link('mailto:'+s['email'],s['email'],'email-link','mail')}<p>Enquiries are welcome in English or Arabic.</p></div></div></section>'''
        return self.page(s['homeTitle'],s['homeDescription'],'/',content,[self.company(),self.person()])

    def profile(self):
        s, urls = self.site,self.site['links']
        content = f'''<section class="page-hero"><div class="wrap"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">PLS Accounting</a><span aria-hidden="true">/</span><span>Professional profile</span></nav><p class="eyebrow">Managing Partner · PLS Accounting</p><h1>Dr. Ahmad Helwani</h1><p class="page-lead">{h(s['biography'])}</p><div class="button-row">{link('mailto:'+s['email'],'Discuss your question','button','mail')}{link(urls['taxes'],'Explore UAE Taxes','button secondary','external')}</div></div></section>
<section class="section"><div class="wrap profile-detail"><div class="profile-main"><section class="detail-block"><h2>Professional background</h2><p>{h(s['biography'])}</p><p>Through <a href="{urls['taxes']}">UAE Taxes</a>, he shares practical explanations of tax topics and provides information about VAT and Corporate Tax guidance. His <a href="{urls['biography']}">professional biography on Bonnard Lawson</a> provides further details of his background.</p><p>PLS Accounting provides accounting and bookkeeping, financial advisory and business consulting support in the UAE. Explore the <a href="/#services">company’s services</a> alongside Dr. Ahmad’s tax guidance.</p></section><section class="detail-block"><h2>Tax guidance and reviews</h2><p>Start with your business activity, the relevant period and the question you want to answer. Available records help establish the facts and identify missing information.</p><div class="profile-services"><article><h3>VAT invoice and transaction reviews</h3><p>A useful VAT review considers the transaction and available supporting records, and identifies information that is still needed.</p>{link(urls['vat'],'VAT guidance and reviews',glyph='external')}</article><article><h3>Corporate Tax questions</h3><p>Start with your business activity, financial year, registration status and the question you want to resolve.</p>{link(urls['corporateTax'],'Corporate Tax guidance',glyph='external')}</article></div><div class="deliverable"><p class="eyebrow">What you receive from a VAT review</p><h3>A written explanation and next steps.</h3><p>{h(s['vatDeliverable'])}</p></div></section><section class="detail-block"><h2>Prepare for a discussion</h2><p>Describe the issue and the records currently available. You can enquire before every document has been gathered. Mention the relevant period and any approaching deadline.</p><p>For a VAT transaction question, useful records may include the invoice or credit note, relevant contracts, purchase orders, payment records and details of the supplier and customer.</p>{link('mailto:'+s['email'],s['email'],'button','mail')}</section></div><aside class="profile-sidebar" aria-labelledby="references-title"><p class="eyebrow">Explore further</p><h2 id="references-title">Work and background</h2><p>Service information and professional profiles.</p><ul><li>{link(urls['biography'],'Professional biography',glyph='external')}</li><li>{link(urls['linkedin'],'LinkedIn profile',glyph='external')}</li><li>{link(urls['taxes'],'UAE Taxes',glyph='external')}</li><li>{link('/articles/','PLS articles')}</li></ul><p class="sidebar-note">English &amp; Arabic enquiries<br><a href="mailto:{h(s['email'])}">{h(s['email'])}</a></p></aside></div></section>'''
        profile = {"@type":"ProfilePage","@id":self.base+'/ahmad-helwani/#profile',"url":self.base+'/ahmad-helwani/',"name":"Dr. Ahmad Helwani | PLS Accounting","mainEntity":{"@id":self.base+'/ahmad-helwani/#person'}}
        return self.page('Dr. Ahmad Helwani | Managing Partner | PLS Accounting','Dr. Ahmad Helwani, Managing Partner at PLS Accounting, brings over fifteen years of UAE accounting, finance and tax experience. Explore his background and guidance.','/ahmad-helwani/',content,[self.company(),self.person(),profile],active='profile')

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
        content=f'''<article class="article-page"><header class="article-header"><div class="reading-wrap"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">PLS Accounting</a><span aria-hidden="true">/</span><a href="/articles/">Articles</a></nav><p class="eyebrow">UAE accounting &amp; tax insights</p><h1>{h(article['title'])}</h1><p class="article-deck">{h(article['description'])}</p><div class="article-byline"><span>By <a href="/ahmad-helwani/">Dr. Ahmad Helwani</a><small>Managing Partner, PLS Accounting</small></span><span>Published <time datetime="{h(actual.isoformat())}">{h(publication_label(article))}</time></span></div></div></header><figure class="article-cover reading-wide"><img src="/{h(article['coverImage'])}" width="{article['imageWidth']}" height="{article['imageHeight']}" alt="{h(article['imageAlt'])}" fetchpriority="high"><figcaption>{h(article['imageCaption'])}</figcaption></figure><div class="article-body reading-wrap">{body}</div><footer class="article-end reading-wrap"><p class="eyebrow">About the author</p><h2>Dr. Ahmad Helwani</h2><p>{h(self.site['biography'])}</p>{link('/ahmad-helwani/','View professional profile')}<div class="article-return">{link('/articles/','More PLS articles')}{link(self.site['links']['taxArticles'],'Read more articles on UAE Taxes',glyph='external')}</div></footer></article>'''
        posting={"@type":"BlogPosting","@id":self.base+path+'#article',"headline":article['title'],"description":article['description'],"url":self.base+path,"mainEntityOfPage":{"@type":"WebPage","@id":self.base+path},"datePublished":actual.isoformat(),"dateModified":article.get('dateModified',actual.isoformat()),"author":{"@id":self.base+'/ahmad-helwani/#person'},"publisher":{"@id":self.base+'/#company'},"image":{"@type":"ImageObject","url":image,"width":article['imageWidth'],"height":article['imageHeight']},"inLanguage":"en","isAccessibleForFree":True,"citation":article['sourceLinks']}
        return self.page(article['title']+' | PLS Accounting',article['description'],path,content,[self.company(),self.person(),posting],active='articles',image=image,image_alt=article['imageAlt'],article=True)

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
        for filename in ['pls-logo.png','pls-logo-compact.jpg','site.css','site.js']:
            shutil.copy2(ROOT/'assets'/filename,output/'assets'/filename)
        pages={'index.html':self.home(),'ahmad-helwani/index.html':self.profile(),'articles/index.html':self.article_index(),'404.html':self.not_found()}
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
        locations=[('/',None),('/ahmad-helwani/',None),('/articles/',None)]+[(f'/articles/{a["slug"]}/',published_time(a).date().isoformat()) for a in self.articles]
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
