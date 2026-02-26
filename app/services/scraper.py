import asyncio
import re
import urllib.parse
from typing import Dict, Any, List, Set
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# --- CONSTANTS ---
CONTACT_KEYWORDS = {
    "high": [
        "contact", "contacts", "contact us", "reach us", "get in touch",  # En
        "yhteystiedot", "ota yhteyttä", "yhteys",  # Fi
        "kontakt", "ansprechpartner", "ansprechpartnerin", # De
        "skontaktuj", "napisz do nas", # Pl
        "contatti", "contacto", "contactar" # It/Es
    ],
    "medium": [
        "impressum", "anfragen", "datenschutz", # De
        "about", "about us", "team", "our team", "support", "help", # En
        "meistä", "asiakaspalvelu", "info", "tietoa meistä", # Fi
        "über uns", "das team", "wir über uns", # De
        "o nas", "wsparcie", "napisz", "zespół" # Pl
    ]
}

EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
# Matches "info (at) domain.com", "info[at]domain.com", "info at domain.com"
OBFUSCATED_EMAIL_PATTERN = r'([a-zA-Z0-9._%+-]+)\s*[\[\(]?\s*(?:at|@)\s*[\]\)]?\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'

class SmartScraper:
    def __init__(self, start_url: str):
        self.start_url = start_url
        if not self.start_url.startswith('http'):
            self.start_url = 'https://' + self.start_url
        
        self.visited_urls: Set[str] = set()
        self.emails_found: Set[str] = set()
        self.queue: List[str] = [self.start_url]
        self.max_pages = 5 # Visit up to 5 pages including home
        self.browser = None
        self.context = None

    async def scan_page(self, page, url: str) -> None:
        """
        I scrape a single page here to find emails and discover new links to visit.
        """
        if url in self.visited_urls:
            return
        self.visited_urls.add(url)
        
        print(f"Scanning: {url}")
        
        try:
            # Go to page
            try:
                await page.goto(url, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"   Navigation failed for {url}: {e}")
                return

            # Get content (Raw and Parsed)
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            full_text = soup.get_text(separator=' ')

            # I run regex on raw HTML first to catch emails hidden in scripts or meta tags
            raw_matches = re.findall(EMAIL_PATTERN, content)
            for email in raw_matches:
                self.emails_found.add(email)

            # Then I check visible text for standard email formats
            text_matches = re.findall(EMAIL_PATTERN, full_text)
            for email in text_matches:
                self.emails_found.add(email)

            # I also look for obfuscated emails (like 'user at domain') in the visible text
            obfuscated_matches = re.findall(OBFUSCATED_EMAIL_PATTERN, full_text)
            for match in obfuscated_matches:
                # match is a tuple ('info', 'domain.com')
                try:
                    email_reconstructed = f"{match[0]}@{match[1]}"
                    print(f"   De-obfuscated email: {email_reconstructed}")
                    self.emails_found.add(email_reconstructed)
                except:
                    pass

            # I extract emails from mailto links here
            for a in soup.find_all('a', href=True):
                href = a.get('href', '').strip()
                if href.startswith('mailto:'):
                    clean_href = urllib.parse.unquote(href)
                    clean_email = clean_href.replace('mailto:', '').split('?')[0].split('&')[0]
                    if '@' in clean_email:
                        self.emails_found.add(clean_email)

            # If I haven't reached the page limit, I look for new links to follow
            if len(self.visited_urls) < self.max_pages:
                candidates = []
                for a in soup.find_all("a", href=True):
                    link_text = a.get_text().lower().strip()
                    href = a.get("href", "")
                    
                    if not href or href.startswith("#") or href.startswith("javascript"):
                        continue
                    
                    if not href.startswith("http"):
                        absolute_href = urllib.parse.urljoin(url, href)
                    else:
                        absolute_href = href
                    
                    # I filter to keep scraping within the same domain, avoiding social media exits
                    try:
                        base_domain = urllib.parse.urlparse(self.start_url).netloc.replace("www.", "")
                        target_domain = urllib.parse.urlparse(absolute_href).netloc.replace("www.", "")
                        
                        if base_domain not in target_domain:
                            continue
                    except:
                        continue

                    # Priority Scoring
                    priority = 0
                    if any(kw in link_text for kw in CONTACT_KEYWORDS["high"]) or any(kw in href.lower() for kw in CONTACT_KEYWORDS["high"]):
                        priority = 2
                    elif any(kw in link_text for kw in CONTACT_KEYWORDS["medium"]) or any(kw in href.lower() for kw in CONTACT_KEYWORDS["medium"]):
                        priority = 1
                    
                    if priority > 0:
                        candidates.append((priority, absolute_href))

                # Sort by priority desc
                candidates.sort(key=lambda x: x[0], reverse=True)
                
                # Add to queue if unique
                for _, link in candidates:
                    if link not in self.visited_urls and link not in self.queue:
                        self.queue.append(link)

        except Exception as e:
            print(f"   ❌ Error on page {url}: {e}")

    async def run(self) -> Dict[str, Any]:
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await self.context.new_page()

            # Main Loop - BFS
            while self.queue and len(self.visited_urls) < self.max_pages:
                current_url = self.queue.pop(0)
                await self.scan_page(page, current_url)
            
            # --- FINAL CLEANUP FOR AI CONTENT ---
            try:
                # If we drifted, try to go back home to get the "Main" content for the AI summary
                # Unless we are already there
                if page.url != self.start_url and self.start_url not in [page.url, page.url+"/"]:
                    # check if start_url was visited successfully
                    pass 
                
                # Use the content of the LAST visited page if valid, or just current.
                # Ideally, we should maybe store the 'Main Page Content' separately in scan_page?
                # For simplicity, let's just grab what we have or reload home if needed.
                
                # Reload home for accurate 'About Company' text
                await page.goto(self.start_url, timeout=30000, wait_until="domcontentloaded")
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # Extract Meta
                title = await page.title()
                meta_desc = ""
                desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
                if desc_tag: meta_desc = desc_tag.get("content", "") or ""

                meta_keywords = ""
                keywords_tag = soup.find("meta", attrs={"name": "keywords"})
                if keywords_tag: meta_keywords = keywords_tag.get("content", "") or ""

                # Cleanup for AI text
                for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe", "svg", "button", "input", "form"]):
                    tag.decompose()
                
                text = soup.get_text(separator=' ')
                clean_text = " ".join(text.split())
                limit = 6000 
                final_text = clean_text[:limit] + "..." if len(clean_text) > limit else clean_text

                return {
                    "status": "success",
                    "url": self.start_url,
                    "final_url": page.url,
                    "title": title,
                    "meta_description": meta_desc,
                    "meta_keywords": meta_keywords,
                    "detected_emails": list(self.emails_found),
                    "raw_text": final_text
                }

            except Exception as e:
                # Fallback return even if HOME reload fails
                return {
                    "status": "success", # Partial success
                    "url": self.start_url,
                    "title": "Error reloading home",
                    "detected_emails": list(self.emails_found),
                    "raw_text": "",
                    "error": f"Scraped emails but failed final content load: {e}"
                }

            finally:
                await self.browser.close()

async def scrape_company_website(url: str) -> Dict[str, Any]:
    scraper = SmartScraper(url)
    return await scraper.run()

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    res = asyncio.run(scrape_company_website("https://it-systemhaus-berlin.de/"))
    print(res)
