import asyncio
from app.services.scraper import scrape_company_website

async def test():
    # Test the HOME PAGE to see if it finds the contact page logic
    url = "https://www.fraktio.fi/"
    print(f"Testing scraper on: {url}")
    
    result = await scrape_company_website(url)
    
    print("\n--- RESULTS ---")
    print(f"Status: {result.get('status')}")
    print(f"Emails: {result.get('detected_emails')}")
    print(f"Title: {result.get('title')}")
    # Print the first 1000 chars of raw text to see if email is visible there
    print(f"Text Preview: {result.get('raw_text')[:1000]}")

if __name__ == "__main__":
    asyncio.run(test())