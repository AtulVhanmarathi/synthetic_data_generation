"""
PlaneSense.com Web Scraper
Extracts structured data from all main and sub-pages.
Excludes careers section. Downloads images locally.
"""

import json
import os
import re
import time
import random
import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://www.planesense.com"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
DATA_DIR = os.path.join(OUTPUT_DIR, "data")
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")

SITEMAPS = [
    f"{BASE_URL}/page-sitemap.xml",
    f"{BASE_URL}/post-sitemap.xml",
]

# Patterns to exclude (careers section)
EXCLUDE_PATTERNS = [
    "/careers/",
    "/careers",
    "/pilot-careers/",
    "/veteran-career-opportunities/",
    "/aircraft-maintenance-and-support-careers/",
]

DELAY_MIN = 3  # seconds
DELAY_MAX = 5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("planesense_scraper")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

session = requests.Session()
session.headers.update(HEADERS)


def polite_delay():
    """Sleep for a random duration between DELAY_MIN and DELAY_MAX."""
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def fetch(url: str, retries: int = 3) -> requests.Response | None:
    """Fetch a URL with retries."""
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, retries, url, exc)
            if attempt < retries:
                time.sleep(2 * attempt)
    return None


def categorize_url(url: str) -> str:
    """Assign a category based on URL path."""
    path = urlparse(url).path.lower()
    if path in ("/", ""):
        return "home"
    if "/your-fleet/" in path or "pc-12" in path or "pc-24" in path or "pc24" in path or "pc12" in path:
        return "fleet"
    if "/program-options/" in path or "cobaltpass" in path or "fractional-program" in path:
        return "programs"
    if "/why-fly-planesense/" in path:
        return "why_planesense"
    if "/blog/" in path:
        return "blog"
    if path in ("/contact/", "/legal/", "/privacy/", "/sitemap/"):
        return "utility"
    # Blog posts are generally long-path pages from the post sitemap
    return "content"


def safe_filename(url: str, ext: str = "") -> str:
    """Create a filesystem-safe filename from a URL."""
    name = urlparse(url).path.strip("/").replace("/", "_") or "index"
    name = re.sub(r"[^\w\-.]", "_", name)
    if ext and not name.endswith(ext):
        name += ext
    # Truncate very long names but keep them unique
    if len(name) > 120:
        h = hashlib.md5(name.encode()).hexdigest()[:8]
        name = name[:110] + "_" + h + ext
    return name


# ---------------------------------------------------------------------------
# Sitemap parsing
# ---------------------------------------------------------------------------

def get_urls_from_sitemap(sitemap_url: str) -> list[str]:
    """Parse a sitemap XML and return all <loc> URLs."""
    resp = fetch(sitemap_url)
    if resp is None:
        log.error("Could not fetch sitemap: %s", sitemap_url)
        return []
    soup = BeautifulSoup(resp.content, "lxml-xml")
    return [loc.text.strip() for loc in soup.find_all("loc")]


def collect_all_urls() -> list[str]:
    """Collect URLs from all configured sitemaps, excluding careers."""
    urls = []
    for sm in SITEMAPS:
        log.info("Fetching sitemap: %s", sm)
        urls.extend(get_urls_from_sitemap(sm))
        polite_delay()

    # Deduplicate and filter
    seen = set()
    filtered = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        path = urlparse(url).path.lower()
        if any(pat in path for pat in EXCLUDE_PATTERNS):
            log.info("Excluding (careers): %s", url)
            continue
        filtered.append(url)

    log.info("Collected %d URLs (excluded %d careers pages)", len(filtered), len(urls) - len(filtered))
    return filtered


# ---------------------------------------------------------------------------
# Image downloading
# ---------------------------------------------------------------------------

