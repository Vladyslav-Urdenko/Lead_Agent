"""
AGGRESSIVE EMAIL HUNTER v2.0
===========================
A comprehensive, multi-strategy email finder that searches:
- All website pages (deep crawl)
- Social media profiles (Facebook, LinkedIn, Instagram)
- Common contact paths (brute force)
- Sitemap.xml and robots.txt
- Google search results
- Common email patterns
- Obfuscated/encoded emails
- JavaScript variables
- JSON-LD structured data
- PDF documents
- And more...
"""

import asyncio
import re
import json
import base64
import urllib.parse
import aiohttp
from typing import Dict, Any, List, Set, Optional, Tuple
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
from app.core.config import settings

# =============================================================================
# CONSTANTS & PATTERNS
# =============================================================================

# Email regex patterns
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE)
# More strict obfuscated patterns - require word boundaries and specific formats
OBFUSCATED_AT_PATTERN = re.compile(r'\b([a-zA-Z][a-zA-Z0-9._%+-]{1,30})\s*[\[\(\{<]?\s*(?:at|AT|At)\s*[\]\)\}>]?\s*([a-zA-Z][a-zA-Z0-9.-]{1,30}\.[a-zA-Z]{2,6})\b', re.IGNORECASE)
DOT_OBFUSCATED_PATTERN = re.compile(r'\b([a-zA-Z][a-zA-Z0-9._%+-]{1,30})\s*@\s*([a-zA-Z][a-zA-Z0-9.-]{1,30})\s*[\[\(\{<]?\s*(?:dot|DOT|Dot|punkt|PUNKT)\s*[\]\)\}>]?\s*([a-zA-Z]{2,6})\b', re.IGNORECASE)
HEX_EMAIL_PATTERN = re.compile(r'&#x?[0-9a-fA-F]+;')
CLOUDFLARE_PATTERN = re.compile(r'data-cfemail="([a-fA-F0-9]+)"')

# Common contact page paths to brute force
CONTACT_PATHS = [
    # English
    "/contact", "/contact-us", "/contact.html", "/contact.php", "/contacts",
    "/get-in-touch", "/reach-us", "/email", "/email-us", "/write-us",
    "/about", "/about-us", "/about.html", "/about/contact",
    "/team", "/our-team", "/staff", "/people", "/leadership",
    "/support", "/help", "/customer-service", "/service",
    # German
    "/kontakt", "/kontakt.html", "/kontakt.php", "/ansprechpartner",
    "/impressum", "/impressum.html", "/uber-uns", "/ueber-uns",
    "/datenschutz", "/team-page", "/unser-team",
    # Polish
    "/kontakt", "/o-nas", "/zespol", "/wsparcie", "/pomoc",
    # Finnish
    "/yhteystiedot", "/ota-yhteytta", "/meista", "/tietoa-meista",
    # Spanish/Italian
    "/contacto", "/contactar", "/contatti", "/chi-siamo",
    # French
    "/contact", "/nous-contacter", "/a-propos", "/equipe",
    # Common variants
    "/info", "/information", "/company", "/company-info",
    "/legal", "/legal-notice", "/privacy", "/privacy-policy",
    "/footer", "/sitemap", "/site-map",
]

# Social media domains to extract and scrape
SOCIAL_DOMAINS = {
    "facebook.com": "facebook",
    "fb.com": "facebook", 
    "linkedin.com": "linkedin",
    "instagram.com": "instagram",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "xing.com": "xing",
    "youtube.com": "youtube",
}

# Keywords for prioritizing links
CONTACT_KEYWORDS = {
    "high": [
        "contact", "kontakt", "kontakty", "yhteystiedot", "contatti", "contacto",
        "email", "e-mail", "mail", "write", "reach", "get in touch",
        "ansprechpartner", "ota yhteyttä", "napisz", "skontaktuj",
    ],
    "medium": [
        "about", "über", "uber", "info", "team", "staff", "impressum",
        "support", "help", "service", "meistä", "o nas", "chi siamo",
        "datenschutz", "privacy", "legal", "footer",
    ]
}

