import httpx
import os
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()

# You typically load this from environment variables
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

PLATFORMS = {
    "Twitter": "site:twitter.com",
    "Facebook": "site:facebook.com",
    "Reddit": "site:reddit.com",
    "Quora": "site:quora.com",
    "Instagram": "site:instagram.com",
    "LinkedIn": "site:linkedin.com/in/ OR site:linkedin.com/pub/"
}

async def scan_social_media(keywords: List[str]) -> List[Dict[str, Any]]:
    """
    Scans social media using Google Dorks via Serper API.
    Returns a list of recent findings (last 24 hours).
    """
    if not SERPER_API_KEY:
        print("❌ Error: SERPER_API_KEY is not identifying. Please set it in .env")
        return []

    print(f"📡 Radar scanning for keywords: {keywords}")
    
    findings = []
    
    async with httpx.AsyncClient() as client:
        # We process keywords in parallel batches or sequentially depending on rate limits.
        # For simplicity and safety, we'll do sequential calls here or small batches.
        
        for platform_name, site_operator in PLATFORMS.items():
            for keyword in keywords:
                # Construct query: site:twitter.com "smart home broken"
                query = f"{site_operator} \"{keyword}\""
                
                payload = {
                    "q": query,
                    "tbs": "qdr:d",  # Query Date Range: Day (Last 24 hours)
                    "num": 10,       # Top 10 results
                    "gl": "de",      # Location: Germany (since user seems to be in Berlin based on context)
                    "hl": "en"       # Language: English (can be changed)
                }
                
                headers = {
                    'X-API-KEY': SERPER_API_KEY,
                    'Content-Type': 'application/json'
                }
                
                try:
                    # Rate limit handling (naive)
                    await asyncio.sleep(0.5) 
                    
                    response = await client.post(
                        'https://google.serper.dev/search',
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        organic_results = data.get("organic", [])
                        
                        for result in organic_results:
                            findings.append({
                                "source": platform_name,
                                "keyword_matched": keyword,
                                "title": result.get("title"),
                                "link": result.get("link"),
                                "snippet": result.get("snippet"),
                                "date": result.get("date")  # Serper sometimes provides relative date
                            })
                            print(f"   🔔 Lead found on {platform_name}: {result.get('title')[:50]}...")
                    else:
                        print(f"   ⚠️ Serper Error ({response.status_code}) for {query}: {response.text}")

                except Exception as e:
                    print(f"   ❌ Network Error scanning {platform_name}: {e}")

    # Remove duplicates based on Link
    unique_findings = []
    seen_links = set()
    
    for f in findings:
        if f['link'] not in seen_links:
            seen_links.add(f['link'])
            unique_findings.append(f)
            
    print(f"✅ Radar Scan Complete. Found {len(unique_findings)} unique leads.")
    return unique_findings

# --- Testing Block ---
if __name__ == "__main__":
    # Test keywords
    test_keywords = ["smart home broken", "wifi issues", "zigbee connection failed"]
    
    # Run async test
    leads = asyncio.run(scan_social_media(test_keywords))
    
    if leads:
        print("\n--- SAMPLE LEADS ---")
        for lead in leads[:3]:
            print(f"[{lead['source']}] {lead['title']}")
            print(f"Link: {lead['link']}")
            print("-" * 30)