def download_image(img_url: str, category: str) -> dict | None:
    """Download an image and return metadata, or None on failure."""
    if not img_url or img_url.startswith("data:"):
        return None

    # Resolve relative URLs
    full_url = urljoin(BASE_URL, img_url)

    # Skip tiny tracking pixels, icons, and SVG data URIs
    skip_patterns = ["gravatar.com", "facebook.com", "google-analytics", "pixel", "1x1"]
    if any(p in full_url.lower() for p in skip_patterns):
        return None

    # Determine local path
    parsed = urlparse(full_url)
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif"):
        ext = ".jpg"  # default

    cat_dir = os.path.join(IMAGE_DIR, category)
    os.makedirs(cat_dir, exist_ok=True)

    filename = safe_filename(full_url, ext)
    local_path = os.path.join(cat_dir, filename)
    relative_path = os.path.relpath(local_path, OUTPUT_DIR)

    # Skip if already downloaded
    if os.path.exists(local_path):
        return {"src": full_url, "local_path": relative_path}

    try:
        resp = session.get(full_url, timeout=20, stream=True)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return {"src": full_url, "local_path": relative_path}
    except requests.RequestException as exc:
        log.warning("Image download failed %s: %s", full_url, exc)
        return {"src": full_url, "local_path": None, "error": str(exc)}


# ---------------------------------------------------------------------------
# Page scraping
# ---------------------------------------------------------------------------