# Blacklist patterns for emails (not real emails)
EMAIL_BLACKLIST_PATTERNS = [
    # Fake/test domains
    r'.*@example\.com$',
    r'.*@test\.com$',
    r'.*@localhost.*$',
    r'.*@domain\.com$',
    r'.*@email\.com$',
    r'.*@yoursite\.com$',
    r'.*@company\.com$',
    r'.*@.*\.local$',
    
    # Image files
    r'.*\.png$',
    r'.*\.jpg$',
    r'.*\.gif$',
    r'.*\.webp$',
    r'.*\.svg$',
    r'.*\.ico$',
    
    # JavaScript/CSS files
    r'.*\.js$',
    r'.*\.css$',
    r'.*\.min\.js$',
    r'.*\.min\.css$',
    
    # No-reply addresses
    r'noreply.*',
    r'no-reply.*',
    r'donotreply.*',
    
    # Third-party services (not business emails)
    r'.*@.*sentry.*',
    r'.*@.*wixpress.*',
    r'.*@.*googleapis.*',
    r'.*@.*gstatic.*',
    r'.*@.*cloudflare.*',
    r'.*@.*wp\.com$',
    r'.*@.*wordpress.*',
    
    # JavaScript code artifacts (false positives from obfuscation detection)
    r'.*navig@or.*',
    r'.*loc@ion.*',
    r'.*d@e\.now.*',
    r'.*d@alayer.*',
    r'.*mut@ion.*',
    r'.*anim@e.*',
    r'.*upd@e.*',
    r'.*@tribute.*',
    r'.*transl@ion.*',
    r'.*m@h\..*',
    r'.*m@omo.*',
    r'.*p@s\..*',
    r'.*d@a\..*',
    r'.*st@ic.*',
    r'.*st@s.*',
    r'.*@.*\.length$',
    r'.*@.*\.push$',
    r'.*@.*\.foreach$',
    r'.*@.*\.includes$',
    r'.*@.*\.match$',
    r'.*@.*\.replace$',
    r'.*@.*\.observe$',
    r'.*@.*\.disconnect$',
    r'.*@.*\.startswith$',
    r'.*@.*\.substring$',
    r'.*migr@e.*',
    r'.*@.*\.join$',
    r'.*\.bitte$',
    r'.*\.office$',
    r'.*\.de\.de$',
    r'.*\.messages$',
    r'.*\.host$',
    r'.*\.abs$',
    r'.*\.max$',
    r'.*\.round$',
    r'.*\.search$',
    r'.*\.protocol$',
    r'.*\.origin$',
    r'.*\.href$',
    r'.*\.locale$',
    r'.*found@ion.*',
    r'.*c@egory.*',
    r'^\+.*',  # Starts with +
    r'^\d+.*@.*',  # Starts with numbers
    r'.*wh@sapp.*',
    r'.*browser-upd@e.*',
    r'.*window\..*',
    r'.*document\..*',
    r'.*this\..*',
    r'.*element\..*',
    r'.*fonts\..*',
    r'.*jquery.*',
    r'.*api\..*@.*',
    r'.*\.then$',
    r'.*@.*imported.*',
    r'.*onaggreg@.*',
    r'.*inform@ik.*',  # False positive from word "informatik"
    
    # React/Facebook false positives
    r'.*\.react$',
    r'.*str@egy.*',
    r'.*@tachment.*',
    r'.*@ion.*',
    r'.*@or\..*',
    r'.*@us.*',
    r'.*confirm@.*',
    r'.*indic@.*',
    r'.*valid@e.*',
    r'.*misinform@.*',
    r'.*regul@.*',
    r'.*verific@.*',
    r'.*cre@ion.*',
    r'.*t@acliq.*',
    r'.*w@ch.*',
    r'.*ch@.*settings.*',
    r'.*notific@.*',
    r'.*loc@ion.*',
    r'.*navig@or.*',
    r'.*compos.*@.*',
    r'.*comet.*@.*',
    r'.*fds.*@.*',
    r'.*experience\.react$',
    r'.*\.noop$',
    
    # More UI/JS component false positives
    r'.*ui-d@.*',         # UI date picker
    r'.*d@epicker.*',     # Date picker
    r'.*my\.m@terport.*', # Masterport typo from obfuscation
    r'.*m@terport.*',
    r'.*sso\.d@.*',       # SSO config
    r'.*ad\.@dmt.*',      # Ad management
    r'.*\.ui$',           # TLD .ui is suspicious
    r'.*@sbydre.*',       # Beats by Dre false positive
    r'.*format user@domain.*',  # Example email in text
]

