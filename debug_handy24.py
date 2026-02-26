import asyncio
import re
from typing import Dict, Any
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import urllib.parse

async def debug_scrape(url: str):
    if not url.startswith('http'):
        url = 'https://' + url

    print(f"Debugging website: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # German user agent just in case
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto(url, timeout=60000, wait_until="networkidle")
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")

            # 1. Quick check for emails on main page
            full_text = soup.get_text(separator=' ')
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = list(set(re.findall(email_pattern, full_text)))
            print(f"   Main Page Emails (Regex): {emails}")

            # 2. Check Mailto
            mailto_emails = []
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if href.startswith('mailto:'):
                    clean_href = urllib.parse.unquote(href)
                    clean_email = clean_href.replace('mailto:', '').split('?')[0].split('&')[0]
                    mailto_emails.append(clean_email)
            print(f"   Main Page Emails (Mailto): {mailto_emails}")

            # 3. List all links for debugging
            contact_keywords = [
                "contact", "contacts", "contact us", 
                "yhteystiedot", "ota yhteyttä", 
                "kontakt", "impressum", "über uns", "anfragen", "ansprechpartner", "datenschutz",
                "o nas", "napisz"
            ]
            
            print("\n   --- Link Analysis ---")
            found_contact_link = None
            for a_tag in soup.find_all("a", href=True):
                link_text = a_tag.get_text().lower().strip()
                href = a_tag["href"]
                
                is_contact = any(kw in link_text for kw in contact_keywords) or any(kw in href.lower() for kw in contact_keywords)
                
                if is_contact:
                    print(f"   [MATCH] Text: '{link_text}' | Href: '{href}'")
                    if not found_contact_link:
                         found_contact_link = urllib.parse.urljoin(url, href)
                else:
                    # Print first 10 non-matches to be sure
                    # print(f"   [NO]    Text: '{link_text}' | Href: '{href}'")
                    pass

            if found_contact_link:
                print(f"\n   -> Will visit: {found_contact_link}")
                await page.goto(found_contact_link, timeout=60000, wait_until="domcontentloaded")
                contact_content = await page.content()
                contact_soup = BeautifulSoup(contact_content, "html.parser")
                contact_text = contact_soup.get_text(separator=' ')
                new_emails = list(set(re.findall(email_pattern, contact_text)))
                print(f"   -> Contact Page Emails: {new_emails}")

        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_scrape("https://handy24berlin.de/"))
