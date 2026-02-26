import os
import json
import asyncio
from typing import List, Optional
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

# Load environment variables (ensure .env is loaded in development)
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    # I print a warning here instead of crashing, just in case the env isn't set yet
    print("WARNING: OPENAI_API_KEY is not set in environment variables.")

# Initialize OpenAI Client
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# --- Default Prompts ---
DEFAULT_PROMPTS = {
    "analyze_text": {
        "value": (
            "You are a Technical Sales Analyst in the IoT sector. "
            "Extract structured data from the provided company website text. "
            "Focus on engineering details, protocols (LoRaWAN, Modbus, etc.), and infrastructure. "
            "Be critical and precise."
        ),
        "description": "System prompt for analyzing company website text."
    },
    "social_lead": {
        "value": (
            "You are a Lead Radar. Analyze this search snippet from {source}.\n"
            "Does this look like a REAL PERSON asking for help, complaining, or looking for advice?\n"
            "- IGNORE: News articles, marketing blogs, tutorials, corporate posts, job listings.\n"
            "- KEEP: Personal complaints ('My wifi sucks'), questions ('How to install...'), requests ('Need recommendation').\n"
            "If it is a lead, suggest a helpful, non-salesy reply."
        ),
        "description": "System prompt for filtering social media leads."
    },
    "generate_email": {
        "value": (
            "You are a Senior IoT Solutions Engineer. Write a cold email to a CTO or Lead Engineer.\n"
            "Tone: Professional, concise, technical (no marketing fluff).\n"
            "Structure:\n"
            "1. Icebreaker (use `suggested_hook` from analysis).\n"
            "2. Bridge: Connect their pain points/stack to our offer.\n"
            "3. Soft CTA (e.g., 'Worth a chat?', 'Send a case study?').\n"
            "Constraint: Max 120 words."
        ),
        "description": "System prompt for cold email composition."
    },
    "infer_lead": {
        "value": (
            "You are a Business Consultant for the IoT & Automation sector. "
            "Analyze a local business based purely on their category and user rating. "
            "Infer likely operational problems that cause low ratings (e.g., delays, quality issues, environment). "
            "Return structured JSON."
        ),
        "description": "System prompt for inferred analysis of Google Maps leads without websites."
    }, 
    "my_offer": {
        "value": "We help local businesses automate their workflows and get more customers.",
        "description": "Your core value proposition to be included in the email."
    }
}


# --- Part 1: Define Data Models ---

class CompanyAnalysis(BaseModel):
    """
    Structured analysis of a company's website content focused on IoT/Technical aspects.
    """
    summary: str = Field(..., description="One sentence summary of what the company does.")
    tech_stack: List[str] = Field(default_factory=list, description="List of detected technologies (e.g., MQTT, AWS, Azure, SCADA, Zigbee).")
    pain_points: List[str] = Field(default_factory=list, description="Potential technical challenges or needs inferred from the text.")
    relevance_score: int = Field(..., ge=1, le=10, description="1-10 score of how relevant this company is to IoT/Automation.")
    suggested_hook: str = Field(..., description="A specific fact or detail from the text to use as an icebreaker.")

class SocialLeadAnalysis(BaseModel):
    """
    Analysis of a social media result to determine if it is a genuine sales lead.
    """
    is_lead: bool = Field(..., description="True if this is a real person asking for help, complaining, or looking for advice. False for news articles, marketing blogs, or corporate posts.")
    reason: str = Field(..., description="Brief explanation of why this is or isn't a qualified lead.")
    suggested_reply: Optional[str] = Field(None, description="A short, casual, and helpful suggested reply tweet/comment if it is a lead.")


# --- Part 2: Analysis Function ---

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def analyze_text(raw_text: str, custom_prompt: Optional[str] = None) -> Optional[CompanyAnalysis]:
    """
    Analyzes raw website text using OpenAI to extract structured data about the company.
    Uses 'json_object' mode or structured outputs (function calling) to ensure valid JSON.
    """
    if not raw_text or len(raw_text) < 50:
        print("Text is too short for analysis.")
        return None

    system_prompt = custom_prompt or DEFAULT_PROMPTS["analyze_text"]["value"]

    try:

        # I use the beta parse method here to ensure Pydantic integration for structured outputs
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",  # I am using this model, but gpt-4o-mini is cheaper if needed
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this company website text:\n\n{raw_text[:6000]}"} 
            ],
            response_format=CompanyAnalysis,
        )

        analysis = completion.choices[0].message.parsed
        return analysis

    except Exception as e:
        print(f"Error during AI analysis: {e}")
        # I am raising this error because structured output parsing errors might be permanent
        raise e 


