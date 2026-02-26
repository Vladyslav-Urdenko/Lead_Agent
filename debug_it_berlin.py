import asyncio
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import urllib.parse
import json

async def debug_scrape(url: str):
    if not url.startswith('http'):
        url = 'https://' + url

    print(f"Debugging website: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(url, timeout=60000, wait_until="networkidle")
            content = await page.content()
            
            # Save content for manual inspection if needed (optional)
            # with open("debug_page.html", "w", encoding="utf-8") as f:
            #     f.write(content)

            soup = BeautifulSoup(content, "html.parser")

            print("\n--- 1. Raw HTML Regex ---")
            # Regex on raw HTML often catches things text leaves out
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            raw_emails = set(re.findall(email_pattern, content))
            print(f"Raw HTML matches: {list(raw_emails)}")

            print("\n--- 2. Visible Text Regex ---")
            full_text = soup.get_text(separator=' ')
            text_emails = set(re.findall(email_pattern, full_text))
            print(f"Visible Text matches: {list(text_emails)}")

            print("\n--- 3. Mailto Links ---")
            mailto_emails = set()
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if 'mailto:' in href:
                    print(f"Found mailto: {href}")
                    clean_href = urllib.parse.unquote(href)
                    try:
                        clean_email = clean_href.split('mailto:')[1].split('?')[0].split('&')[0]
                        mailto_emails.add(clean_email)
                    except IndexError:
                        pass
            print(f"Mailto emails: {list(mailto_emails)}")

            print("\n--- 4. Obfuscated Checks ---")
            # Check for (at) or [at]
            obfuscated_pattern = r'([a-zA-Z0-9._%+-]+)\s*[\[\(]?\s*(?:at|@)\s*[\]\)]?\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            matches = re.findall(obfuscated_pattern, full_text)
            print(f"Likely obfuscated: {matches}")

            print("\n--- 5. Navigation Candidates ---")
            contact_keywords = [
                "contact", "kontakt", "impressum", "legal", "about", "über uns", "team", "ansprechpartner"
            ]
            candidates = []
            for a in soup.find_all('a', href=True):
                text = a.get_text().strip().lower()
                href = a['href']
                if any(k in text for k in contact_keywords) or any(k in href.lower() for k in contact_keywords):
                    candidates.append({"text": text, "href": href})
            
            print(f"Found {len(candidates)} candidate links:")
            for c in candidates[:10]: # Print first 10
                 print(f" - {c['text']} -> {c['href']}")

        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_scrape("https://it-systemhaus-berlin.de/"))
