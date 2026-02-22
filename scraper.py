from playwright.sync_api import sync_playwright
import time
import random
import json
import re

URL = "https://assetstore.unity.com/3d"
OUTPUT_FILE = "Unity_3D_Market_Intel.json"


def human_like_scroll(page, steps=20, min_wait=0.25, max_wait=0.8):
    height = page.evaluate("() => document.body.scrollHeight")
    for i in range(steps):
        y = int((i + 1) / steps * height)
        page.evaluate(f"window.scrollTo(0, {y})")
        time.sleep(random.uniform(min_wait, max_wait))
    # final slow pass to the bottom
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(1.0)


def parse_price(text):
    if not text:
        return None
    t = text.strip()
    if not t:
        return None
    if re.search(r"free", t, re.I):
        return 0.0
    m = re.search(r"\$\s*([0-9.,]+)", t)
    if m:
        num = m.group(1).replace(',', '')
        try:
            return float(num)
        except:
            return None
    # fallback: any number with decimal or integer
    m2 = re.search(r"([0-9]+\.[0-9]+|[0-9,]+)", t)
    if m2:
        num = m2.group(1).replace(',', '')
        try:
            return float(num)
        except:
            return None
    return None


def parse_rating_count(text):
    if not text:
        return None
    m = re.search(r"([0-9,]+)", text)
    if m:
        return int(m.group(1).replace(',', ''))
    return None


def extract_from_card(el):
    try:
        txt = el.inner_text()
    except Exception:
        txt = ""

    # Name: try common tag lookups
    name = None
    for s in ["h3", "h2", "a[title]", "a"]:
        try:
            node = el.query_selector(s)
            if node:
                n = node.text_content().strip()
                if n:
                    name = n
                    break
        except:
            pass

    # Publisher
    publisher = None
    try:
        pub = el.query_selector(".publisher, .byline, .vendor, .author")
        if pub:
            publisher = pub.text_content().strip()
    except:
        publisher = None
    if not publisher:
        # try to find 'by' line in inner text
        m = re.search(r"by\s+([A-Za-z0-9 ._-]{2,50})", txt, re.I)
        if m:
            publisher = m.group(1).strip()

    # Price
    price = None
    try:
        price_nodes = el.query_selector_all(".price, .asset-price, .product-price, .price__value")
        for pnode in price_nodes:
            ptext = pnode.text_content().strip()
            price_val = parse_price(ptext)
            if price_val is not None:
                price = price_val
                break
    except:
        price = None
    if price is None:
        # fallback: search text for $pattern
        m = re.search(r"\$\s*[0-9.,]+|free", txt, re.I)
        if m:
            price = parse_price(m.group(0))

    # Rating count
    rating_count = None
    try:
        rc_nodes = el.query_selector_all(".rating-count, .reviews, .rating__count")
        for rnode in rc_nodes:
            rtext = rnode.text_content().strip()
            rc = parse_rating_count(rtext)
            if rc is not None:
                rating_count = rc
                break
    except:
        rating_count = None
    if rating_count is None:
        # fallback: find patterns like '123 ratings' or '(123)'
        m = re.search(r"([0-9,]+)\s+(ratings|reviews)", txt, re.I)
        if m:
            rating_count = int(m.group(1).replace(',', ''))
        else:
            m2 = re.search(r"\(([0-9,]+)\)", txt)
            if m2:
                rating_count = int(m2.group(1).replace(',', ''))

    return {
        "name": name or None,
        "publisher": publisher or None,
        "price": float(price) if price is not None else None,
        "rating_count": int(rating_count) if rating_count is not None else None,
    }


def scrape_first_n(n=12):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)

        # human-like scroll to trigger lazy loads
        human_like_scroll(page, steps=20)

        # wait a bit after scrolling
        time.sleep(1.0)

        # try several product card selectors and choose the best candidate
        candidate_selectors = [
            "article.asset-card",
            ".asset-card",
            ".product-card",
            ".product-tile",
            ".package-tile",
            ".card",
            "a.asset",
            "a[href*='/content/']",
            "a[href*='/packages/']",
        ]

        elements = []
        best_found = []
        for sel in candidate_selectors:
            try:
                found = page.query_selector_all(sel)
            except Exception:
                found = []
            if found and (not best_found or len(found) > len(best_found)):
                best_found = found
            if len(found) >= n:
                elements = found
                break

        if not elements:
            elements = best_found

        if not elements:
            print("No product cards found with the heuristic selectors. You may need to adjust selectors for the Unity site.")
        else:
            for el in elements[:n]:
                datum = extract_from_card(el)
                results.append(datum)

        browser.close()

    return results


def main():
    assets = scrape_first_n(12)

    output = {
        "market_analysis": {
            "sector": "3D Assets",
            "pilot": "WalterByte",
            "currency": "USD",
        },
        "assets": assets,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)

    print(f"Saved {len(assets)} assets to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