# --- Part 3: Social Media Sorting ---

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def analyze_social_lead(text: str, source: str, custom_prompt: Optional[str] = None) -> Optional[SocialLeadAnalysis]:
    """
    Analyzes a social media snippet to classify it as a human lead vs noise.
    """
    if not text or len(text) < 10:
        return None

    system_prompt = custom_prompt or DEFAULT_PROMPTS["social_lead"]["value"].format(source=source)

    try:
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Snippet: '{text}'"} 
            ],
            response_format=SocialLeadAnalysis,
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        print(f"Error analysis social lead: {e}")
        return None


# --- Part 4: Email Generation Function ---

async def generate_email(analysis: CompanyAnalysis, my_offer: str, custom_prompt: Optional[str] = None) -> str:
    """
    I wrote this function to generate a cold email using the AI, based on the analysis and the user's offer.
    """
    if not analysis:
        return "Error: Cannot generate email without valid analysis."

    system_prompt = custom_prompt or DEFAULT_PROMPTS["generate_email"]["value"]
    
    user_prompt = (
        f"Icebreaker Fact: {analysis.suggested_hook}\n\n"
        f"My Offer: {my_offer}\n\n"
        "Write the email body only."
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4", # I use gpt-4 for better writing quality here
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=250
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error generating email: {e}")
        return "Error generating email."

async def analyze_category_and_rating(
    business_name: str, 
    category: str, 
    rating: float, 
    location: str,
    custom_prompt: Optional[str] = None
) -> Optional[CompanyAnalysis]:
    """
    I use this function to infer company details when we only have Google Maps data (Category + Low Rating).
    Basically, if they have low ratings, I assume they have operational issues we can solve.
    """
    print(f"AI Inferring pain points for {business_name} ({category}, {rating} stars)...")
    
    # I default to the stored prompt if a custom one isn't provided
    system_prompt = custom_prompt or DEFAULT_PROMPTS["infer_lead"]["value"]

    user_prompt = (
        f"Business: {business_name}\n"
        f"Category: {category}\n"
        f"Rating: {rating} stars\n"
        f"Location: {location}\n\n"
        "1. Summarize what they likely do.\n"
        "2. Score relevance to IoT/Automation (1-10).\n"
        "3. Infer 3 likely technical pain points based on their rating/category.\n"
        "4. Guess likely tech stack (POS, sensors, HVAC, etc).\n"
        "5. Write a hook referencing their rating/customer feedback indirectly."
    )

    try:
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=CompanyAnalysis,
        )
        return completion.choices[0].message.parsed
    except Exception as e:
        print(f"Error during AI Inference: {e}")
        return None

# --- Testing Block ---
if __name__ == "__main__":
    
    # Fake scraped content for testing
    fake_raw_text = """
    About Us: Industrial Automation Co. specializes in SCADA systems for water treatment plants.
    We use legacy Modbus TCP controllers and are looking to migrate to the cloud. 
    Our engineers struggle with real-time data visualization and remote monitoring coverage in rural areas.
    We have over 500 sensors deployed across the state.
    """
    
    my_offer_text = "We provide an AI-driven IoT Edge Gateway that converts Modbus to MQTT and pushes data to AWS IoT Core with 99.9% uptime, even in low bandwidth areas."

    async def main():
        print("--- Testing AI Analysis ---")
        analysis = await analyze_text(fake_raw_text)
        
        if analysis:
            print(f"Summary: {analysis.summary}")
            print(f"Score: {analysis.relevance_score}/10")
            print(f"Stack: {analysis.tech_stack}")
            print(f"Hook: {analysis.suggested_hook}")
            
            print("\n--- Testing Email Generation ---")
            email = await generate_email(analysis, my_offer_text)
            print(email)
        else:
            print("Analysis failed.")

    asyncio.run(main())
