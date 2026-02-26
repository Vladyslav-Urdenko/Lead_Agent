import asyncio
import sys
from app.services.scraper import scrape_company_website

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def main():
    url = "https://it-systemhaus-berlin.de/"
    print(f"Testing Scraper on {url}...")
    result = await scrape_company_website(url)
    print("\n--- RESULTS ---")
    print(f"URL: {result.get('url')}")
    print(f"Emails: {result.get('detected_emails')}")
    print(f"Title: {result.get('title')}")

if __name__ == "__main__":
    asyncio.run(main())
