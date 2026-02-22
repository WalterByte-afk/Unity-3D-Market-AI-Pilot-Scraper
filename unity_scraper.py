"""
Unity Asset Store 3D Category Scraper
Senior AI Pilot: WalterByte
Sector: 3D Assets
Date: February 22, 2026
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Optional, Dict, List, Any
import random
import time

from playwright.async_api import async_playwright
from playwright_stealth.stealth import Stealth


async def human_like_scroll(page, max_scroll_distance: int = 3000, increment: int = 100):
    """
    Simulate human-like scrolling with random increments to trigger lazy-loaded elements.
    
    Args:
        page: Playwright page object
        max_scroll_distance: Total distance to scroll
        increment: Base increment (will be randomized)
    """
    current_scroll = 0
    iterations = 0
    max_iterations = 50  # Safety limit
    
    while current_scroll < max_scroll_distance and iterations < max_iterations:
        # Random increment between 50-150 pixels
        random_increment = random.randint(max(50, increment - 50), increment + 50)
        current_scroll += random_increment
        
        # Scroll with random delays
        await page.evaluate(f"window.scrollBy(0, {random_increment})")
        
        # Random pause between 0.1 - 0.5 seconds (human-like)
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        iterations += 1
    
    # Final scroll to top to reset
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(0.5)


def parse_price(price_text: str) -> float:
    """
    Convert price text to float.
    e.g., '$45.00' -> 45.0
    """
    if not price_text or price_text.strip().upper() == 'FREE':
        return 0.0
    
    # Extract numbers and decimal point
    match = re.search(r'\d+(?:\.\d{2})?', price_text.replace(',', ''))
    if match:
        return float(match.group())
    return 0.0


def parse_rating(rating_text: str) -> Optional[float]:
    """
    Parse rating from text.
    e.g., '4.7' -> 4.7, 'Not enough ratings' -> None
    """
    if not rating_text or 'Not enough ratings' in rating_text:
        return None
    
    match = re.search(r'\d+\.?\d*', rating_text)
    if match:
        return float(match.group())
    return None


def parse_review_count(review_text: str) -> Optional[int]:
    """
    Parse review count from text.
    e.g., '(1.2K)' -> 1200, '(42)' -> 42
    """
    if not review_text or 'Not enough ratings' in review_text:
        return None
    
    # Remove parentheses
    text = review_text.strip().replace('(', '').replace(')', '')
    
    # Handle K suffix (e.g., 1.2K)
    if 'K' in text.upper():
        match = re.search(r'(\d+\.?\d*)[KkMm]?', text)
        if match:
            value = float(match.group(1))
            if 'K' in text.upper():
                return int(value * 1000)
            elif 'M' in text.upper():
                return int(value * 1_000_000)
    else:
        match = re.search(r'\d+', text)
        if match:
            return int(match.group())
    
    return None


async def scrape_unity_store() -> Dict[str, Any]:
    """
    Scrape top 15 3D assets from Unity Asset Store.
    """
    print("🚀 Initializing WalterByte Pilot...")
    print("📍 Target: Unity Asset Store 3D Category")
    print("⏰ Timestamp:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    async with async_playwright() as p:
        # Launch browser with stealth plugin
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # Apply Stealth to avoid detection
        stealth_instance = Stealth()
        await stealth_instance.apply_stealth_async(page)
        
        try:
            print("\n🌐 Navigating to Unity Asset Store...")
            await page.goto(
                'https://assetstore.unity.com/3d',
                wait_until='domcontentloaded',
                timeout=30000
            )
            
            # Wait for initial content load
            await asyncio.sleep(2)
            
            print("\n📜 Performing human-like scrolling to trigger lazy-load...")
            await human_like_scroll(page, max_scroll_distance=4000)
            
            print("🔍 Extracting asset data...")
            
            # Get all asset cards with better selectors
            assets_data = await page.evaluate("""
            () => {
                const assets = [];
                
                // Multiple selector strategies to find asset cards
                let items = document.querySelectorAll('[data-testid*="asset"], [class*="PackageCard"], article');
                
                if (items.length === 0) {
                    items = document.querySelectorAll('[class*="card"], [class*="item"], li');
                }
                
                // Get up to 15 items
                const maxItems = Math.min(15, items.length);
                let assetCount = 0;
                
                for (let i = 0; i < items.length && assetCount < 15; i++) {
                    const item = items[i];
                    const text = item.textContent;
                    
                    // Skip if it's an ad or sponsored content
                    if (text.includes('Sponsored') || text.includes('Advertisement')) {
                        continue;
                    }
                    
                    // Skip if the item is too small or empty (likely not a real asset)
                    if (text.trim().length < 10) {
                        continue;
                    }
                    
                    // Find the asset name: look for the first link that's likely the asset title
                    let name = null;
                    const nameEl = item.querySelector('a[href*="/packages/"], a[href*="/asset/"], h2, h3, [class*="title"]');
                    if (nameEl) {
                        const tempName = nameEl.textContent.trim();
                        if (tempName.length > 2 && tempName.length < 200) {
                            name = tempName;
                        }
                    }
                    
                    if (!name) continue;
                    
                    // Extract publisher: usually appears near the name, often in small text
                    let publisher = null;
                    const allText = item.innerText || text;
                    const lines = allText.split('\\n').filter(l => l.trim().length > 0);
                    
                    // Try to find publisher in common positions
                    // Skip sale/price information
                    for (let j = 0; j < Math.min(8, lines.length); j++) {
                        const line = lines[j].trim();
                        // Skip sale, price, rating, and review related lines
                        if (line && 
                            line !== name && 
                            !line.match(/Sale ends|Price|Free|[$£€]|[0-9]*\\.[0-9]+|\\([0-9KM]+\\)|rating/i) &&
                            line.length > 2 && 
                            line.length < 100) {
                            publisher = line;
                            break;
                        }
                    }
                    
                    if (!publisher) publisher = name;
                    
                    // Extract price: look for $ or "Free"
                    let price = null;
                    const priceMatch = text.match(/[$€£]\\s*([0-9]+(?:\\.[0-9]{2})?)|Free/i);
                    if (priceMatch) {
                        price = priceMatch[0];
                    } else {
                        price = item.querySelector('[class*="price"], span[class*="cost"]')?.textContent.trim();
                    }
                    
                    // Extract rating and review count
                    // Rating is usually a decimal number between 0-5
                    let rating = null;
                    let reviews = null;
                    
                    const ratingMatch = text.match(/([0-4]\\.[0-9]|5\\.0)\\s*(?:out of 5|★|star)?/i);
                    if (ratingMatch) {
                        rating = ratingMatch[1];
                    }
                    
                    // Reviews are usually in (number) or (K) format
                    const reviewMatch = text.match(/\\(([0-9]+\\.?[0-9]*[KMk]?)\\s*(?:rating|review)?[s]?\\)/i);
                    if (reviewMatch) {
                        reviews = reviewMatch[1];
                    } else if (text.match(/Not enough rating/i)) {
                        reviews = 'Not enough ratings';
                    }
                    
                    assets.push({
                        name,
                        publisher: publisher || name,
                        price,
                        rating,
                        reviews
                    });
                    
                    assetCount++;
                }
                
                return assets;
            }
            """)
            
            # If we didn't get enough, try even more aggressive alternatives
            if len(assets_data) < 5:
                print(f"⚠️  Found only {len(assets_data)} assets, retrying with aggressive selectors...")
                assets_data = await page.evaluate("""
                () => {
                    const assets = [];
                    
                    // Get all text nodes and try to reconstruct asset information
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_ELEMENT,
                        null
                    );
                    
                    let currentNode;
                    let assetIndex = 0;
                    
                    while (currentNode = walker.nextNode()) {
                        const el = currentNode;
                        const href = el.getAttribute('href') || '';
                        
                        // Look for package links
                        if (href.includes('/packages/') || href.includes('/asset/')) {
                            const name = el.textContent.trim();
                            
                            if (name.length > 5 && name.length < 200 && assetIndex < 15) {
                                const container = el.closest('[class*="card"], article, li, div[class*="item"]') || el.parentElement;
                                const containerText = container?.textContent || '';
                                
                                let price = 'Free';
                                const priceMatch = containerText.match(/[$€£]\\s*([0-9]+(?:\\.[0-9]{2})?)/);
                                if (priceMatch) {
                                    price = priceMatch[0];
                                }
                                
                                let rating = null;
                                const ratingMatch = containerText.match(/([0-4]\\.[0-9]|5\\.0)(?:\\s|$)/);
                                if (ratingMatch) {
                                    rating = ratingMatch[1];
                                }
                                
                                // Publisher is often the first clickable element after the name
                                let publisher = name;
                                const siblings = Array.from(el.parentElement?.children || []);
                                for (const sib of siblings) {
                                    const text = sib.textContent.trim();
                                    if (text && text !== name && text.length > 2 && text.length < 100) {
                                        publisher = text;
                                        break;
                                    }
                                }
                                
                                assets.push({
                                    name,
                                    publisher,
                                    price,
                                    rating,
                                    reviews: null
                                });
                                assetIndex++;
                            }
                        }
                    }
                    
                    return assets;
                }
                """)

            
            # Process and validate extracted data
            results = []
            for idx, asset in enumerate(assets_data[:15], 1):
                processed_asset = {
                    "id": idx,
                    "asset_name": asset.get('name', '').strip(),
                    "publisher": asset.get('publisher', '').strip(),
                    "price": parse_price(asset.get('price', '')),
                    "rating": parse_rating(asset.get('rating', '')),
                    "review_count": parse_review_count(asset.get('reviews', ''))
                }
                
                results.append(processed_asset)
                
                # Print status message
                status_price = f"${processed_asset['price']:.2f}" if processed_asset['price'] else "FREE"
                status_rating = f"{processed_asset['rating']}" if processed_asset['rating'] else "N/A"
                status_reviews = f"{processed_asset['review_count']}" if processed_asset['review_count'] else "N/A"
                
                print(
                    f"✅ [{idx:2d}] {processed_asset['asset_name']:<40} | "
                    f"Publisher: {processed_asset['publisher']:<20} | "
                    f"Price: {status_price:>10} | Rating: {status_rating:>4} | "
                    f"Reviews: {status_reviews:>6}"
                )
            
            # Create output with metadata
            output = {
                "metadata": {
                    "pilot": "WalterByte",
                    "sector": "3D Assets",
                    "date": datetime.now().isoformat(),
                    "source": "https://assetstore.unity.com/3d",
                    "total_assets": len(results)
                },
                "results": results
            }
            
            return output
            
        finally:
            await page.close()
            await context.close()
            await browser.close()


def main():
    """Main entry point."""
    try:
        # Run async scraper
        output = asyncio.run(scrape_unity_store())
        
        # Save to JSON file
        output_file = "Unity_3D_Market_Intel.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n\n📊 MISSION COMPLETE!")
        print(f"✅ Successfully parsed {output['metadata']['total_assets']} assets")
        print(f"💾 Data saved to: {output_file}")
        print(f"📋 Metadata: Pilot={output['metadata']['pilot']}, "
              f"Sector={output['metadata']['sector']}, "
              f"Date={output['metadata']['date']}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        raise


if __name__ == "__main__":
    main()
