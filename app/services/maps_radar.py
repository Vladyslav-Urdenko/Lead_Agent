import json
import logging
import aiohttp
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

async def search_local_leads(query: str, location: str) -> List[Dict[str, Any]]:
    """
    Search for local businesses using Serper.dev (Google Maps API).
    
    Args:
        query: Business type (e.g., "Software Company")
        location: City/Area (e.g., "Berlin, Germany")
        
    Returns:
        List of dictionaries containing business details using Serper 'places' format.
    """
    if not settings.SERPER_API_KEY:
        logger.warning("⚠️ SERPER_API_KEY is missing. Cannot search Maps.")
        return []

    url = "https://google.serper.dev/places"
    
    # Construct search payload
    # "q" combines query and location for best results with Serper
    search_term = f"{query} in {location}"
    payload = json.dumps({
        "q": search_term,
        "gl": "us",   # Global setting, can be customized or inferred if needed
        "hl": "en"    # Language
    })
    
    headers = {
        'X-API-KEY': settings.SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    leads_found = []

    print(f"🌍 Radar pinging Serper.dev for '{search_term}'...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"❌ Serper API Error [{response.status}]: {error_text}")
                    return []
                
                data = await response.json()
                places = data.get("places", [])
                
                for place in places:
                    # Extract fields safely
                    lead = {
                        "name": place.get("title", "Unknown"),
                        "address": place.get("address"),
                        "website": place.get("website"),
                        "rating": place.get("rating"),
                        "reviews_count": place.get("ratingCount", 0),
                        "category": place.get("category"),
                        "phone": place.get("phoneNumber"),
                        "cid": place.get("cid") # Context ID, useful for unique tracking
                    }
                    leads_found.append(lead)

    except Exception as e:
        logger.error(f"❌ Connection Error to Serper: {e}")
        return []

    print(f"✅ Radar found {len(leads_found)} businesses.")
    return leads_found

if __name__ == "__main__":
    import asyncio
    # Simple test
    async def test():
        results = await search_local_leads("IoT Solutions", "London")
        for res in results:
            print(f"- {res['name']} | Web: {res['website']}")
            
    try:
        asyncio.run(test())
    except Exception as e:
        print(e)