def is_domain_email(email: str, target_domain: str) -> bool:
    """Check if email belongs to target domain."""
    try:
        email_domain = email.split('@')[1].lower()
        target = target_domain.lower().replace("www.", "")
        return target in email_domain or email_domain in target
    except:
        return False

# =============================================================================
# EMAIL HUNTER CLASS
# =============================================================================

class AggressiveEmailHunter:
    """
    Multi-strategy email hunter that aggressively searches for contact emails.
    """
    
    def __init__(self, start_url: str, company_name: str = None):
        self.start_url = start_url
        if not self.start_url.startswith('http'):
            self.start_url = 'https://' + self.start_url
            
        self.company_name = company_name
        self.base_domain = self._extract_domain(self.start_url)
        self.domain_name = self.base_domain.replace("www.", "").split('.')[0]
        
        # State
        self.visited_urls: Set[str] = set()
        self.emails_found: Set[str] = set()
        self.social_links: Dict[str, Set[str]] = {k: set() for k in set(SOCIAL_DOMAINS.values())}
        self.all_links: Set[str] = set()
        
        # Configuration
        self.max_pages = 30  # Visit up to 30 pages
        self.timeout = 20000  # 20 seconds per page
        
        # Browser
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    def _extract_domain(self, url: str) -> str:
        """Extract base domain from URL."""
        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.netloc.lower().replace("www.", "")
        except:
            return ""
    
    def _is_valid_email(self, email: str) -> bool:
        """Check if email is valid and not blacklisted."""
        email = email.lower().strip()
        
        # Basic validation
        if not email or '@' not in email or len(email) < 5:
            return False
        if email.count('@') != 1:
            return False
        
        local, domain = email.split('@')
        if not local or not domain or '.' not in domain:
            return False
        
        # Check blacklist
        for pattern in EMAIL_BLACKLIST_PATTERNS:
            if re.match(pattern, email, re.IGNORECASE):
                return False
                
        return True
    
    def _add_email(self, email: str, source: str = ""):
        """Add email to found set if valid."""
        email = email.lower().strip()
        if self._is_valid_email(email):
            self.emails_found.add(email)
            print(f"   [EMAIL] Found: {email} (from {source})")
    
    def _decode_cloudflare_email(self, encoded: str) -> Optional[str]:
        """Decode Cloudflare email protection."""
        try:
            r = int(encoded[:2], 16)
            email = ''.join([chr(int(encoded[i:i+2], 16) ^ r) for i in range(2, len(encoded), 2)])
            return email
        except:
            return None
    
    def _decode_html_entities(self, text: str) -> str:
        """Decode HTML entities in email."""
        try:
            import html
            return html.unescape(text)
        except:
            return text
    
    def _try_base64_decode(self, text: str) -> Optional[str]:
        """Try to decode base64 encoded email."""
        try:
            decoded = base64.b64decode(text).decode('utf-8')
            if '@' in decoded and '.' in decoded:
                return decoded
        except:
            pass
        return None
    
    def _generate_common_emails(self) -> List[str]:
        """Generate common email patterns for the domain."""
        if not self.base_domain:
            return []
        
        domain = self.base_domain.replace("www.", "")
        prefixes = [
            "info", "contact", "hello", "hi", "mail", "email",
            "office", "admin", "support", "help", "service",
            "sales", "team", "general", "enquiry", "inquiry",
            "post", "kontakt", "anfrage", "buero", "office"
        ]
        
        return [f"{prefix}@{domain}" for prefix in prefixes]
    
    async def _extract_emails_from_content(self, content: str, source: str = "page"):
        """Extract all possible emails from HTML/text content."""
        
        # 1. Standard email regex
        for email in EMAIL_PATTERN.findall(content):
            self._add_email(email, f"{source}/regex")
        
        # 2. Obfuscated "at" pattern (info [at] domain.com)
        for match in OBFUSCATED_AT_PATTERN.findall(content):
            email = f"{match[0]}@{match[1]}"
            self._add_email(email, f"{source}/obfuscated-at")
        
        # 3. Obfuscated "dot" pattern (info@domain [dot] com)
        for match in DOT_OBFUSCATED_PATTERN.findall(content):
            email = f"{match[0]}@{match[1]}.{match[2]}"
            self._add_email(email, f"{source}/obfuscated-dot")
        
        # 4. Cloudflare email protection
        for encoded in CLOUDFLARE_PATTERN.findall(content):
            decoded = self._decode_cloudflare_email(encoded)
            if decoded:
                self._add_email(decoded, f"{source}/cloudflare")
        
        # 5. HTML entities encoding (&#109;&#97;&#105;&#108;)
        decoded_content = self._decode_html_entities(content)
        if decoded_content != content:
            for email in EMAIL_PATTERN.findall(decoded_content):
                self._add_email(email, f"{source}/html-entities")
        
        # 6. JavaScript strings
        js_patterns = [
            r'["\']([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["\']',
            r'email["\s:=]+["\']([^"\']+@[^"\']+)["\']',
            r'mailto["\s:=]+["\']([^"\']+)["\']',
        ]
        for pattern in js_patterns:
            for match in re.findall(pattern, content, re.IGNORECASE):
                self._add_email(match, f"{source}/javascript")
        
        # 7. JSON-LD structured data
        json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        for json_str in re.findall(json_ld_pattern, content, re.DOTALL | re.IGNORECASE):
            try:
                data = json.loads(json_str)
                self._extract_emails_from_json(data, f"{source}/json-ld")
            except:
                pass
        
        # 8. data-email attributes
        for match in re.findall(r'data-email=["\']([^"\']+)["\']', content, re.IGNORECASE):
            self._add_email(match, f"{source}/data-attr")
        
        # 9. href="mailto:" links
        for match in re.findall(r'href=["\']mailto:([^"\'?]+)', content, re.IGNORECASE):
            self._add_email(urllib.parse.unquote(match), f"{source}/mailto")
    
    def _extract_emails_from_json(self, data: Any, source: str):
        """Recursively extract emails from JSON data."""
        if isinstance(data, dict):
            for key, value in data.items():
                if key.lower() in ['email', 'mail', 'contactpoint', 'contact']:
                    if isinstance(value, str):
                        self._add_email(value, source)
                    elif isinstance(value, dict) and 'email' in value:
                        self._add_email(str(value['email']), source)
                self._extract_emails_from_json(value, source)
        elif isinstance(data, list):
            for item in data:
                self._extract_emails_from_json(item, source)
        elif isinstance(data, str) and '@' in data:
            self._add_email(data, source)
    
    def _extract_social_links(self, soup: BeautifulSoup, current_url: str):
        """Extract social media links from page."""
        for a in soup.find_all('a', href=True):
            href = a.get('href', '').lower()
            for domain, platform in SOCIAL_DOMAINS.items():
                if domain in href:
                    # Clean and store the link
                    full_url = urllib.parse.urljoin(current_url, a['href'])
                    self.social_links[platform].add(full_url)
    
    def _collect_all_links(self, soup: BeautifulSoup, current_url: str) -> List[Tuple[int, str]]:
        """Collect and prioritize all internal links."""
        candidates = []
        
        for a in soup.find_all('a', href=True):
            href = a.get('href', '').strip()
            link_text = a.get_text().lower().strip()
            
            if not href or href.startswith('#') or href.startswith('javascript'):
                continue
            
            # Make absolute
            if not href.startswith('http'):
                absolute_href = urllib.parse.urljoin(current_url, href)
            else:
                absolute_href = href
            
            # Check if same domain
            try:
                target_domain = self._extract_domain(absolute_href)
                if self.base_domain not in target_domain and target_domain not in self.base_domain:
                    continue
            except:
                continue
            
            # Skip if already visited
            if absolute_href in self.visited_urls or absolute_href in self.all_links:
                continue
            
            # Calculate priority
            priority = 0
            href_lower = href.lower()
            
            for kw in CONTACT_KEYWORDS["high"]:
                if kw in link_text or kw in href_lower:
                    priority = 3
                    break
            
            if priority == 0:
                for kw in CONTACT_KEYWORDS["medium"]:
                    if kw in link_text or kw in href_lower:
                        priority = 2
                        break
            
            if priority == 0:
                priority = 1  # Default priority for other internal links
            
            candidates.append((priority, absolute_href))
            self.all_links.add(absolute_href)
        
        # Sort by priority (highest first)
        candidates.sort(key=lambda x: -x[0])
        return candidates
    
    async def _scan_page(self, url: str) -> bool:
        """Scan a single page for emails and links."""
        if url in self.visited_urls:
            return False
        
        self.visited_urls.add(url)
        print(f"\n[SCAN {len(self.visited_urls)}/{self.max_pages}] {url}")
        
        try:
            response = await self.page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
            if not response:
                return False
            
            # Wait a bit for dynamic content
            await asyncio.sleep(0.5)
            
            # Get content
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # Extract emails
            await self._extract_emails_from_content(content, url)
            
            # Also check visible text specifically
            text_content = soup.get_text(separator=' ')
            await self._extract_emails_from_content(text_content, f"{url}/text")
            
            # Extract social links
            self._extract_social_links(soup, url)
            
            # Collect internal links
            new_links = self._collect_all_links(soup, url)
            
            return True
            
        except Exception as e:
            print(f"   [WARNING] Error: {str(e)[:100]}")
            return False
    
    async def _brute_force_contact_paths(self):
        """Try common contact page paths."""
        print(f"\n[BRUTE FORCE] Trying {len(CONTACT_PATHS)} common contact paths...")
        
        base = f"https://{self.base_domain}"
        paths_to_try = [p for p in CONTACT_PATHS if f"{base}{p}" not in self.visited_urls]
        
        for path in paths_to_try[:20]:  # Limit to first 20
            if len(self.visited_urls) >= self.max_pages:
                break
            
            url = f"{base}{path}"
            await self._scan_page(url)
    
    async def _check_sitemap(self):
        """Check sitemap.xml for URLs."""
        print(f"\n[SITEMAP] Checking sitemap.xml...")
        
        sitemap_urls = [
            f"https://{self.base_domain}/sitemap.xml",
            f"https://{self.base_domain}/sitemap_index.xml",
            f"https://www.{self.base_domain}/sitemap.xml",
        ]
        
        for sitemap_url in sitemap_urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(sitemap_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            content = await response.text()
                            # Extract URLs from sitemap
                            urls = re.findall(r'<loc>([^<]+)</loc>', content)
                            
                            # Prioritize contact-related URLs
                            for url in urls:
                                url_lower = url.lower()
                                for kw in CONTACT_KEYWORDS["high"] + CONTACT_KEYWORDS["medium"]:
                                    if kw in url_lower:
                                        self.all_links.add(url)
                                        break
                            
                            print(f"   Found {len(urls)} URLs in sitemap")
                            return
            except:
                continue
    
    async def _scrape_facebook_page(self, fb_url: str):
        """Try to extract email from Facebook page - STRICT mode to avoid React false positives."""
        print(f"\n[FACEBOOK] Checking: {fb_url}")
        
        try:
            await self.page.goto(fb_url, timeout=self.timeout, wait_until="domcontentloaded")
            await asyncio.sleep(1)
            
            # Only extract visible text, NOT the full HTML with React code
            # This avoids all the false positives from Facebook's minified JS
            visible_text = await self.page.evaluate('''() => {
                // Get only visible text content, avoiding scripts
                const body = document.body;
                const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT, null, false);
                const texts = [];
                let node;
                while (node = walker.nextNode()) {
                    const parent = node.parentElement;
                    if (parent && !['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(parent.tagName)) {
                        const text = node.textContent.trim();
                        if (text) texts.push(text);
                    }
                }
                return texts.join(' ');
            }''')
            
            # Only look for standard emails in visible text (no obfuscated patterns)
            for email in EMAIL_PATTERN.findall(visible_text):
                self._add_email(email, "facebook/visible-text")
            
            # Also check for mailto links
            mailto_links = await self.page.query_selector_all('a[href^="mailto:"]')
            for link in mailto_links:
                href = await link.get_attribute('href')
                if href:
                    email = href.replace('mailto:', '').split('?')[0]
                    self._add_email(email, "facebook/mailto")
                
        except Exception as e:
            print(f"   [WARNING] Facebook scrape failed: {str(e)[:50]}")
    
    async def _scrape_instagram_page(self, ig_url: str):
        """Try to extract email from Instagram bio."""
        print(f"\n[INSTAGRAM] Checking: {ig_url}")
        
        try:
            await self.page.goto(ig_url, timeout=self.timeout, wait_until="domcontentloaded")
            await asyncio.sleep(1)
            
            content = await self.page.content()
            await self._extract_emails_from_content(content, "instagram")
            
        except Exception as e:
            print(f"   [WARNING] Instagram scrape failed: {str(e)[:50]}")
    
    async def _search_google_for_email(self):
        """Search Google for company email using Serper API."""
        if not settings.SERPER_API_KEY:
            print("\n[GOOGLE] Skipping (no SERPER_API_KEY)")
            return
        
        search_queries = [
            f"{self.company_name or self.domain_name} email contact",
            f"site:{self.base_domain} email",
            f"{self.company_name or self.domain_name} kontakt email",
        ]
        
        print(f"\n[GOOGLE] Searching for emails...")
        
        for query in search_queries[:2]:  # Limit API calls
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://google.serper.dev/search",
                        headers={
                            'X-API-KEY': settings.SERPER_API_KEY,
                            'Content-Type': 'application/json'
                        },
                        json={"q": query, "num": 10}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Check organic results
                            for result in data.get("organic", []):
                                snippet = result.get("snippet", "")
                                await self._extract_emails_from_content(snippet, "google/snippet")
                                
                                # Also check the link if it's our domain
                                link = result.get("link", "")
                                if self.base_domain in link and link not in self.visited_urls:
                                    self.all_links.add(link)
                            
                            # Check knowledge graph
                            kg = data.get("knowledgeGraph", {})
                            if kg:
                                for key in ["email", "contact", "phone"]:
                                    if key in kg:
                                        await self._extract_emails_from_content(str(kg[key]), "google/kg")
                            
            except Exception as e:
                print(f"   [WARNING] Google search failed: {str(e)[:50]}")
    
    async def _verify_common_emails(self):
        """Check if common email patterns exist (basic check)."""
        print(f"\n[SUGGEST] Generating common email patterns for {self.base_domain}...")
        
        common_emails = self._generate_common_emails()
        
        # Add these as potential emails - they'll be filtered by validity check
        for email in common_emails[:5]:  # Limit to top 5 common patterns
            # We can't verify without SMTP check, but we add them as suggestions
            self.emails_found.add(f"[SUGGESTED] {email}")
    
    async def run(self) -> Dict[str, Any]:
        """Execute the full email hunting process."""
        print(f"\n{'='*60}")
        print(f"AGGRESSIVE EMAIL HUNTER v2.0")
        print(f"{'='*60}")
        print(f"Target: {self.start_url}")
        print(f"Domain: {self.base_domain}")
        print(f"Company: {self.company_name or 'Unknown'}")
        print(f"{'='*60}")
        
        async with async_playwright() as p:
            # Launch browser
            self.browser = await p.chromium.launch(headless=True)
            self.page = await self.browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            try:
                # PHASE 1: Check sitemap first
                await self._check_sitemap()
                
                # PHASE 2: Search Google for emails
                await self._search_google_for_email()
                
                # PHASE 3: Scan homepage and follow priority links
                print(f"\n[CRAWL] Starting deep website crawl...")
                
                # Start with homepage
                await self._scan_page(self.start_url)
                
                # Process all collected links by priority
                processed = 0
                links_to_process = sorted(self.all_links, key=lambda x: (
                    -3 if any(kw in x.lower() for kw in CONTACT_KEYWORDS["high"]) else
                    -2 if any(kw in x.lower() for kw in CONTACT_KEYWORDS["medium"]) else
                    -1
                ))
                
                for url in links_to_process:
                    if len(self.visited_urls) >= self.max_pages:
                        break
                    if url not in self.visited_urls:
                        await self._scan_page(url)
                        processed += 1
                
                # PHASE 4: Brute force common contact paths
                if len(self.emails_found) == 0:
                    await self._brute_force_contact_paths()
                
                # PHASE 5: Check social media
                print(f"\n[SOCIAL] Checking social media profiles...")
                
                for fb_url in list(self.social_links["facebook"])[:2]:
                    await self._scrape_facebook_page(fb_url)
                
                for ig_url in list(self.social_links["instagram"])[:2]:
                    await self._scrape_instagram_page(ig_url)
                
                # PHASE 6: If still no emails, suggest common patterns
                real_emails = {e for e in self.emails_found if not e.startswith("[SUGGESTED]")}
                if len(real_emails) == 0:
                    await self._verify_common_emails()
                
                # FINAL: Get page content for AI analysis
                print(f"\n[CONTENT] Collecting page content for AI...")
                
                await self.page.goto(self.start_url, timeout=self.timeout, wait_until="domcontentloaded")
                content = await self.page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # Extract metadata
                title = await self.page.title()
                meta_desc = ""
                desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
                if desc_tag:
                    meta_desc = desc_tag.get("content", "") or ""
                
                # Clean text for AI
                for tag in soup(["script", "style", "nav", "noscript", "iframe", "svg"]):
                    tag.decompose()
                
                text = soup.get_text(separator=' ')
                clean_text = " ".join(text.split())[:6000]
                
                # Separate real emails from suggested
                real_emails = sorted([e for e in self.emails_found if not e.startswith("[SUGGESTED]")])
                suggested_emails = sorted([e.replace("[SUGGESTED] ", "") for e in self.emails_found if e.startswith("[SUGGESTED]")])
                
                # Prioritize emails from target domain
                domain_emails = [e for e in real_emails if is_domain_email(e, self.base_domain)]
                other_emails = [e for e in real_emails if not is_domain_email(e, self.base_domain)]
                
                # Final list: domain emails first, then others
                final_emails = domain_emails + other_emails
                
                # Print summary
                print(f"\n{'='*60}")
                print(f"HUNT COMPLETE")
                print(f"{'='*60}")
                print(f"Pages scanned: {len(self.visited_urls)}")
                print(f"Domain emails found: {len(domain_emails)}")
                print(f"Other emails found: {len(other_emails)}")
                print(f"Suggested emails: {len(suggested_emails)}")
                print(f"Social links: FB={len(self.social_links['facebook'])}, IG={len(self.social_links['instagram'])}, LI={len(self.social_links['linkedin'])}")
                
                if domain_emails:
                    print(f"\nDomain Emails (PRIMARY):")
                    for email in domain_emails:
                        print(f"   * {email}")
                
                if other_emails:
                    print(f"\nOther Emails (from Google/references):")
                    for email in other_emails[:5]:  # Limit display
                        print(f"   * {email}")
                
                if suggested_emails and not domain_emails:
                    print(f"\nSuggested Emails (unverified):")
                    for email in suggested_emails[:3]:
                        print(f"   * {email}")
                
                return {
                    "status": "success",
                    "url": self.start_url,
                    "title": title,
                    "meta_description": meta_desc,
                    "detected_emails": domain_emails if domain_emails else final_emails,  # Prefer domain emails
                    "all_emails": final_emails,
                    "suggested_emails": suggested_emails,
                    "social_links": {k: list(v) for k, v in self.social_links.items() if v},
                    "pages_scanned": len(self.visited_urls),
                    "raw_text": clean_text
                }
                
            except Exception as e:
                import traceback
                print(f"\n[CRITICAL ERROR] {e}")
                traceback.print_exc()
                
                return {
                    "status": "error",
                    "url": self.start_url,
                    "error": str(e),
                    "detected_emails": list(self.emails_found),
                    "raw_text": ""
                }
            
            finally:
                await self.browser.close()


# =============================================================================
# PUBLIC API
# =============================================================================

async def scrape_company_website(url: str, company_name: str = None) -> Dict[str, Any]:
    """
    Main entry point for scraping a company website.
    
    Args:
        url: The website URL to scrape
        company_name: Optional company name for better Google searches
        
    Returns:
        Dict with detected_emails, raw_text, and other metadata
    """
    hunter = AggressiveEmailHunter(url, company_name)
    return await hunter.run()


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # Test with a website
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://it-service.berlin/"
    
    result = asyncio.run(scrape_company_website(test_url))
    
    print(f"\n\n{'='*60}")
    print("FINAL RESULT:")
    print(f"{'='*60}")
    print(f"Emails: {result.get('detected_emails', [])}")
    print(f"Suggested: {result.get('suggested_emails', [])}")
