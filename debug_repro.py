import asyncio
import os
from dotenv import load_dotenv

# Load env before importing services
load_dotenv()

from app.services import scraper, ai_engine

async def debug_pipeline():
    print("----- DEBUG START -----")
    
    # 1. Check Env
    apikey = os.getenv("OPENAI_API_KEY")
    print(f"OPENAI_API_KEY Check: {'Present' if apikey else 'Missing'}")
    
    url = "https://example.com"
    offer = "IoT Services"
    
    # 2. Test Scraper
    print(f"\n[1/3] Testing Scraper on {url}...")
    try:
        scrape_result = await scraper.scrape_company_website(url)
        if scrape_result.get("status") == "error":
            print(f"Scraper returned error: {scrape_result}")
        else:
            print(f"Scraper Success. Clean text length: {len(scrape_result.get('raw_text', ''))}")
    except Exception as e:
        print(f"Scraper CRASH: {e}")
        # Stop here if scraper fails (playwright issue?)
        return

    # 3. Test AI Engine
    raw_text = scrape_result.get("raw_text", "Example text content about a company.")
    print(f"\n[2/3] Testing AI Analysis...")
    try:
        analysis = await ai_engine.analyze_text(raw_text)
        if not analysis:
            print("AI returned None")
        else:
            print(f"AI Success. Summary: {analysis.summary}")
    except Exception as e:
        print(f"AI CRASH: {e}")
        return

    print("\n[3/3] Testing Email Generation...")
    try:
        draft = await ai_engine.generate_email(analysis, offer)
        print(f"Email Gen Success. Length: {len(draft)}")
    except Exception as e:
        print(f"Email Gen CRASH: {e}")

if __name__ == "__main__":
    asyncio.run(debug_pipeline())