def scrape_page(url: str) -> dict:
    """Scrape a single page and return structured data."""
    log.info("Scraping: %s", url)
    resp = fetch(url)
    if resp is None:
        return {"url": url, "error": "Failed to fetch", "scraped_at": datetime.now(timezone.utc).isoformat()}

    soup = BeautifulSoup(resp.text, "lxml")
    category = categorize_url(url)

    # --- Meta ---
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_desc_tag["content"] if meta_desc_tag and meta_desc_tag.get("content") else ""

    og_image_tag = soup.find("meta", attrs={"property": "og:image"})
    og_image = og_image_tag["content"] if og_image_tag and og_image_tag.get("content") else ""

    # --- Published date (blog posts) ---
    published_date = ""
    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        published_date = time_tag["datetime"]
    else:
        meta_date = soup.find("meta", attrs={"property": "article:published_time"})
        if meta_date and meta_date.get("content"):
            published_date = meta_date["content"]

    # --- Author ---
    author = ""
    author_tag = soup.find("span", class_=re.compile(r"author", re.I))
    if author_tag:
        author = author_tag.get_text(strip=True)
    else:
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            author = meta_author["content"]

    # --- Breadcrumbs ---
    breadcrumbs = []
    bc_nav = soup.find("nav", class_=re.compile(r"breadcrumb", re.I)) or soup.find(
        attrs={"class": re.compile(r"breadcrumb", re.I)}
    )
    if bc_nav:
        breadcrumbs = [a.get_text(strip=True) for a in bc_nav.find_all("a")]
        last_span = bc_nav.find("span", class_=re.compile(r"current", re.I))
        if last_span:
            breadcrumbs.append(last_span.get_text(strip=True))

    # --- Headings ---
    headings = {}
    for level in ("h1", "h2", "h3"):
        tags = soup.find_all(level)
        texts = [t.get_text(strip=True) for t in tags if t.get_text(strip=True)]
        if texts:
            headings[level] = texts

    # --- Body text ---
    # Try to get main content area, falling back to body
    content_area = (
        soup.find("article")
        or soup.find("main")
        or soup.find("div", class_=re.compile(r"entry-content|post-content|page-content|main-content", re.I))
        or soup.find("div", id=re.compile(r"content|main", re.I))
    )
    if content_area is None:
        content_area = soup.find("body") or soup

    # Remove script/style/nav/footer noise
    for tag in content_area.find_all(["script", "style", "nav", "footer", "noscript", "iframe"]):
        tag.decompose()

    body_text = content_area.get_text(separator="\n", strip=True)
    # Collapse excessive whitespace
    body_text = re.sub(r"\n{3,}", "\n\n", body_text)

    # --- Images ---
    images = []
    seen_srcs = set()
    img_tags = content_area.find_all("img") if content_area else []
    for img in img_tags:
        src = img.get("src") or img.get("data-src") or ""
        if not src or src in seen_srcs:
            continue
        seen_srcs.add(src)

        alt = img.get("alt", "")
        img_meta = download_image(src, category)
        if img_meta:
            img_meta["alt"] = alt
            images.append(img_meta)

    # Also grab OG image if not already captured
    if og_image and og_image not in seen_srcs:
        img_meta = download_image(og_image, category)
        if img_meta:
            img_meta["alt"] = "og:image"
            images.append(img_meta)

    # --- Links ---
    internal_links = []
    external_links = []
    seen_links = set()
    for a in content_area.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True)
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full_href = urljoin(url, href)
        if full_href in seen_links:
            continue
        seen_links.add(full_href)

        link_obj = {"text": text, "url": full_href}
        if urlparse(full_href).netloc == urlparse(BASE_URL).netloc:
            internal_links.append(link_obj)
        else:
            external_links.append(link_obj)

    # --- Tables ---
    tables = []
    for table in content_area.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        if rows:
            caption_tag = table.find("caption")
            tables.append({
                "caption": caption_tag.get_text(strip=True) if caption_tag else "",
                "rows": rows,
            })

    return {
        "url": url,
        "title": title,
        "meta_description": meta_desc,
        "category": category,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "published_date": published_date,
        "author": author,
        "breadcrumbs": breadcrumbs,
        "headings": headings,
        "body_text": body_text,
        "images": images,
        "internal_links": internal_links,
        "external_links": external_links,
        "tables": tables,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)

    log.info("=" * 60)
    log.info("PlaneSense.com Scraper - Starting")
    log.info("=" * 60)

    # Step 1: Collect URLs
    urls = collect_all_urls()
    if not urls:
        log.error("No URLs collected. Exiting.")
        return

    # Step 2: Scrape each page
    results = []
    errors = []
    total = len(urls)

    for idx, url in enumerate(urls, 1):
        log.info("[%d/%d] Processing: %s", idx, total, url)
        try:
            data = scrape_page(url)
            if "error" in data:
                errors.append({"url": url, "error": data["error"]})
            results.append(data)
        except Exception as exc:
            log.error("Unexpected error scraping %s: %s", url, exc)
            errors.append({"url": url, "error": str(exc)})

        if idx < total:
            polite_delay()

    # Step 3: Split results by type
    pages = [r for r in results if r.get("category") not in ("content", "blog")]
    blog_posts = [r for r in results if r.get("category") in ("content", "blog")]

    # Step 4: Save JSON files
    pages_path = os.path.join(DATA_DIR, "pages.json")
    with open(pages_path, "w", encoding="utf-8") as f:
        json.dump(pages, f, indent=2, ensure_ascii=False)
    log.info("Saved %d pages to %s", len(pages), pages_path)

    blog_path = os.path.join(DATA_DIR, "blog_posts.json")
    with open(blog_path, "w", encoding="utf-8") as f:
        json.dump(blog_posts, f, indent=2, ensure_ascii=False)
    log.info("Saved %d blog posts to %s", len(blog_posts), blog_path)

    # Also save a combined file
    all_path = os.path.join(DATA_DIR, "all_pages.json")
    with open(all_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Step 5: Summary
    total_images = sum(len(r.get("images", [])) for r in results)
    summary = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "total_urls_found": total,
        "total_scraped": len(results),
        "pages": len(pages),
        "blog_posts": len(blog_posts),
        "total_images_downloaded": total_images,
        "errors": len(errors),
        "error_details": errors,
        "categories": {},
    }
    for r in results:
        cat = r.get("category", "unknown")
        summary["categories"][cat] = summary["categories"].get(cat, 0) + 1

    summary_path = os.path.join(OUTPUT_DIR, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    log.info("=" * 60)
    log.info("DONE! Summary:")
    log.info("  Total pages scraped: %d", len(results))
    log.info("  Main pages:          %d", len(pages))
    log.info("  Blog/content posts:  %d", len(blog_posts))
    log.info("  Images downloaded:   %d", total_images)
    log.info("  Errors:              %d", len(errors))
    log.info("  Output directory:    %s", OUTPUT_DIR)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
