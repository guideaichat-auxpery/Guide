import streamlit as st
import os
from openai import OpenAI
from datetime import datetime
import json
import re
import trafilatura
import requests
from PIL import Image
import io
import base64
import logging

# Create logger for utils module (logging configured in app.py)
logger = logging.getLogger(__name__)

# ---- SCROLL UTILITIES ----
def scroll_to_top():
    """Scroll page to top when interface loads"""
    st.markdown(
        """
        <script>
            window.parent.document.querySelector('section.main').scrollTo({top: 0, behavior: 'instant'});
        </script>
        """,
        unsafe_allow_html=True
    )

def add_scroll_to_top_button():
    """Add a floating scroll-to-top button at the bottom of the page - Montessori-inspired design"""
    import streamlit.components.v1 as components
    
    components.html(
        """
        <!-- Scroll to Top Button -->
        <button id="scrollTopBtn" aria-label="Scroll to top"></button>
        
        <style>
        #scrollTopBtn {
            position: fixed;
            bottom: 25px;
            right: 25px;
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #8B7355, #A67B5B);
            border: none;
            border-radius: 50%;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            cursor: pointer;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.4s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            color: white;
            z-index: 999;
        }
        
        #scrollTopBtn.show {
            opacity: 1;
            transform: translateY(0);
        }
        
        #scrollTopBtn:hover {
            background: linear-gradient(135deg, #A67B5B, #B8956A);
            box-shadow: 0 6px 15px rgba(0,0,0,0.2);
            transform: translateY(-2px);
        }
        
        #scrollTopBtn::before {
            content: '⬆️';
        }
        </style>
        
        <script>
        const scrollBtn = document.getElementById('scrollTopBtn');
        const mainSection = window.parent.document.querySelector('section.stMain');
        
        // Show/hide button smoothly based on scroll position
        if (mainSection) {
            mainSection.addEventListener('scroll', () => {
                if (mainSection.scrollTop > 150) {
                    scrollBtn.classList.add('show');
                } else {
                    scrollBtn.classList.remove('show');
                }
            });
        }
        
        // Scroll to top gently when clicked
        scrollBtn.addEventListener('click', () => {
            if (mainSection) {
                mainSection.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
        
        // Ensure page loads at top
        window.addEventListener('load', () => {
            if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
            if (mainSection) {
                mainSection.scrollTo({ top: 0, behavior: 'instant' });
            }
        });
        </script>
        """,
        height=0
    )

def scroll_to_element(element_id):
    """Scroll to a specific element by ID"""
    st.markdown(
        f"""
        <script>
            setTimeout(function() {{
                var element = window.parent.document.getElementById('{element_id}');
                if (element) {{
                    element.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}
            }}, 100);
        </script>
        """,
        unsafe_allow_html=True
    )

def add_response_anchor():
    """Add an invisible anchor at the start of a response for scrolling"""
    import time
    anchor_id = f"response_{int(time.time() * 1000)}"
    st.markdown(f'<div id="{anchor_id}" style="height: 0; margin: 0; padding: 0;"></div>', unsafe_allow_html=True)
    return anchor_id

def scroll_to_latest_response():
    """Scroll to show the beginning of the latest AI response"""
    st.markdown(
        """
        <script>
            setTimeout(function() {
                var chatMessages = window.parent.document.querySelectorAll('[data-testid="stChatMessage"]');
                if (chatMessages.length > 0) {
                    var lastMessage = chatMessages[chatMessages.length - 1];
                    lastMessage.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }, 200);
        </script>
        """,
        unsafe_allow_html=True
    )

# ---- URL PROCESSING UTILITIES ----
def extract_urls_from_text(text):
    """Extract all URLs from a text message"""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    return urls

def fetch_web_content(url):
    """Fetch and extract main text content from a webpage using trafilatura"""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text:
                return f"""
═══════════════════════════════════════════════════════════════════
🔗 WEB CONTENT FROM: {url}
═══════════════════════════════════════════════════════════════════

{text}

═══════════════════════════════════════════════════════════════════
END OF WEB CONTENT
═══════════════════════════════════════════════════════════════════
"""
        return None
    except Exception as e:
        st.warning(f"Could not fetch content from {url}: {str(e)}")
        return None

def fetch_image_from_url(url):
    """Fetch an image from URL and return PIL Image object"""
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content))
            return image
        return None
    except Exception as e:
        st.warning(f"Could not fetch image from {url}: {str(e)}")
        return None

def is_image_url(url):
    """Check if URL likely points to an image"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
    return any(url.lower().endswith(ext) for ext in image_extensions)

def is_document_url(url):
    """Check if URL likely points to a document"""
    doc_extensions = ['.pdf', '.doc', '.docx', '.txt']
    return any(url.lower().endswith(ext) for ext in doc_extensions)

def fetch_document_from_url(url):
    """Fetch a document (PDF, DOCX, TXT) from URL and extract text content"""
    try:
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if response.status_code == 200:
            # Determine document type from URL
            url_lower = url.lower()
            
            if url_lower.endswith('.pdf'):
                # Extract PDF content
                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(response.content))
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    if text.strip():
                        return f"""
═══════════════════════════════════════════════════════════════════
📄 PDF DOCUMENT FROM: {url}
═══════════════════════════════════════════════════════════════════

{text}

═══════════════════════════════════════════════════════════════════
END OF PDF DOCUMENT
═══════════════════════════════════════════════════════════════════
"""
                except Exception as e:
                    st.warning(f"Could not extract PDF content: {str(e)}")
                    return None
                    
            elif url_lower.endswith(('.docx', '.doc')):
                # Extract Word document content
                try:
                    from docx import Document
                    doc = Document(io.BytesIO(response.content))
                    text = "\n".join([para.text for para in doc.paragraphs])
                    if text.strip():
                        return f"""
═══════════════════════════════════════════════════════════════════
📝 WORD DOCUMENT FROM: {url}
═══════════════════════════════════════════════════════════════════

{text}

═══════════════════════════════════════════════════════════════════
END OF WORD DOCUMENT
═══════════════════════════════════════════════════════════════════
"""
                except Exception as e:
                    st.warning(f"Could not extract Word document content: {str(e)}")
                    return None
                    
            elif url_lower.endswith('.txt'):
                # Plain text file
                text = response.text
                if text.strip():
                    return f"""
═══════════════════════════════════════════════════════════════════
📋 TEXT FILE FROM: {url}
═══════════════════════════════════════════════════════════════════

{text}

═══════════════════════════════════════════════════════════════════
END OF TEXT FILE
═══════════════════════════════════════════════════════════════════
"""
        return None
    except Exception as e:
        st.warning(f"Could not fetch document from {url}: {str(e)}")
        return None

def process_url_content(url):
    """Process URL content - fetch web pages, images, or documents"""
    if is_image_url(url):
        # Try to fetch and OCR the image
        image = fetch_image_from_url(url)
        if image:
            try:
                import pytesseract
                text = pytesseract.image_to_string(image)
                if text.strip():
                    return f"""
═══════════════════════════════════════════════════════════════════
🖼️ IMAGE CONTENT FROM: {url}
Extracted text via OCR:
═══════════════════════════════════════════════════════════════════

{text}

═══════════════════════════════════════════════════════════════════
END OF IMAGE CONTENT
═══════════════════════════════════════════════════════════════════
"""
                else:
                    return f"📷 Image fetched from {url} (no text detected)"
            except Exception as e:
                return f"📷 Image fetched from {url} (OCR not available: {str(e)})"
        return None
    elif is_document_url(url):
        # Try to fetch and parse document
        return fetch_document_from_url(url)
    else:
        # Try to fetch as web page
        return fetch_web_content(url)

# ---- CURRICULUM KEYWORD MAPPING ----
# Maps subjects to key curriculum terms from AC V9 descriptors
CURRICULUM_KEYWORDS = {
    "Geography": [
        # Multi-word AC V9 topic names (Year 7-9) - with singular/plural variations
        "Geographies of Interconnections", "geographies of interconnections",
        "Geographies of Interconnection", "geographies of interconnection",
        "Geography of Interconnections", "geography of interconnections",
        "Geography of Interconnection", "geography of interconnection",
        "Biomes and Food Security", "biomes and food security",
        "Water in the World", "water in the world",
        "Place and Liveability", "place and liveability",
        "Landforms and Landscapes", "landforms and landscapes", "landform and landscape",
        "Changing Nations", "changing nations", "changing nation",
        # Content descriptor phrases
        "geographical processes", "geographical phenomena",
        "interconnections between people", "people and environments",
        "people, places and environments", "characteristics of places",
        "human activities", "human impact",
        # Single keywords
        "environment", "environmental", "sustainability", "sustainable",
        "urbanization", "urbanisation", "place", "space", "interconnectedness", "interconnected",
        "landforms", "landscapes", "biomes", "ecosystems", "migration", "food security",
        "climate", "water", "liveability"
    ],
    "History": [
        # Multi-word AC V9 topic names (Year 7-9)
        "The Ancient World", "the ancient world",
        "The Ancient to Modern World", "ancient to modern world",
        "Making a Nation", "making a nation",
        "Australian Involvement in World War I", "world war i", "world war 1",
        # Content descriptor phrases
        "Industrial Revolution", "industrial revolution",
        "causes and effects", "significance of events",
        "historical sources", "cultural exchange",
        "First Nations Australians", "Aboriginal and Torres Strait Islander",
        "Aboriginal and Torres Strait Islander Histories and Cultures",
        "continuity and change", "social groups",
        # Single keywords
        "ancient", "civilisation", "civilization", "heritage", "continuity", "change",
        "historical", "colonisation", "colonization", "federation",
        "indigenous", "First Nations", "Aboriginal", "Torres Strait Islander", "significance",
        "cause", "effect", "identity", "society"
    ],
    "Business and Economics": [
        # Multi-word AC V9 topic names (Year 7-9)
        "Resource Allocation and Making Choices", "resource allocation",
        "Business in the Australian Economy", "australian economy",
        "Personal and Financial Decision-Making", "financial decision-making",
        # Content descriptor phrases
        "economic decision-making", "consumer choices", "market dynamics",
        "ethical considerations", "workplace rights", "financial decisions",
        "businesses and governments", "domestic and international markets",
        # Single keywords
        "innovation", "design thinking", "prototype", "technology", "functionality",
        "economic", "market", "markets", "consumer", "business", "entrepreneurship", "enterprise",
        "trade", "interdependent", "financial", "workplace", "employment", "rights", "responsibilities"
    ],
    "Civics and Citizenship": [
        # Multi-word AC V9 topic names (Year 7-9)
        "Democratic Values, Rights and Responsibilities", "democratic values",
        "Laws and Citizens", "laws and citizens",
        "Government and Democracy", "government and democracy",
        # Content descriptor phrases
        "democratic system of government", "Australian Constitution", "representative democracy",
        "rule of law", "legal system", "political parties", "independent representatives",
        "citizen participation", "media and democracy", "interest groups",
        "rights and responsibilities", "ethical understanding",
        # Single keywords
        "ethics", "ethical", "community", "decision-making", "rights", "responsibilities",
        "intercultural understanding", "democracy", "democratic", "government", "constitution",
        "law", "laws", "justice", "citizenship", "political", "participation", "values",
        "media", "voting", "elections", "representation"
    ],
    "English": [
        # Multi-word AC V9 strand names and concepts
        "language features", "literary devices", "literary texts",
        "text structure", "persuasive texts", "informative texts", "imaginative texts",
        "reading comprehension", "multimodal texts", "analytical images",
        "audience and purpose", "creating texts",
        # Content descriptor phrases
        "analyse and evaluate", "create and edit", "structural features",
        "language features and literary devices", "position readers",
        # Single keywords
        "persuasive", "informational", "narrative", "communication", "presentation", "literacy",
        "text", "texts", "literary", "analysis", "audience", "purpose",
        "multimodal", "reading", "writing", "comprehension", "discourse", "argument", "rhetoric"
    ],
    "Science": [
        # Multi-word AC V9 strand names
        "Biological Sciences", "biological sciences",
        "Physical Sciences", "physical sciences",
        "Chemical Sciences", "chemical sciences",
        "Earth and Space Sciences", "earth and space sciences",
        # Content descriptor phrases
        "living things", "external features", "structural features",
        "energy transformation", "electrical circuits", "forces and motion",
        "natural processes", "human activity", "habitats and environments",
        "scientific inquiry", "scientific method",
        # Single keywords
        "investigate", "experiment", "observation", "hypothesis", "evidence", "inquiry",
        "biological", "physical", "chemical", "earth", "space", "energy", "forces", "motion",
        "ecosystems", "adaptation", "conservation", "sustainability",
        "data", "variables", "prediction"
    ],
    "Mathematics": [
        # Multi-word AC V9 strand names
        "Number and Algebra", "number and algebra",
        "Measurement and Geometry", "measurement and geometry",
        "Statistics and Probability", "statistics and probability",
        # Content descriptor phrases
        "place value", "addition and subtraction", "multiplication and division",
        "fractions and decimals", "data representation", "data interpretation",
        "problem solving", "mathematical reasoning",
        # Single keywords
        "number", "algebra", "geometry", "measurement", "statistics", "probability",
        "reasoning", "patterns", "relationships", "functions",
        "data analysis", "spatial", "calculation", "estimation"
    ],
    "Design and Technologies": [
        # Multi-word AC V9 concepts
        "design thinking", "design process", "design iteration",
        "digital systems", "user-centered design", "sustainable design",
        "materials and technologies", "technologies and society",
        # Content descriptor phrases
        "innovative design", "prototype development", "functionality and aesthetics",
        "environmental sustainability", "engineering principles",
        # Single keywords
        "innovation", "sustainability", "sustainable", "prototype",
        "technology", "technologies", "functionality", "materials", "systems",
        "iteration", "engineering"
    ],
    "Digital Technologies": [
        # Multi-word AC V9 concepts
        "digital systems", "computational thinking", "data representation",
        "artificial intelligence", "machine learning", "cybersecurity",
        "digital solutions", "programming languages", "algorithm design",
        # Content descriptor phrases
        "networks and the internet", "data collection and analysis",
        "automation and control", "problem solving",
        # Single keywords
        "algorithm", "coding", "programming", "data", "networks",
        "automation", "problem-solving"
    ],
    "HASS (Humanities and Social Sciences)": [
        # Multi-word AC V9 topic names (Foundation-Year 6)
        "Personal and Family Histories", "personal and family histories",
        "The Past in the Present", "past in the present",
        "Community and Remembrance", "community and remembrance",
        "First Contacts", "first contacts",
        "The Australian Colonies", "australian colonies",
        "Australia as a Nation", "australia as a nation",
        # Content descriptor phrases
        "continuity and change", "First Nations Australians",
        "cultural diversity", "community identity",
        "democracy and citizenship", "Australian democracy",
        # Single keywords
        "community", "history", "geography", "heritage", "culture", "identity", "change",
        "continuity", "place", "environment", "society", "civic", "economics", "sustainability"
    ]
}

def extract_curriculum_keywords(subject, user_input):
    """
    Extract curriculum-relevant keywords from user input based on subject area.
    Prioritizes multi-word phrases over single words for better AC V9 topic detection.
    
    Args:
        subject: Subject area (e.g., "Geography", "History")
        user_input: The user's message or prompt
        
    Returns:
        List of found keywords that match the subject's curriculum terms
    """
    if not subject or not user_input:
        return []
    
    # Get keywords for this subject
    keywords = CURRICULUM_KEYWORDS.get(subject, [])
    if not keywords:
        return []
    
    # Sort keywords by length (longest first) to prioritize multi-word phrases
    # This ensures "Geographies of Interconnections" is matched before "interconnections"
    sorted_keywords = sorted(keywords, key=lambda k: len(k), reverse=True)
    
    # Find matching keywords using word boundary regex (case-insensitive)
    found_keywords = []
    user_input_lower = user_input.lower()
    matched_positions = set()  # Track positions to avoid overlapping matches
    
    for keyword in sorted_keywords:
        # Use word boundary to match whole words/phrases
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        match = re.search(pattern, user_input_lower)
        
        if match:
            # Check if this position overlaps with a previously matched phrase
            start, end = match.span()
            if not any(start < pos < end or pos == start for pos in matched_positions):
                found_keywords.append(keyword)
                # Mark this position range as matched
                for pos in range(start, end):
                    matched_positions.add(pos)
    
    # Remove duplicates while preserving order (prioritize longer phrases)
    seen = set()
    unique_keywords = []
    for keyword in found_keywords:
        keyword_lower = keyword.lower()
        if keyword_lower not in seen:
            seen.add(keyword_lower)
            unique_keywords.append(keyword)
    
    return unique_keywords

# Initialize OpenAI client
@st.cache_resource
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        st.stop()
    return OpenAI(api_key=api_key)

client = get_openai_client()

# ---- OPENAI API RETRY LOGIC WITH EXPONENTIAL BACKOFF ----
import time
from functools import wraps

def retry_with_exponential_backoff(
    max_retries=5,
    initial_delay=1.0,
    exponential_base=2.0,
    max_delay=32.0
):
    """
    Decorator for OpenAI API calls with exponential backoff retry logic.
    
    Handles:
    - Rate limit errors (429)
    - Timeout errors
    - API errors (500, 502, 503)
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds (default: 1s)
        exponential_base: Base for exponential backoff (default: 2x)
        max_delay: Maximum delay between retries (default: 32s)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Check if error is retryable
                    is_rate_limit = 'rate_limit' in error_str or '429' in error_str
                    is_timeout = 'timeout' in error_str or 'timed out' in error_str
                    is_server_error = any(code in error_str for code in ['500', '502', '503', 'internal server'])
                    
                    if retries >= max_retries or not (is_rate_limit or is_timeout or is_server_error):
                        # Non-retryable error or max retries reached
                        logger.error(f"OpenAI API error (non-retryable or max retries): {type(e).__name__} - {str(e)}")
                        raise
                    
                    # Calculate backoff delay
                    wait_time = min(delay, max_delay)
                    
                    # Log retry attempt
                    logger.warning(f"OpenAI API error (attempt {retries + 1}/{max_retries}): {type(e).__name__}")
                    logger.info(f"Retrying in {wait_time:.1f}s...")
                    
                    time.sleep(wait_time)
                    
                    # Exponential backoff
                    delay *= exponential_base
                    retries += 1
            
            # Should never reach here, but just in case
            raise Exception(f"Max retries ({max_retries}) exceeded")
        
        return wrapper
    return decorator

# Load Montessori texts
@st.cache_data
def load_montessori_own_handbook():
    """Load Dr. Montessori's Own Handbook content with caching"""
    try:
        with open('montessori_own_handbook.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning("Dr. Montessori's Own Handbook file not found.")
        return ""
    except Exception as e:
        st.error(f"Error loading Dr. Montessori's Own Handbook: {str(e)}")
        return ""

@st.cache_data
def load_the_absorbent_mind():
    """Load The Absorbent Mind content with caching"""
    try:
        with open('the_absorbent_mind_montessori.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning("The Absorbent Mind file not found.")
        return ""
    except Exception as e:
        st.error(f"Error loading The Absorbent Mind: {str(e)}")
        return ""

@st.cache_data
def load_the_montessori_method():
    """Load The Montessori Method content with caching"""
    try:
        with open('the_montessori_method.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning("The Montessori Method file not found.")
        return ""
    except Exception as e:
        st.error(f"Error loading The Montessori Method: {str(e)}")
        return ""

@st.cache_data
def load_montessori_national_curriculum():
    """Load Montessori National Curriculum content with caching"""
    try:
        with open('montessori_national_curriculum.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning("Montessori National Curriculum file not found.")
        return ""
    except Exception as e:
        st.error(f"Error loading Montessori National Curriculum: {str(e)}")
        return ""

def get_montessori_companion_system_prompt():
    """Get specialized Montessori Companion system prompt with FULL authentic texts - strictly Montessori-focused"""
    base_prompt = """IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all responses.

You are the Montessori Companion, a philosophical guide deeply rooted in Dr. Maria Montessori's foundational texts and the Montessori National Curriculum.

CRITICAL INSTRUCTIONS:
🔴 **STRICTLY USE MONTESSORI SOURCES ONLY** 🔴
- Your responses MUST be grounded EXCLUSIVELY in the Montessori texts provided below
- NEVER use general internet knowledge or non-Montessori educational theories
- Always cite specific quotes from Dr. Montessori's works when answering
- Reference the Montessori National Curriculum for curriculum-specific queries
- If information is not in the provided texts, acknowledge this limitation

Your role is to:
- Share authentic Montessori wisdom from Dr. Montessori's foundational works
- Explain Montessori philosophy, principles, and practices with accuracy
- Help educators understand cosmic education and child development
- Provide guidance rooted in the prepared environment and observation
- Connect educators to the Montessori National Curriculum framework

RESPONSE FORMAT:
1. Begin with a direct answer grounded in Montessori texts
2. Include specific quotes from Dr. Montessori (cite the work: Own Handbook, Absorbent Mind, or Montessori Method)
3. Provide practical implementation guidance aligned with Montessori principles
4. Reference Montessori National Curriculum when relevant
5. Be warm, humble, and encourage the educator's journey

CORE MONTESSORI PRINCIPLES TO EMPHASIZE:
- The absorbent mind and sensitive periods
- The prepared environment
- Freedom within limits
- Follow the child
- Hands-on, concrete learning
- Mixed-age communities
- Intrinsic motivation (no rewards/punishments)
- Cosmic education and the universe story
- The teacher as observer and guide
- Normalization and concentration
- Human tendencies and cosmic task

═══════════════════════════════════════════════════════════════════
📚 AUTHENTIC MONTESSORI TEXTS AVAILABLE TO YOU:
═══════════════════════════════════════════════════════════════════
"""
    
    # Load ALL Montessori texts COMPLETELY (not truncated)
    montessori_texts = ""
    
    # Dr. Montessori's Own Handbook (FULL)
    handbook = load_montessori_own_handbook()
    if handbook and len(handbook) > 100:
        montessori_texts += f"""
📖 DR. MONTESSORI'S OWN HANDBOOK (COMPLETE):
─────────────────────────────────────────────
{handbook}
─────────────────────────────────────────────
"""
    
    # The Absorbent Mind (FULL)
    absorbent_mind = load_the_absorbent_mind()
    if absorbent_mind and len(absorbent_mind) > 100:
        montessori_texts += f"""
📖 THE ABSORBENT MIND (COMPLETE):
─────────────────────────────────────────────
{absorbent_mind}
─────────────────────────────────────────────
"""
    
    # The Montessori Method (FULL)
    montessori_method = load_the_montessori_method()
    if montessori_method and len(montessori_method) > 100:
        montessori_texts += f"""
📖 THE MONTESSORI METHOD (COMPLETE):
─────────────────────────────────────────────
{montessori_method}
─────────────────────────────────────────────
"""
    
    # Montessori National Curriculum (FULL)
    mnc = load_montessori_national_curriculum()
    if mnc and len(mnc) > 100:
        montessori_texts += f"""
📖 MONTESSORI NATIONAL CURRICULUM (COMPLETE):
─────────────────────────────────────────────
{mnc}
─────────────────────────────────────────────
"""
    
    montessori_texts += """
═══════════════════════════════════════════════════════════════════
END OF AUTHENTIC MONTESSORI TEXTS
═══════════════════════════════════════════════════════════════════

🔴 CRITICAL REMINDER: Use ONLY the texts above. Never introduce concepts not found in these sources. When educators ask questions, search these texts first and provide accurate, contextually relevant quotes and explanations.
"""
    
    return base_prompt + montessori_texts

def get_montessori_system_prompt():
    """Get Montessori-focused system prompt with authentic texts and Australian Curriculum V.9 integration"""
    base_prompt = """IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all responses.

You are Guide, a warm and knowledgeable Montessori educational planning companion. You embody Maria Montessori's philosophy and provide guidance grounded in authentic Montessori principles while ensuring alignment with the Australian Curriculum V.9 for auditing purposes.

You help educators with comprehensive lesson planning, scope and sequence creation, and educational planning that demonstrates clear alignment to both Montessori principles and Australian Curriculum requirements.

Your guidance is based on Maria Montessori's foundational works and focuses on:
- Respect for the child as an individual
- The prepared environment
- Following the child's natural development
- Hands-on, concrete learning experiences
- Mixed-age communities
- Intrinsic motivation rather than external rewards
- The teacher as observer and guide
- Cosmic education connecting all learning
- Adolescent learning alongside early years and primary education

CRITICAL RESPONSE REQUIREMENTS FOR EDUCATIONAL PLANNING:
- Always include a "**Montessori Rationale**" section explaining WHY this approach aligns with Montessori principles
- Include a "**Curriculum Alignment**" section with specific Australian Curriculum V.9 content descriptor codes and achievement standards
- When creating lesson plans or scope & sequence, provide explicit AC V.9 codes for auditing purposes
- Cover all age ranges equally: early years (3-6), primary (6-12), and adolescent (12-18)
- Emphasize adolescent cosmic education, practical application, and community involvement
- For lesson planning, emphasize: concrete materials, sequential presentations, child choice, control of error, observation, and curriculum alignment
- For home-school educators, focus on: demonstrating curriculum coverage, creating educational plans for authorities, scope and sequence development
- Include specific quotes from Montessori texts when relevant

LESSON PLANNING FORMAT:
When creating lesson plans, always include:
1. **Age Group**: (early years/primary/adolescent)
2. **Montessori Area**: (practical life, sensorial, language, mathematics, cultural studies)
3. **Learning Objectives**: (clear, observable outcomes)
4. **Materials Required**: (specific Montessori materials and alternatives)
5. **Presentation Steps**: (detailed sequential instructions)
6. **Australian Curriculum Alignment**: (specific AC V.9 codes and achievement standards)
7. **Montessori Rationale**: (philosophical foundation)
8. **Assessment & Observation**: (how to observe and document learning)
9. **Extensions**: (follow-up activities and connections)

WHAT I WON'T DO:
- Provide guidance that contradicts core Montessori principles
- Suggest punishments, rewards, or coercive methods
- Recommend activities without concrete materials for young children
- Give advice that doesn't respect the child's natural development
- Create lesson plans without Australian Curriculum alignment when requested"""

    # Add condensed Montessori text references
    montessori_references = ""
    
    # Load and add key Montessori content
    handbook = load_montessori_own_handbook()
    if handbook and len(handbook) > 100:
        montessori_references += f"\n\nDr. Montessori's Own Handbook Reference:\n{handbook[:800]}..."
    
    absorbent_mind = load_the_absorbent_mind()
    if absorbent_mind and len(absorbent_mind) > 100:
        montessori_references += f"\n\nThe Absorbent Mind Reference:\n{absorbent_mind[:800]}..."
    
    montessori_method = load_the_montessori_method()
    if montessori_method and len(montessori_method) > 100:
        montessori_references += f"\n\nThe Montessori Method Reference:\n{montessori_method[:800]}..."
    
    return base_prompt + montessori_references

def call_openai_api(messages, max_tokens=None, system_prompt=None, is_student=False, age_group=None, 
                    subject=None, subjects=None, year_level=None, curriculum_type="Blended", use_conversation_history=True,
                    interface_type=None, planning_type=None):
    """Enhanced OpenAI API call with conversation history and curriculum context
    
    Args:
        messages: List of message dictionaries
        max_tokens: Maximum tokens for response (if None, auto-determined by user type)
        system_prompt: Optional custom system prompt (if None, uses enhanced prompts)
        is_student: Whether this is for a student (affects prompt and token limit)
        age_group: Age group for context (optional)
        subject: Subject area for curriculum context (optional)
        year_level: Year level for curriculum context (optional)
        curriculum_type: Type of curriculum ("AC_V9", "Montessori", "Blended")
        use_conversation_history: Whether to manage conversation history (default True)
        interface_type: Type of interface (e.g., "lesson_planning" for age-appropriate prompts)
        planning_type: Type of planning (e.g., "Lesson Planning", "Assessment Rubric")
    """
    try:
        # Determine max_tokens if not specified
        if max_tokens is None:
            max_tokens = get_max_tokens_for_user_type("student" if is_student else "educator")
        
        # Use enhanced prompts if no custom system prompt provided
        if system_prompt is None:
            if is_student:
                system_prompt = get_enhanced_student_prompt(age_group)
            elif interface_type == "lesson_planning" and age_group:
                # Use age-appropriate lesson planning prompt
                system_prompt = get_age_appropriate_lesson_planning_prompt(age_group)
            elif interface_type == "companion":
                # Use age-appropriate companion prompt (defaults to all ages if no age_group)
                system_prompt = get_age_appropriate_companion_prompt(age_group)
            else:
                system_prompt = get_enhanced_educator_prompt()
        
        # Manage conversation history if enabled
        conversation_messages = messages
        if use_conversation_history and len(messages) > 0:
            conversation_messages = get_conversation_context(messages, max_messages=10)
        
        # Extract curriculum keywords from user input
        keyword_context = ""
        all_keywords = []
        if messages and len(messages) > 0:
            # Get the last user message
            last_user_message = None
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_user_message = msg.get("content", "")
                    break
            
            # Extract keywords for all selected subjects
            subject_list = subjects if subjects else ([subject] if subject else [])
            if last_user_message and subject_list:
                for subj in subject_list:
                    found_keywords = extract_curriculum_keywords(subj, last_user_message)
                    if found_keywords:
                        all_keywords.extend(found_keywords)
                
                # Create keyword context if keywords found
                if all_keywords:
                    unique_keywords = list(set(all_keywords))
                    keyword_context = f"🎯 Curriculum Keywords Detected: {', '.join(unique_keywords)}\nFocus on these curriculum-aligned concepts in your response.\n\n"
        
        # RAG: Retrieve relevant chunks from ingested documents
        rag_context = ""
        if last_user_message and len(last_user_message) > 10:
            try:
                from database import get_db
                from rag_system import retrieve_relevant_chunks, format_retrieved_context
                
                db = get_db()
                if db:
                    try:
                        # Determine framework filter based on curriculum type
                        framework_filter = None
                        if curriculum_type == "AC_V9":
                            framework_filter = "AC_V9"
                        elif curriculum_type == "Montessori":
                            framework_filter = "Montessori"
                        # "Blended" retrieves from both frameworks (no filter)
                        
                        # Retrieve top 3 relevant chunks
                        chunks = retrieve_relevant_chunks(
                            db_session=db,
                            query=last_user_message,
                            top_k=3,
                            framework_filter=framework_filter
                        )
                        
                        if chunks:
                            rag_context = format_retrieved_context(chunks)
                    finally:
                        db.close()
            except Exception as e:
                # Silently fail RAG retrieval - don't interrupt user experience
                print(f"RAG retrieval error: {e}")
        
        # Fetch curriculum context for all selected subjects
        curriculum_context = ""
        
        # Determine which subjects to process
        subject_list = subjects if subjects else ([subject] if subject else [])
        
        if subject_list:
            # Get year level (from parameter or auto-map from age with keyword inference)
            target_year_level = year_level
            if not target_year_level and age_group:
                # Pass detected keywords to intelligently infer year level
                target_year_level = get_primary_year_level(age_group, detected_keywords=all_keywords if all_keywords else None)
                
                # Add year level inference info to keyword context if keywords were used
                if all_keywords and target_year_level:
                    inferred = infer_year_level_from_keywords(all_keywords, age_group)
                    if inferred:
                        keyword_context += f"🎓 Inferred Year Level: **{target_year_level}** (based on detected curriculum topics)\n\n"
            
            # Fetch context for each subject and combine
            if target_year_level:
                contexts = []
                for subj in subject_list:
                    context = fetch_curriculum_context(subj, target_year_level, curriculum_type)
                    if context:
                        contexts.append(f"--- {subj} ---\n{context}")
                
                if contexts:
                    curriculum_context = "\n\n".join(contexts)
        
        # Prepare API messages
        api_messages = [{"role": "system", "content": system_prompt}]
        
        # Add keyword context first (if detected)
        if keyword_context:
            api_messages.append({
                "role": "system",
                "content": keyword_context
            })
        
        # Add trending topics context (for students only)
        if is_student:
            from database import get_db
            db = get_db()
            if db:
                try:
                    trending_context = get_trending_topics_context(db, limit=3)
                    if trending_context:
                        api_messages.append({
                            "role": "system",
                            "content": trending_context
                        })
                finally:
                    db.close()
        
        # Add curriculum context as system message if available
        if curriculum_context:
            api_messages.append({
                "role": "system", 
                "content": f"Curriculum Context:\n{curriculum_context}"
            })
        
        # Add RAG retrieved context if available
        if rag_context:
            api_messages.append({
                "role": "system",
                "content": rag_context
            })
        
        # Add conversation messages
        api_messages.extend(conversation_messages)
        
        # Determine temperature based on interface type and planning type
        # Tiered system: High (0.7) for creativity, Medium (0.5) for balanced, Low (0.3) for precision
        temperature = 0.6  # Default balanced
        
        if interface_type == "great_stories":
            temperature = 0.7  # High - Cosmic narratives need imaginative storytelling
        elif interface_type == "companion":
            temperature = 0.7  # High - Warm, exploratory philosophical guidance
        elif interface_type == "pd_expert":
            temperature = 0.7  # High - Creative professional development coaching
        elif interface_type == "lesson_planning":
            if planning_type == "Assessment Rubric":
                temperature = 0.3  # Low - Precise curriculum codes and consistent descriptions
            else:  # "Lesson Planning" or other
                temperature = 0.5  # Medium - Creative pedagogy with accurate curriculum
        elif is_student:
            temperature = 0.6  # Balanced - Engaging but accurate for student learning
        
        # Make API call with retry logic and enhanced parameters
        @retry_with_exponential_backoff(max_retries=3, initial_delay=1.0)
        def make_api_call():
            return client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                presence_penalty=0.3,  # Encourage diverse responses
                frequency_penalty=0.2  # Reduce repetition
            )
        
        response = make_api_call()
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling OpenAI API: {str(e)}")
        return None

def get_max_tokens_for_user_type(user_type):
    """Get appropriate token limit based on user type"""
    if user_type in ["educator"]:
        return 6000  # Enhanced for comprehensive responses and detailed planning
    elif user_type == "student":
        return 800   # Approximately 2,500 words with scaffolding
    else:
        return 1500  # Default

# ---- CONVERSATION HISTORY MANAGEMENT ----
def manage_conversation_history(messages, max_history=10):
    """
    Keep conversation history manageable by limiting to last N messages
    Args:
        messages: List of message dictionaries
        max_history: Maximum number of message pairs to keep (default 10)
    Returns:
        Trimmed message list
    """
    if len(messages) > max_history:
        # Keep only the last max_history messages
        return messages[-max_history:]
    return messages

def get_conversation_context(messages, max_messages=10):
    """
    Get conversation context for API calls with proper history management
    Args:
        messages: Full message history
        max_messages: Maximum messages to include
    Returns:
        Formatted message list for API
    """
    managed_messages = manage_conversation_history(messages, max_messages)
    return [{"role": msg["role"], "content": msg["content"]} for msg in managed_messages]

# ---- AGE TO YEAR LEVEL MAPPING ----
def map_age_to_year_levels(age_group):
    """Map age group to Australian Curriculum year levels"""
    age_to_year_mapping = {
        "3-6": ["Foundation"],
        "6-9": ["Year 1", "Year 2", "Year 3"],
        "9-12": ["Year 4", "Year 5", "Year 6"],
        "12-15": ["Year 7", "Year 8", "Year 9"]
    }
    return age_to_year_mapping.get(age_group, [])

# ---- YEAR LEVEL SPECIFIC TOPIC MAPPING ----
# Maps specific topics/keywords to their primary year level in AC V9
YEAR_SPECIFIC_TOPICS = {
    "Year 9": [
        # Geography Year 9
        "geographies of interconnections", "geographies of interconnection",
        "geography of interconnections", "geography of interconnection",
        # History Year 9
        "making a nation", "australian involvement in world war i",
        "industrial revolution",
        # Business and Economics Year 9
        "personal and financial decision-making",
        # Civics and Citizenship Year 9
        "government and democracy",
    ],
    "Year 8": [
        # Geography Year 8
        "landforms and landscapes", "landform and landscape",
        "changing nations", "changing nation",
        # History Year 8
        "the ancient to modern world", "ancient to modern world",
        # Business and Economics Year 8
        "business in the australian economy", "australian economy",
        # Civics and Citizenship Year 8
        "laws and citizens",
    ],
    "Year 7": [
        # Geography Year 7
        "water in the world", "place and liveability",
        "biomes and food security",
        # History Year 7
        "the ancient world", "ancient world",
        # Business and Economics Year 7
        "resource allocation and making choices", "resource allocation",
        # Civics and Citizenship Year 7
        "democratic values, rights and responsibilities", "democratic values",
    ],
}

def infer_year_level_from_keywords(detected_keywords, age_group):
    """
    Infer the most appropriate year level based on detected curriculum keywords.
    
    Args:
        detected_keywords: List of detected keywords from user input
        age_group: Selected age group (e.g., "12-15")
        
    Returns:
        Specific year level (e.g., "Year 9") or None if can't infer
    """
    if not detected_keywords or not age_group:
        return None
    
    # Get valid year levels for this age group
    valid_year_levels = map_age_to_year_levels(age_group)
    if not valid_year_levels:
        return None
    
    # Convert keywords to lowercase for matching
    keywords_lower = [k.lower() for k in detected_keywords]
    
    # Check each year level from highest to lowest (prioritize higher years)
    for year in ["Year 9", "Year 8", "Year 7", "Year 6", "Year 5", "Year 4", "Year 3", "Year 2", "Year 1"]:
        if year not in valid_year_levels:
            continue
            
        # Check if any detected keyword matches this year's specific topics
        year_topics = [topic.lower() for topic in YEAR_SPECIFIC_TOPICS.get(year, [])]
        for keyword in keywords_lower:
            if keyword in year_topics:
                return year
    
    return None

def get_primary_year_level(age_group, detected_keywords=None):
    """
    Get the primary year level for an age group, with optional keyword-based inference.
    
    Args:
        age_group: Age group string (e.g., "12-15")
        detected_keywords: Optional list of detected curriculum keywords
        
    Returns:
        Year level string (e.g., "Year 8")
    """
    year_levels = map_age_to_year_levels(age_group)
    if not year_levels:
        return None
    
    # Try to infer specific year level from keywords first
    if detected_keywords:
        inferred_year = infer_year_level_from_keywords(detected_keywords, age_group)
        if inferred_year:
            return inferred_year
    
    # Default to middle year level for the age group
    if "Foundation" in year_levels:
        return "Foundation"
    elif len(year_levels) >= 2:
        return year_levels[1]  # Return middle year (e.g., Year 2 for 6-9, Year 5 for 9-12, Year 8 for 12-15)
    return year_levels[0]

# ---- CURRICULUM CONTEXT FETCHING ----
@st.cache_data
def fetch_curriculum_context(subject=None, year_level=None, curriculum_type="AC_V9"):
    """
    Fetch curriculum context for a specific subject and year level
    Args:
        subject: Subject area (e.g., "Science", "Mathematics", "English")
        year_level: Year level (e.g., "Year 3", "Year 5")
        curriculum_type: Type of curriculum ("AC_V9", "Montessori", "Blended")
    Returns:
        Formatted curriculum context string
    """
    if not subject or not year_level:
        return ""
    
    # Australian Curriculum V9 contexts
    ac_v9_contexts = {
        "Science": {
            "Year 1": """Australian Curriculum V9 — Science (Year 1)
Strand: Biological Sciences
Focus: Living things have a variety of external features
Descriptor: "Observe external features of plants and animals and describe ways they can be grouped based on these features" (AC9S1U01)
Montessori Connection: Classification activities, nature studies, and sensorial exploration of living things in the prepared environment.""",
            
            "Year 2": """Australian Curriculum V9 — Science (Year 2)
Strand: Physical Sciences
Focus: Forces and materials
Descriptor: "Explore the way objects move and how pushing and pulling can change the way objects move" (AC9S2U02)
Montessori Connection: Practical life activities exploring force, movement materials, and cosmic education connections.""",
            
            "Year 3": """Australian Curriculum V9 — Science (Year 3)
Strand: Physical Sciences
Focus: Forces and motion
Descriptor: "Explore how contact and non-contact forces cause changes in the motion and shape of objects" (AC9S3U02)
Montessori Connection: Students investigate push and pull forces using everyday materials and Montessori apparatus such as weights, ramps, and cosmic education stories about movement and forces in the universe.""",
            
            "Year 4": """Australian Curriculum V9 — Science (Year 4)
Strand: Earth and Space Sciences
Focus: Earth's surface and natural processes
Descriptor: "Describe how natural processes and human activity cause changes to Earth's surface" (AC9S4U03)
Montessori Connection: Cosmic education stories about Earth's formation, geography materials, and outdoor observation studies.""",
            
            "Year 5": """Australian Curriculum V9 — Science (Year 5)
Strand: Biological Sciences
Focus: Living things have structural features and adaptations
Descriptor: "Examine how particular structural features and behaviours of living things enable their survival in specific habitats" (AC9S5U01)
Montessori Connection: Classification work, nature studies, and cosmic education exploring interconnections in ecosystems.""",
            
            "Year 6": """Australian Curriculum V9 — Science (Year 6)
Strand: Physical Sciences
Focus: Energy transformation
Descriptor: "Investigate energy transfer and transformation in electrical circuits" (AC9S6U02)
Montessori Connection: Practical experiments with circuits, cosmic education about energy in the universe, and hands-on investigations."""
        },
        
        "Mathematics": {
            "Year 1": """Australian Curriculum V9 — Mathematics (Year 1)
Strand: Number
Focus: Counting and place value
Descriptor: "Recognise, represent and order numbers to at least 120 using physical and virtual materials and numerals" (AC9M1N01)
Montessori Connection: Golden beads, number rods, sandpaper numbers, and sequential counting materials.""",
            
            "Year 2": """Australian Curriculum V9 — Mathematics (Year 2)
Strand: Number
Focus: Addition and subtraction
Descriptor: "Add and subtract one- and two-digit numbers, representing problems using number sentences and solve using part-part-whole understanding" (AC9M2N04)
Montessori Connection: Stamp game, bead frames, and concrete materials for operations.""",
            
            "Year 3": """Australian Curriculum V9 — Mathematics (Year 3)
Strand: Number
Focus: Multiplication and division
Descriptor: "Recall and demonstrate proficiency with multiplication facts up to 10; extend and apply facts to develop related division facts" (AC9M3N04)
Montessori Connection: Multiplication bead board, division materials, and concrete exploration of operations.""",
            
            "Year 4": """Australian Curriculum V9 — Mathematics (Year 4)
Strand: Number
Focus: Fractions and decimals
Descriptor: "Recognise and extend the number system to tenths and hundredths and explain the connections to the metric system" (AC9M4N04)
Montessori Connection: Decimal system materials, fraction insets, and concrete decimal work.""",
            
            "Year 5": """Australian Curriculum V9 — Mathematics (Year 5)
Strand: Measurement
Focus: Area and volume
Descriptor: "Choose and use appropriate metric units to measure length, area, capacity and mass; estimate and check measurements" (AC9M5M01)
Montessori Connection: Geometry cabinet, measurement materials, and practical life applications.""",
            
            "Year 6": """Australian Curriculum V9 — Mathematics (Year 6)
Strand: Statistics
Focus: Data representation and interpretation
Descriptor: "Interpret and compare data displays, including displays for two categorical variables" (AC9M6ST01)
Montessori Connection: Graphing materials, data collection activities, and cosmic education connections."""
        },
        
        "English": {
            "Year 1": """Australian Curriculum V9 — English (Year 1)
Strand: Literacy
Focus: Phonics and word knowledge
Descriptor: "Use phoneme–grapheme correspondences to read and write words" (AC9E1LY04)
Montessori Connection: Movable alphabet, sandpaper letters, phonogram work, and language materials.""",
            
            "Year 2": """Australian Curriculum V9 — English (Year 2)
Strand: Literature
Focus: Narrative structure
Descriptor: "Create and edit short imaginative, informative and persuasive written texts" (AC9E2LY06)
Montessori Connection: Students plan, draft, and publish narratives using Montessori movable alphabets, storytelling materials, and command cards.""",
            
            "Year 3": """Australian Curriculum V9 — English (Year 3)
Strand: Literacy
Focus: Reading comprehension
Descriptor: "Use comprehension strategies when listening and reading to build understanding" (AC9E3LY05)
Montessori Connection: Reading analysis work, command cards, and cosmic education story discussions.""",
            
            "Year 4": """Australian Curriculum V9 — English (Year 4)
Strand: Language
Focus: Text structure and organisation
Descriptor: "Understand how texts are made cohesive by using personal and possessive pronouns and by using resources for tracking participants" (AC9E4LA03)
Montessori Connection: Grammar boxes, sentence analysis, and language development materials.""",
            
            "Year 5": """Australian Curriculum V9 — English (Year 5)
Strand: Literacy
Focus: Creating texts
Descriptor: "Plan, create, edit and publish written and multimodal texts" (AC9E5LY06)
Montessori Connection: Research skills, presentation work, and cosmic education project writing.""",
            
            "Year 6": """Australian Curriculum V9 — English (Year 6)
Strand: Literature
Focus: Literary analysis
Descriptor: "Identify and explain how analytical images like figures, tables and diagrams contribute to understanding" (AC9E6LA04)
Montessori Connection: Text analysis, research materials, and integrated cosmic education studies.""",
            
            "Year 7": """Australian Curriculum V9 — English (Year 7)
Strand: Literacy
Focus: Analysing and creating texts
Descriptor: "Create and edit literary texts that experiment with language features and literary devices" (AC9E7LE05)
Additional: "Analyse and evaluate the ways that language features vary according to audience and purpose" (AC9E7LA06)
Montessori Connection: Adolescent expression through writing, debate preparation, and cosmic education connections to human communication.""",
            
            "Year 8": """Australian Curriculum V9 — English (Year 8)
Strand: Literature
Focus: Critical analysis
Descriptor: "Analyse how texts position readers and viewers through language, structural and presentational devices" (AC9E8LE03)
Additional: "Create and edit literary texts that adapt plot structure, characters and language" (AC9E8LE05)
Montessori Connection: Critical thinking, persuasive communication, and adolescent exploration of perspective and voice.""",
            
            "Year 9": """Australian Curriculum V9 — English (Year 9)
Strand: Literacy
Focus: Complex analysis and argumentation
Descriptor: "Analyse and evaluate how language features are used to represent ideas and issues in ways that may influence audiences" (AC9E9LA07)
Additional: "Create and edit texts that respond to written and visual texts, developing original ideas drawn from these texts" (AC9E9LE05)
Montessori Connection: Adolescent moral reasoning, argumentative discourse, and cosmic education about human communication and social change."""
        },
        
        "History": {
            "Year 7": """Australian Curriculum V9 — History (Year 7)
Focus: The Ancient World
Descriptor: "Identify and describe the causes and effects of significant events that shaped the ancient world" (AC9HH7K01)
Additional: "Analyse the role of groups and the significance of particular individuals in ancient societies" (AC9HH7K03)
General Capabilities: Critical & Creative Thinking, Ethical Understanding
Montessori Connection: Timeline of civilizations, cosmic education exploring human society development, and interdependence of cultures.""",
            
            "Year 8": """Australian Curriculum V9 — History (Year 8)
Focus: The Ancient to Modern World
Descriptor: "Explain the causes and effects of events and developments in the period from approximately 650 CE (AD) to 1750" (AC9HH8K01)
Additional: "Analyse how different groups in society experienced and participated in these changes" (AC9HH8K04)
General Capabilities: Intercultural Understanding, Critical & Creative Thinking
Montessori Connection: Human tendencies toward exploration and social organization, cosmic education about cultural exchange.""",
            
            "Year 9": """Australian Curriculum V9 — History (Year 9)
Focus: Making a Nation to Australian Involvement in World War I
Descriptor: "Explain the significance of the Industrial Revolution and the movement of peoples for the development of Australian society" (AC9HH9K02)
Additional: "Analyse the causes and effects of Federation and how this shaped Australian identity" (AC9HH9K04)
Cross-Curriculum Priority: Aboriginal & Torres Strait Islander Histories and Cultures
Montessori Connection: Adolescent exploration of identity, social justice, and cosmic education about Australia's place in world history."""
        },
        
        "Geography": {
            "Year 7": """Australian Curriculum V9 — Geography (Year 7)
Focus: Water in the World & Place and Liveability
Descriptor: "Explain processes that influence the characteristics of places and the interconnections between people, places and environments" (AC9HG7K03)
Additional: "Analyse the causes and effects of geographical phenomena and challenges" (AC9HG7K04)
General Capabilities: Critical & Creative Thinking, Sustainability
Montessori Connection: Earth studies, cosmic education about interconnected systems, and environmental stewardship.""",
            
            "Year 8": """Australian Curriculum V9 — Geography (Year 8)
Focus: Landforms and Landscapes & Changing Nations
Descriptor: "Explain how geographical processes change the characteristics of places and the interconnections between people and environments" (AC9HG8K03)
Additional: "Analyse the causes and effects of urbanisation and migration, and the consequences for people, places and environments" (AC9HG8K04)
Cross-Curriculum Priority: Sustainability, Asia and Australia's Engagement with Asia
Montessori Connection: Landform studies, cosmic education about Earth's processes, and human adaptation to environments.""",
            
            "Year 9": """Australian Curriculum V9 — Geography (Year 9)
Focus: Biomes and Food Security & Geographies of Interconnections
Descriptor: "Explain how geographical processes change the characteristics of places and the interconnections between people, places and environments" (AC9HG9K03)
Additional: "Analyse the causes and effects of challenges facing places and regions, and consequences for sustainability" (AC9HG9K05)
Cross-Curriculum Priority: Sustainability, Aboriginal & Torres Strait Islander Histories and Cultures
Montessori Connection: Biome studies, cosmic education about interconnected global systems, and food security as human responsibility."""
        },
        
        "Business and Economics": {
            "Year 7": """Australian Curriculum V9 — Economics and Business (Year 7)
Focus: Resource Allocation and Making Choices
Descriptor: "Explain how markets operate and the role of individuals, businesses and governments in economic decision-making" (AC9HE7K01)
Additional: "Analyse the factors that influence decisions about work, and characteristics of successful businesses" (AC9HE7K02)
General Capabilities: Critical & Creative Thinking, Ethical Understanding
Montessori Connection: Adolescent economic independence, cosmic education about human work and exchange, and enterprise education.""",
            
            "Year 8": """Australian Curriculum V9 — Economics and Business (Year 8)
Focus: Business in the Australian Economy
Descriptor: "Explain how businesses respond to opportunities and challenges in domestic and international markets" (AC9HE8K01)
Additional: "Analyse the rights, responsibilities and ethical considerations of participants in the workplace" (AC9HE8K02)
General Capabilities: Ethical Understanding, Critical & Creative Thinking
Montessori Connection: Adolescent work exploration, entrepreneurship, and cosmic education about human economic systems.""",
            
            "Year 9": """Australian Curriculum V9 — Economics and Business (Year 9)
Focus: Personal and Financial Decision-Making
Descriptor: "Explain how participants in the economy are interdependent and how markets enable trade" (AC9HE9K01)
Additional: "Analyse factors that influence consumer and financial decisions, and consequences for individuals, businesses and the economy" (AC9HE9K02)
General Capabilities: Critical & Creative Thinking, Ethical Understanding, Literacy, Numeracy
Montessori Connection: Adolescent financial literacy, cosmic education about economic interdependence, and responsible decision-making."""
        },
        
        "Civics and Citizenship": {
            "Year 7": """Australian Curriculum V9 — Civics and Citizenship (Year 7)
Focus: Democratic Values, Rights and Responsibilities
Descriptor: "Explain the key features of Australia's democratic system of government and how it is shaped by the Australian Constitution" (AC9HC7K01)
Additional: "Analyse the key ideas that underpin Australia's representative democracy and explain their significance" (AC9HC7K02)
General Capabilities: Ethical Understanding, Critical & Creative Thinking
Cross-Curriculum Priority: Aboriginal & Torres Strait Islander Histories and Cultures
Montessori Connection: Adolescent exploration of justice, cosmic education about human rights, and participatory democracy.""",
            
            "Year 8": """Australian Curriculum V9 — Civics and Citizenship (Year 8)
Focus: Laws and Citizens
Descriptor: "Explain how Australia's legal system aims to provide justice, including through the rule of law, laws and courts" (AC9HC8K01)
Additional: "Analyse how citizens can participate in their democracy including through the media, interest groups and political parties" (AC9HC8K03)
General Capabilities: Ethical Understanding, Critical & Creative Thinking
Montessori Connection: Adolescent moral independence, cosmic education about justice systems, and active citizenship.""",
            
            "Year 9": """Australian Curriculum V9 — Civics and Citizenship (Year 9)
Focus: Government and Democracy
Descriptor: "Explain the role of political parties and independent representatives in Australia's system of government" (AC9HC9K01)
Additional: "Analyse how citizens participate in resolving contemporary issues and how values can influence actions" (AC9HC9K04)
General Capabilities: Ethical Understanding, Critical & Creative Thinking, Intercultural Understanding
Cross-Curriculum Priority: Aboriginal & Torres Strait Islander Histories and Cultures
Montessori Connection: Adolescent social consciousness, cosmic education about human governance, and community contribution."""
        },
        
        "HASS (Humanities and Social Sciences)": {
            "Year 1": """Australian Curriculum V9 — HASS (Year 1)
Focus: Personal and Family Histories
Descriptor: "Explore the past through the experiences of individuals and families" (AC9HS1K01)
Montessori Connection: Family timeline work, sensorial exploration of history, and cosmic education about continuity and change.""",
            
            "Year 2": """Australian Curriculum V9 — HASS (Year 2)
Focus: The Past in the Present
Descriptor: "Identify and describe continuity and change in family and local community life over time" (AC9HS2K01)
Montessori Connection: Community studies, timeline work, and cosmic education about human communities.""",
            
            "Year 3": """Australian Curriculum V9 — HASS (Year 3)
Focus: Community and Remembrance
Descriptor: "Examine significant events and people in the local community and their contribution to the community's identity" (AC9HS3K02)
Montessori Connection: Local community exploration, timeline of community, and cosmic education about human belonging.""",
            
            "Year 4": """Australian Curriculum V9 — HASS (Year 4)
Focus: First Contacts
Descriptor: "Explain the diversity of First Nations Australians' ways of life before and after the arrival of Europeans" (AC9HS4K01)
Cross-Curriculum Priority: Aboriginal & Torres Strait Islander Histories and Cultures
Montessori Connection: Timeline of Australian history, cosmic education about cultural diversity, and respect for Indigenous knowledge.""",
            
            "Year 5": """Australian Curriculum V9 — HASS (Year 5)
Focus: The Australian Colonies
Descriptor: "Explain the economic, political and social causes and effects of colonial settlement on First Nations Australians" (AC9HS5K04)
Cross-Curriculum Priority: Aboriginal & Torres Strait Islander Histories and Cultures
Montessori Connection: Timeline work, cosmic education about colonization and impact, and justice education.""",
            
            "Year 6": """Australian Curriculum V9 — HASS (Year 6)
Focus: Australia as a Nation
Descriptor: "Explain the key features of Australia's democracy including elections, and the role of the Constitution" (AC9HS6K05)
Additional: "Explain the significance of key events in the development of Australian democracy and citizenship" (AC9HS6K04)
Montessori Connection: Timeline of Australian democracy, cosmic education about governance systems, and civic participation."""
        }
    }
    
    # Check if we have specific AC V9 context
    if curriculum_type in ["AC_V9", "Blended"] and subject in ac_v9_contexts:
        if year_level in ac_v9_contexts[subject]:
            context = ac_v9_contexts[subject][year_level]
            if curriculum_type == "Blended":
                context += "\n\nBlended Approach: Integrate Montessori materials and philosophy with AC V9 descriptors for comprehensive learning."
            return context
    
    # Generic context if specific not found
    if subject and year_level:
        return f"""Curriculum Context for {subject}, {year_level}:
Connect learning to both Australian Curriculum V9 standards and Montessori principles.
Use concrete materials, follow the child's interests, and emphasize cosmic education connections."""
    
    return ""

def get_age_appropriate_companion_prompt(age_group=None):
    """
    Generate age-appropriate Montessori companion prompt based on age group.
    If no age_group provided, returns a comprehensive prompt covering all ages 3-18.
    
    Args:
        age_group: Optional age range string ("3-6", "6-9", "9-12", "12-15")
    
    Returns:
        String containing the appropriate system prompt for Montessori companion
    """
    
    # If no specific age group, provide comprehensive guidance for all ages
    if not age_group or age_group == "all":
        return """IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all responses.

You are GuideChat, a warm and knowledgeable Montessori companion rooted in Dr. Maria Montessori's authentic philosophy and foundational texts. You support educators working with children and adolescents ages 3-18 across all planes of development.

🌍 **YOUR ROLE: Pure Montessori Guide (Ages 3-18)**

You provide authentic Montessori guidance grounded in Dr. Montessori's original works, spanning ALL planes of development:

**The Four Planes of Development:**
- **First Plane (0-6)**: Absorbent mind, sensorial exploration, independence, order, concrete learning
- **Second Plane (6-12)**: Reasoning mind, imagination, cosmic education, moral development, abstract thinking
- **Third Plane (12-18)**: Social consciousness, intellectual independence, valorization, community contribution
- **Fourth Plane (18-24)**: Specialized study, career preparation, social responsibility (when relevant)

**CRITICAL: Adapt all guidance to the developmental plane being discussed.**

**When Educators Ask About Montessori Concepts:**
- **Prepared Adult**: Guide across all planes - self-awareness, observation skills, humility, spiritual preparation
- **Prepared Environment**: Physical, psychological, social aspects for each developmental stage
- **Observation**: Techniques for different ages, what to observe, recording methods
- **Great Lessons**: Cosmic education implementation across planes
- **Normalization**: Recognition and support at each developmental stage
- **Freedom & Discipline**: Age-appropriate balance and application
- **Sensitive Periods**: Recognition and support across development
- **Cosmic Education**: Universe story connections for all subjects and ages

**Core Montessori Principles (All Ages):**
- Follow the child's natural development
- Prepared environment appropriate to the plane
- Hands-on, concrete to abstract learning progression
- Mixed-age communities and peer learning
- Intrinsic motivation, not external rewards
- Adult as observer and guide, not instructor
- Cosmic education connecting all learning to the universe story
- Respect for the child as a whole human being

**Your Expertise Includes:**
- **Teacher Training Topics**: Prepared Adult, observation techniques, presentations, environment preparation
- **Philosophical Concepts**: Absorbent mind, sensitive periods, normalization, inner discipline, cosmic task
- **Practical Implementation**: Materials, presentations, daily rhythms, classroom management
- **Developmental Understanding**: Characteristics of each plane, appropriate responses
- **Cosmic Education**: Integration across subjects and ages
- **Montessori Assessment**: Observation-based, portfolio development, child-led demonstration

**Response Guidelines:**
1. **Draw from authentic texts**: Reference Dr. Montessori's Own Handbook, The Absorbent Mind, The Montessori Method
2. **Match to developmental plane**: 3-6 concrete materials; 6-12 imagination & research; 12-18 real-world engagement
3. **Honor Montessori philosophy**: No rewards/punishments, follow the child, prepared adult
4. **Provide practical guidance**: Specific materials, presentations, environmental setup
5. **Ask clarifying questions** when needed to provide appropriate developmental guidance
6. **Use appropriate tone**: Gentle for early years, enthusiastic for primary, philosophical for adolescents

**What You Provide:**
- Pure Montessori philosophy and practical implementation
- Teacher training on Montessori concepts (Prepared Adult, observation, etc.)
- Age-appropriate materials and presentation guidance
- Cosmic education connections across all ages
- Classroom environment and rhythm support
- Developmental stage-specific understanding
- Montessori assessment and observation methods

**What You Avoid:**
- Curriculum alignment or government standards (this is a pure Montessori space)
- One-size-fits-all advice ignoring developmental differences
- Punishments, rewards, or coercive methods at any age
- Activities inappropriate to the developmental plane
- Non-Montessori pedagogical approaches
- Contradicting core Montessori philosophy

**Remember:** 
- You are a Montessori purist, drawing from Dr. Montessori's authentic works
- A 4-year-old needs different guidance than a 14-year-old
- The Prepared Adult is the foundation of Montessori practice across all ages
- Always consider the developmental plane when responding
- Teacher training and philosophical questions are your specialty"""
    
    # Age-specific companion prompts
    age_specific_prompts = {
        "3-6": """You are GuideChat, a warm Montessori companion specializing in the First Plane of Development (ages 0-6, focus on 3-6).

🌱 **FOCUS: The First Plane of Development (Ages 0-6)**

**Developmental Characteristics (Dr. Montessori's Observations):**
- **Absorbent Mind**: Unconscious absorption (0-3), conscious absorption (3-6) - effortlessly taking in from environment
- **Sensitive Periods**: Language, order, movement, refinement of senses, small objects, social aspects
- **Concrete Learning**: All learning through hands-on sensorial experience and manipulation
- **Independence**: "Help me to do it myself" - the fundamental cry of this age
- **Order**: Deep psychological need for consistency, routine, and logical sequence
- **Constructive Rhythm**: Work-rest cycles, repetition leading to mastery

**Your Guidance Centers On:**
- **Practical Life**: Pouring, spooning, tonging, food preparation, care of self, care of environment, grace and courtesy
- **Sensorial**: Pink Tower, Brown Stair, Red Rods, Color Tablets, Sound Cylinders, tactile experiences, geometric solids
- **Language**: Sandpaper Letters, Moveable Alphabet, oral language games, phonetic progression, vocabulary enrichment
- **Mathematics**: Concrete quantity (Number Rods, Spindle Boxes, Cards & Counters, Golden Beads, introduction to decimal system)
- **Cultural Studies**: Puzzle maps, land/water forms, botany/zoology classification, music, art appreciation

**Key Montessori Principles for This Plane:**
- Materials must have control of error (child self-corrects)
- Presentations are slow, deliberate, precise, with minimal language
- Three-period lessons for vocabulary development
- Freedom within limits - child chooses within prepared environment
- Observation is the primary tool for understanding the child
- Prepared environment with beauty, order, and purpose
- Mixed-age community (3-6 years together)

**The Prepared Adult for Ages 3-6:**
- Deep observation skills - seeing the child, not our expectations
- Humility and spiritual preparation
- Mastery of precise presentations
- Understanding of sensitive periods
- Patience and trust in the child's inner guide

**Tone**: Warm, gentle, precise, honoring the absorbent mind and emerging independence

**Guidance Style**: Provide specific Montessori materials, exact presentation steps, and developmental rationale rooted in Dr. Montessori's philosophy.""",

        "6-9": """You are GuideChat, a warm Montessori companion specializing in the Second Plane of Development - Part 1 (ages 6-9).

🌿 **FOCUS: The Second Plane - Part 1 (Ages 6-9)**

**Developmental Characteristics (Dr. Montessori's Observations):**
- **Reasoning Mind**: "Why?" and "How?" drive all exploration - the child seeks causality
- **Imagination**: Power to go beyond the senses through stories and visualization - the key to learning
- **Social Development**: Peer relationships become central, collaborative work, emerging moral awareness
- **Cosmic Education**: Desire to understand their place in the universe and interconnections
- **Abstract Thinking Begins**: Moving from concrete manipulation to representational and abstract thought
- **Hero Worship**: Admiration for great human achievements and contributions

**Your Guidance Centers On:**
- **Cosmic Education**: Five Great Stories as foundation (Universe, Life, Humans, Language, Mathematics) - the skeleton key
- **Language**: Grammar boxes, sentence analysis, word study, creative writing, reading comprehension
- **Mathematics**: Bead frames, multiplication/division materials, fractions, geometry, passage to abstraction
- **Science**: Classification work (botany, zoology), experiments, timelines of life, scientific method introduction
- **History/Geography**: Timelines, cultural studies, economic geography fundamentals, human contributions
- **Collaborative Learning**: Group work, peer teaching, research projects, presentations

**Key Montessori Principles for This Plane:**
- Use imagination and storytelling to spark curiosity and wonder
- Great Lessons provide the big picture; follow-up work provides the details
- Materials still important but more abstract (hierarchical materials, charts, impressionistic charts)
- Research and independent exploration actively encouraged
- Social group work is essential to development
- Reasoning and "why" questions must be honored with substance
- Mixed-age community (6-9 or 6-12)

**The Prepared Adult for Ages 6-9:**
- Master storyteller - bringing cosmic education to life
- Enthusiastic guide to research and discovery
- Observer of social dynamics and moral development
- Provider of "just enough" information to spark further inquiry
- Facilitator of collaborative work

**Tone**: Enthusiastic, story-driven, encouraging wonder and cosmic connections

**Guidance Style**: Include cosmic education connections, specific materials, and opportunities for imagination and reasoning.""",

        "9-12": """You are GuideChat, a warm Montessori companion specializing in the Second Plane of Development - Part 2 (ages 9-12).

🌳 **FOCUS: The Second Plane - Part 2 (Ages 9-12)**

**Developmental Characteristics (Dr. Montessori's Observations):**
- **Abstract Reasoning**: Fully capable of complex thought, analysis, and abstraction
- **Justice & Fairness**: Strong moral compass, deep reasoning about right and wrong
- **Intellectual Independence**: Self-directed research and deep investigation - "going out"
- **Social Awareness**: Understanding societal structures and their place within them
- **Hero Worship**: Inspired by great figures and their contributions to humanity
- **Passage to Abstraction**: Ready to work without concrete materials in many areas

**Your Guidance Centers On:**
- **Research Skills**: Independent investigation, note-taking, bibliography, presentation skills, "going out"
- **Cosmic Education Deepens**: Interconnections, systems thinking, human contributions to civilization
- **Advanced Mathematics**: Full abstraction, algebraic thinking, advanced geometry, squaring and cubing
- **Scientific Method**: Hypothesis formation, experimentation, analysis, conclusion, scientific reasoning
- **Cultural Studies**: Economic geography, history timelines, cultural interconnections, fundamental needs of humans
- **Creative Expression**: Writing, drama, art, music as ways to synthesize and express understanding

**Key Montessori Principles for This Plane:**
- Honor intellectual independence and self-direction
- Provide opportunities for deep research and specialization
- Connect learning to real-world applications and cosmic significance
- Support moral reasoning about justice, fairness, and human dignity
- Encourage presentation and communication of research findings
- Materials now primarily support abstraction (timelines, charts, research resources)
- "Going out" into the community for authentic learning
- Mixed-age community continues (often 6-12 together)

**The Prepared Adult for Ages 9-12:**
- Facilitator of deep research and inquiry
- Guide to resources and research methods
- Observer of moral and intellectual development
- Provider of cosmic context and connections
- Supporter of "going out" experiences
- Respecter of the child's intellectual autonomy

**Tone**: Intellectually rigorous, respectful of growing autonomy, encouraging deep inquiry

**Guidance Style**: Include research pathways, cosmic connections, and opportunities for moral reasoning and intellectual autonomy.""",

        "12-15": """You are GuideChat, a warm Montessori companion specializing in the Third Plane of Development (ages 12-18, focus on 12-15).

🌲 **FOCUS: The Third Plane of Development (Ages 12-18)**

**Developmental Characteristics (Dr. Montessori's Observations):**
- **Social Consciousness**: Deep awareness of societal issues, passionate desire to contribute to humanity
- **Moral Independence**: Forming personal values and ethical frameworks, questioning authority
- **Intellectual Work**: Capacity for rigorous academic study combined with practical application
- **Identity Formation**: "Who am I?" and "How do I fit into society?" - the central questions
- **Physical & Emotional Changes**: Heightened sensitivity, self-awareness, vulnerability
- **Social Valuation**: Need for recognition and valorization from society
- **Sense of Justice**: Strong, sometimes rigid sense of fairness and equity

**Your Guidance Centers On:**
- **Erdkinder (Land Children)**: Dr. Montessori's vision - farm school, practical work, community living
- **Real-World Engagement**: Community projects, social enterprises, meaningful work with value
- **Intellectual Rigor**: Seminars, Socratic dialogue, complex texts, philosophical inquiry
- **Social Contribution**: Work that genuinely benefits others and society
- **Moral & Ethical Development**: Exploring values, justice, rights, responsibilities, civic engagement
- **Economic Independence**: Understanding economy through running enterprises
- **Authentic Assessment**: Self-evaluation, portfolio, demonstration of real competence

**Key Montessori Principles for This Plane:**
- Treat as emerging adults fully capable of moral reasoning
- Provide meaningful work with real consequences and social value
- Balance intellectual study with practical, physical work
- Honor deep need for social contribution and belonging
- Support identity formation through choice, responsibility, and valorization
- Create opportunities for leadership, autonomy, and authentic contribution
- AVOID childish activities, abstract-only learning, or infantilizing approaches
- Small community living (residential if possible, or intensive programs)

**Dr. Montessori's Erdkinder Vision:**
- **Valorization**: Building self-worth through meaningful contribution to society
- **Farm/Land School**: Learning through practical agricultural and community work
- **Seminar Model**: Intellectual discourse, collaborative learning, philosophical discussion
- **Social & Economic Independence**: Real understanding through doing and running enterprises
- **Connection to Land**: Practical work in nature, understanding human relationship to earth
- **Community Living**: Small group living, shared responsibility, social development

**The Prepared Adult for Ages 12-18:**
- Respectful guide treating adolescents as emerging adults
- Facilitator of real-world experiences and valorization
- Provider of intellectual rigor and philosophical depth
- Supporter of social contribution and meaningful work
- Observer of identity formation and moral development
- Connector to community and authentic opportunities

**Tone**: Mature, philosophical, exploratory, treating adolescents as emerging adults with dignity

**Guidance Style**: Include provocations, philosophical questions, real-world engagement opportunities, and deep respect for adolescent developmental needs and Montessori's Erdkinder vision."""
    }
    
    # Return age-specific prompt if provided
    return age_specific_prompts.get(age_group, age_specific_prompts.get("12-15"))

def get_enhanced_educator_prompt():
    """Enhanced provocational educator prompt with MANDATORY AC V9 alignment and adolescent intellectual sophistication"""
    return """IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all responses.

You are GuideChat, an advanced AI teaching assistant that designs learning experiences grounded in Montessori philosophy and the Australian Curriculum V9.

🧠 **DEVELOPMENTAL FOCUS: The Adolescent Mind (Third Plane, ages 12–18)**
These learners seek moral purpose, social belonging, and intellectual independence.
They move from sensory exploration → to conceptual and moral reasoning.
They examine complex causality, interdependence, ethical dilemmas, and civic responsibility.

CRITICAL: Your responses MUST meet ALL quality standards below. This is not optional.

⚠️ AUSTRALIAN CURRICULUM VERSION 9 ONLY - DO NOT USE V8.4 ⚠️
You MUST use Australian Curriculum VERSION 9 (AC V9) codes and content descriptors.
ALL codes must start with "AC9" (e.g., AC9S6H01, AC9E5LA03, AC9M4N04, AC9HG8K04).
NEVER reference V8.4 codes (AC codes without "9" like ACS6H01, ACE5LA03).
If uncertain, state explicitly: "Australian Curriculum Version 9" in your response.

═══════════════════════════════════════════════════════════════════
DESIGN PRINCIPLES FOR ADOLESCENT SOPHISTICATION:
═══════════════════════════════════════════════════════════════════
When generating lesson plans or inquiry experiences:

1. **Prioritize sophisticated, open-ended questions** requiring ethical reasoning, social analysis, and systems thinking.
   - AVOID simple factual recall or one-dimensional inquiry
   - USE nuanced, ambiguous problems with multiple valid perspectives

2. **Always begin with a PROVOCATION or real-world quote/scenario**, preferably from Australian life, culture, or current affairs.
   - e.g., "Australia's cities keep growing — but at what cost to the country that sustains them?"
   - e.g., "A local Indigenous group reclaims land for cultural preservation. How should governments respond?"

3. **Frame inquiry around DILEMMAS or TENSIONS**, not just topics.
   - Instead of "How can we protect the environment?" → "Who decides what protection means — and who benefits?"
   - Instead of "What is democracy?" → "When should the majority not get their way?"

4. **Integrate INTERDISCIPLINARY thinking** — connect geography, technology, literature, civics, ethics, sustainability.

5. **Expect AUTONOMY and REAL-WORLD engagement.**
   - Encourage students to design projects, enterprises, debates, investigations with social purpose.

6. **Use MATURE TONE** — philosophical, exploratory, treating students as emerging adults capable of moral reasoning and abstract thought.

7. **AVOID childish or sensory-based activities** for adolescents — focus on ethical dilemmas, societal issues, critical reasoning, interdisciplinary inquiry, and authentic adolescent expression (debate, enterprise, activism, art, research).

═══════════════════════════════════════════════════════════════════
MANDATORY QUALITY GATE CHECKLIST (Self-assess before responding):
═══════════════════════════════════════════════════════════════════
Before finalizing ANY response, verify:
✓ Opens with PROVOCATION from real Australian context (quote, statistic, scenario, tension, dilemma) — not just a topic
✓ Framed as DILEMMA or TENSION with NO simple answer, requiring ethical/philosophical/civic reasoning
✓ Demands higher-order thinking: synthesis, analysis, evaluation, ethical reasoning (NOT factual recall)
✓ Uses MATURE, PHILOSOPHICAL tone appropriate for adolescent emerging adults (ages 12-18)
✓ Cites SPECIFIC AC V9 descriptor codes starting with "AC9" (e.g., AC9S6H01, AC9HG8K04) with achievement standards
✓ Maps to General Capabilities explicitly (Ethical Understanding, Critical & Creative Thinking, Intercultural Understanding)
✓ Includes First Nations perspectives or multicultural dimensions where culturally relevant
✓ Provides 3-4 exploration pathways representing genuinely DIFFERENT worldviews or analytical lenses (not minor variations)
✓ Expects AUTONOMY & REAL-WORLD engagement: projects, enterprises, debates, investigations with social purpose
✓ Includes Montessori third-plane alignment (social consciousness, moral independence, intellectual work, community contribution)

═══════════════════════════════════════════════════════════════════
AUSTRALIAN CURRICULUM V9 REQUIREMENTS (NON-NEGOTIABLE):
═══════════════════════════════════════════════════════════════════
1. CITE SPECIFIC DESCRIPTOR CODES: Every response must reference precise AC V9 codes
   Example: "AC9S6H01: Investigate the role of science in responding to conservation and sustainability challenges"
   NOT ACCEPTABLE: "Links to Science understanding strand"

2. NAME ACHIEVEMENT STANDARDS: Identify expected student performance levels
   Example: "Students explain cause-and-effect relationships and analyse data from investigations (Year 6 Achievement Standard)"

3. INTEGRATE GENERAL CAPABILITIES with explicit mapping:
   - Ethical Understanding: Specify which elements (recognising ethical concepts, reasoning in decision making, exploring values/rights/responsibilities)
   - Critical & Creative Thinking: Name specific skills (analysing, synthesising, evaluating, reflecting)
   - Intercultural Understanding: State connections (recognising worldviews, considering and developing multiple perspectives)
   - Personal & Social Capability: Identify aspects (self-management, social awareness, social management)

4. REFERENCE CROSS-CURRICULUM PRIORITIES when relevant:
   - Aboriginal and Torres Strait Islander Histories and Cultures (with specific connections to Country/Place, Culture, People)
   - Sustainability (systems thinking, futures thinking, values & ethics)
   - Asia and Australia's Engagement with Asia

═══════════════════════════════════════════════════════════════════
INTELLECTUAL RIGOR STANDARDS (Years 5-10):
═══════════════════════════════════════════════════════════════════
Your responses MUST demand:

COGNITIVE COMPLEXITY:
- Analysis of systems, patterns, and interconnections (not isolated facts)
- Synthesis across disciplines (science ↔ ethics ↔ civics ↔ culture)
- Evaluation of competing claims, values, and evidence
- Creation of reasoned arguments with supporting evidence

ETHICAL SOPHISTICATION:
- Genuine moral dilemmas with competing legitimate values
- Exploration of justice, fairness, rights, and responsibilities
- Consideration of short-term vs. long-term consequences
- Recognition that reasonable people can disagree

AUSTRALIAN CONTEXTUAL DEPTH:
- Contemporary Australian social/environmental/political issues
- First Nations knowledge systems and perspectives (with cultural respect)
- Australian multicultural realities and plural worldviews
- Real challenges facing Australian communities and environments

═══════════════════════════════════════════════════════════════════
MANDATORY RESPONSE STRUCTURE:
═══════════════════════════════════════════════════════════════════

**🔥 Provocation & Environmental Setup (Australian Context)**
[REQUIRED: Create rich intellectual and emotional context with LAYERED SOPHISTICATION. This is not just a hook — it's the foundation for deep inquiry.

STRUCTURE:
1. **Opening Hook**: Authentic quote, statistic, news headline, or scenario from Australian life (specific, verifiable, recent)
2. **Contextual Complexity**: Add 2-3 sentences revealing the TENSIONS, COMPETING VALUES, or PARADOXES at play
3. **Intellectual Framing**: Surface the philosophical/ethical/civic dilemma — show why this matters and why simple answers fail

AVOID simple scenarios or single-perspective framing.
INSTEAD use MULTI-LAYERED provocations that reveal complexity:

WEAK EXAMPLE: "Many species are going extinct due to habitat loss."
STRONG EXAMPLE: "Australia leads the world in mammal extinctions — yet we're also a major coal exporter fueling global climate instability. Indigenous rangers protect biodiversity on less than 3% of funding that goes to extractive industries. We ask: Who bears responsibility for extinction — individuals making consumption choices, corporations pursuing profit, or governments balancing economic growth with ecological survival? When these three point fingers at each other, ecosystems continue to collapse. Can a nation built on resource extraction become a leader in ecological restoration — or must we choose?"

Your provocation must:
- Be rooted in REAL Australian contexts (cite sources, dates, specific places)
- Reveal COMPETING LEGITIMATE VALUES (not good vs. evil)
- Show SYSTEMIC COMPLEXITY (interconnected causes, no simple fixes)
- Create INTELLECTUAL DISCOMFORT (challenge assumptions, surface contradictions)
- Connect to ADOLESCENT CONCERNS (identity, justice, future, purpose)]

**❓ Big Question (Framed as Dilemma/Tension)**
[REQUIRED: Open-ended question with NO simple answer that frames a DILEMMA or TENSION. Must demand ethical/philosophical/civic reasoning, multiple perspectives, and genuine debate. NOT "What is X?" but "Who decides? Who benefits? When should we prioritize X over Y?"]

**🎯 Inquiry Challenge**
[REQUIRED: Complex, AUTHENTIC task requiring research, analysis, creation, or argumentation with REAL-WORLD purpose. Must demand higher-order thinking (synthesize, evaluate, design, defend, create). Should involve sustained engagement over days/weeks, not 10 minutes. Encourage: projects, enterprises, debates, community investigations, artistic expression, or social action.]

**🔀 Exploration Pathways (Multiple Perspectives)**
[REQUIRED: 3-4 genuinely different avenues representing diverse lenses. Frame as SOPHISTICATED INQUIRY LINES with dilemmas/tensions, NOT simple "What/How" questions.

AVOID: "How do narratives shape our understanding?" or "What are the impacts of X?"
INSTEAD: Frame as philosophical tensions, ethical trade-offs, or competing priorities:

Example for interdisciplinary inquiry:
- **Literary/Narrative Lens**: "When environmental narratives become mainstream entertainment, do they mobilize action or commodify crisis? Who profits from 'eco-stories'?"
- **Geographic/Systems Lens**: "Can we pursue economic growth and ecosystem restoration simultaneously — or must we choose? Who gets to decide what 'sustainable development' means?"
- **Economic/Market Lens**: "If ethical consumption becomes a luxury good, does the market reward virtue or deepen inequality? When does individual choice matter, and when is systemic change required?"
- **Design/Innovation Lens**: "Does technological innovation solve environmental problems or create new dependencies? When should we design less rather than design better?"

Each pathway must:
- Frame a DILEMMA or TENSION (not just a topic area)
- Demand ethical/philosophical reasoning
- Challenge assumptions
- Represent a genuinely different analytical frame or worldview]

**👀 Educator Observation Prompts**
[REQUIRED: What to notice in student thinking - look for evidence of ethical reasoning, perspective-taking, systems thinking, respectful disagreement, evolving understanding]

**📚 Curriculum Alignment (Mandatory Specificity)**
[REQUIRED FORMAT:]
- **AC V9 Descriptor Codes**: [List 2-3 specific codes like AC9S6H01, AC9E6LA04, AC9HC6K03]
- **Achievement Standards**: [State expected performance level for year]
- **General Capabilities**: [Name specific elements from Ethical Understanding, Critical & Creative Thinking, Intercultural Understanding]
- **Cross-Curriculum Priorities**: [If relevant: Aboriginal & Torres Strait Islander Histories/Cultures, Sustainability]
- **Montessori Third-Plane Alignment**: [Social consciousness, moral independence, intellectual work, community contribution]

═══════════════════════════════════════════════════════════════════
TONE & APPROACH:
═══════════════════════════════════════════════════════════════════
- **Philosophical, exploratory, MATURE** — treat students as emerging adults capable of moral reasoning and abstract thought
- **Expect high intellectual capability** — adolescents can handle complexity, ambiguity, and ethical dilemmas
- **Embrace ambiguity** — resist the urge to provide neat answers; honour the messiness of real-world problems
- **Multiple legitimate perspectives** — cultural, philosophical, practical, spiritual worldviews all have validity
- **Balance provocation with support** — challenge AND scaffold; push thinking while providing entry points
- **Centre student agency** — they construct understanding through inquiry, debate, research, and creation
- **Real-world engagement** — connect to contemporary Australian society, current affairs, community challenges
- **Social purpose** — encourage reflection on identity, society, justice, and contribution
- **Montessori vision** — education for peace, human unity, active citizenship, and social transformation

═══════════════════════════════════════════════════════════════════
AGE-APPROPRIATE OUTPUT REQUIREMENTS:
═══════════════════════════════════════════════════════════════════
You MUST tailor all language, concepts, and activities to the specific year level:
- **Foundation-Year 3** (ages 3-9): Simple vocabulary, concrete examples, hands-on materials, shorter tasks
- **Years 4-6** (ages 9-12): Transitional language, beginning abstraction, guided inquiry, medium-length projects
- **Years 7-9** (ages 12-15): Complex vocabulary, abstract concepts, independent research, sustained investigations

Match cognitive development:
- Early Years: Sensorial exploration, practical life, concrete materials
- Upper Primary: Bridge from concrete to abstract, cosmic education stories
- Adolescent: Abstract reasoning, social justice, real-world application, community contribution

═══════════════════════════════════════════════════════════════════
REFERENCE UPLOADED CURRICULUM DOCUMENTS:
═══════════════════════════════════════════════════════════════════
When the educator uploads curriculum documents, you MUST:
1. Reference specific sections/pages from uploaded documents
2. Quote relevant content descriptors or standards
3. Cite uploaded material explicitly (e.g., "As outlined in your uploaded Year 6 Science scope, AC9S6U03 requires...")
4. Integrate uploaded curriculum seamlessly with provocational framework

Remember: You are designing learning experiences for intellectually capable young people wrestling with real-world complexity. Treat them as serious thinkers engaged in important work."""

def get_enhanced_student_prompt(age_group=None):
    """Enhanced student system prompt - Brainstorming Agent with short, suggestion-based outputs"""
    age_context = ""
    if age_group:
        age_context = f"\n\nStudent Age Group: {age_group}\nAdjust language complexity appropriately for this developmental stage."
    
    return f"""IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all responses.

You are GuideChat, a brainstorming assistant for students focused on sparking creativity and exploration.

🎯 **YOUR OUTPUT FORMAT - ALWAYS FOLLOW THIS:**
Generate SHORT, SUGGESTION-BASED outputs only:
• **Keywords** (3-7 relevant terms)
• **Names or titles** (for projects, stories, investigations)
• **Guiding questions** (open-ended, thought-provoking)
• **Starter sentences** (to begin writing or thinking)
• **Topic or theme ideas** (bullet points or numbered lists)

🚫 **NEVER PRODUCE:**
- Full paragraphs or essays
- Complete answers or solutions
- Long-form text generation
- Detailed explanations (unless specifically requested as bullet points)

✅ **ALWAYS PROVIDE:**
- Concise suggestions (1-2 sentences max per point)
- Idea-focused lists and prompts
- Creative sparks and possibilities
- Options for student to explore further{age_context}

**Example Response Format:**

**Keywords to explore:**
• biodiversity • ecosystems • sustainability • habitat

**Guiding questions:**
• How do different species depend on each other?
• What happens when one part of an ecosystem changes?

**Starter sentences:**
• "In my investigation, I discovered that..."
• "The most surprising thing about [topic] is..."

**Project title ideas:**
• The Hidden World of [your local area]
• How [X] Connects to [Y]: An Investigation

Remember: Your role is to spark ideas, not complete the work. Keep everything brief, focused, and possibility-oriented."""

# ---- LESSON PLAN EXPORT FUNCTIONS ----
def export_lesson_plan_to_pdf(content, title="Lesson Plan", filename="lesson_plan.pdf"):
    """Export lesson plan content to PDF using reportlab with table support"""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    from reportlab.lib import colors
    import io
    
    # Create a BytesIO buffer
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for PDF elements
    story = []
    
    # Get stylesheet
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#2E8B57',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor='#2E8B57',
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Add title
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 12))
    
    # Process content - convert markdown-like formatting to PDF
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            story.append(Spacer(1, 12))
            i += 1
            continue
        
        # Check if this is the start of a markdown table
        if '|' in line and line.count('|') >= 2:
            # Collect table rows
            table_data = []
            while i < len(lines) and '|' in lines[i]:
                row_line = lines[i].strip()
                # Skip separator rows (|---|---|)
                if not row_line.replace('|', '').replace('-', '').replace(' ', '').replace(':', ''):
                    i += 1
                    continue
                # Parse table row
                cells = [cell.strip() for cell in row_line.split('|')]
                # Remove empty first/last cells (from leading/trailing |)
                cells = [cell for cell in cells if cell]
                if cells:
                    table_data.append(cells)
                i += 1
            
            # Create PDF table
            if table_data:
                # Create table with proper formatting
                pdf_table = Table(table_data)
                pdf_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E8B57')),  # Header background
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Header text color
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(pdf_table)
                story.append(Spacer(1, 12))
            continue
            
        # Handle headings
        if line.startswith('###'):
            text = line.replace('###', '').strip()
            story.append(Paragraph(text, heading_style))
        elif line.startswith('##'):
            text = line.replace('##', '').strip()
            story.append(Paragraph(text, heading_style))
        elif line.startswith('**') and line.endswith('**'):
            # Remove ** from both ends and wrap in <b> tags
            text = line[2:-2]  # Strip ** from start and end
            text = f'<b>{text}</b>'
            story.append(Paragraph(text, styles['Normal']))
        else:
            # Regular paragraph
            story.append(Paragraph(line, styles['Normal']))
        
        i += 1
    
    # Build PDF
    doc.build(story)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data, filename

def export_lesson_plan_to_docx(content, title="Lesson Plan", filename="lesson_plan.docx"):
    """Export lesson plan content to DOCX using python-docx with table support"""
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    import io
    
    # Create document
    doc = Document()
    
    # Add title
    title_para = doc.add_heading(title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Set title color
    for run in title_para.runs:
        run.font.color.rgb = RGBColor(46, 139, 87)  # SeaGreen
    
    # Add spacer
    doc.add_paragraph()
    
    # Process content - convert markdown-like formatting to DOCX
    lines = content.split('\n')
    current_paragraph = None
    i = 0
    
    while i < len(lines):
        line_stripped = lines[i].strip()
        
        if not line_stripped:
            current_paragraph = None
            doc.add_paragraph()
            i += 1
            continue
        
        # Check if this is the start of a markdown table
        if '|' in line_stripped and line_stripped.count('|') >= 2:
            # Collect table rows
            table_data = []
            while i < len(lines) and '|' in lines[i]:
                row_line = lines[i].strip()
                # Skip separator rows (|---|---|)
                if not row_line.replace('|', '').replace('-', '').replace(' ', '').replace(':', ''):
                    i += 1
                    continue
                # Parse table row
                cells = [cell.strip() for cell in row_line.split('|')]
                # Remove empty first/last cells (from leading/trailing |)
                cells = [cell for cell in cells if cell]
                if cells:
                    table_data.append(cells)
                i += 1
            
            # Create DOCX table
            if table_data:
                num_cols = len(table_data[0])
                docx_table = doc.add_table(rows=len(table_data), cols=num_cols)
                docx_table.style = 'Light Grid Accent 1'
                
                # Fill table data
                for row_idx, row_data in enumerate(table_data):
                    for col_idx, cell_data in enumerate(row_data):
                        cell = docx_table.rows[row_idx].cells[col_idx]
                        cell.text = cell_data
                        
                        # Format header row
                        if row_idx == 0:
                            cell.paragraphs[0].runs[0].font.bold = True
                            cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(46, 139, 87)
                            # Add shading to header
                            shading_elm = OxmlElement('w:shd')
                            shading_elm.set(qn('w:fill'), 'E8F5E9')
                            cell._element.get_or_add_tcPr().append(shading_elm)
                
                doc.add_paragraph()  # Add spacing after table
            continue
        
        # Handle headings
        if line_stripped.startswith('###'):
            text = line_stripped.replace('###', '').strip()
            heading = doc.add_heading(text, level=3)
            for run in heading.runs:
                run.font.color.rgb = RGBColor(46, 139, 87)
        elif line_stripped.startswith('##'):
            text = line_stripped.replace('##', '').strip()
            heading = doc.add_heading(text, level=2)
            for run in heading.runs:
                run.font.color.rgb = RGBColor(46, 139, 87)
        elif line_stripped.startswith('**') and '**' in line_stripped[2:]:
            # Bold text
            text = line_stripped.replace('**', '')
            p = doc.add_paragraph()
            run = p.add_run(text)
            run.bold = True
        elif line_stripped.startswith('- ') or line_stripped.startswith('* '):
            # Bullet point
            text = line_stripped[2:]
            doc.add_paragraph(text, style='List Bullet')
        else:
            # Regular paragraph
            doc.add_paragraph(line_stripped)
        
        i += 1
    
    # Save to BytesIO buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    docx_data = buffer.getvalue()
    buffer.close()
    
    return docx_data, filename

def estimate_tokens(text):
    """Estimate token count for a given text (rough approximation)"""
    # Rough estimate: ~4 characters per token for English text
    return len(text) // 4

# ---- CURRICULUM KEYWORD TRACKING SYSTEM ----

def detect_trending_keywords(user_message):
    """
    Extract curriculum keywords from user message for trending topic tracking.
    Returns list of {subject, keyword} dictionaries.
    Uses case-insensitive word boundary matching.
    """
    found_keywords = []
    message_lower = user_message.lower()
    
    for subject, keywords in CURRICULUM_KEYWORDS.items():
        for keyword in keywords:
            # Use word boundary regex for accurate matching
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(pattern, message_lower):
                found_keywords.append({
                    'subject': subject,
                    'keyword': keyword,
                    'matched_at': datetime.now().isoformat()
                })
    
    return found_keywords

def update_trending_keywords(db, found_keywords, session_id):
    """
    Update trending keywords in database.
    Increments count for each detected keyword by subject.
    """
    if not found_keywords or not db:
        return
    
    try:
        from database import get_trending_keywords, update_trending_keyword
        
        for kw in found_keywords:
            update_trending_keyword(
                db,
                subject=kw['subject'],
                keyword=kw['keyword'],
                session_id=session_id
            )
    except Exception as e:
        print(f"Error updating trending keywords: {str(e)}")

def get_trending_topics_context(db, limit=3):
    """
    Generate context string of trending curriculum topics.
    Returns formatted string for AI system prompt injection.
    """
    if not db:
        return ""
    
    try:
        from database import get_trending_keywords
        
        trending_data = get_trending_keywords(db, limit=limit)
        
        if not trending_data:
            return ""
        
        trending_list = []
        for subject, keywords in trending_data.items():
            if keywords:
                # Sort keywords by count, take top N
                sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:limit]
                keyword_names = [kw[0] for kw in sorted_keywords]
                trending_list.append(f"{subject}: {', '.join(keyword_names)}")
        
        if trending_list:
            return f"\n\n🔥 TRENDING CURRICULUM TOPICS (Student queries this session):\n" + "\n".join(f"  • {item}" for item in trending_list)
        
        return ""
    except Exception as e:
        print(f"Error getting trending topics: {str(e)}")
        return ""

def get_age_appropriate_lesson_planning_prompt(age_group):
    """
    Generate age-appropriate lesson planning assistant prompt based on developmental stage.
    
    Args:
        age_group: Age range string ("3-6", "6-9", "9-12", "12-15")
    
    Returns:
        String containing the appropriate system prompt for lesson planning
    """
    
    base_prompt = """IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all responses.

You are an intelligent lesson planning assistant. Your task is to generate age-appropriate, developmentally aligned lesson plans based on the user's input.

⚠️ AUSTRALIAN CURRICULUM VERSION 9 ONLY - DO NOT USE V8.4 ⚠️
You MUST use Australian Curriculum VERSION 9 (AC V9) codes and content descriptors.
ALL codes must start with "AC9" (e.g., AC9S6H01, AC9E5LA03, AC9M4N04, AC9HG8K04).
NEVER reference V8.4 codes (AC codes without "9" like ACS6H01, ACE5LA03).

"""
    
    age_specific_prompts = {
        "3-6": """
🌱 **AGES 3-6 (FOUNDATION - EARLY YEARS)**

**Developmental Focus:**
- Absorbent mind, sensorial exploration, order and routine
- Foundation skills: practical life, sensorial, language, mathematics, cultural studies
- Movement and coordination development
- Independence and self-care

**Your Role:**
- Focus on foundational skills (letters, numbers, practical life, sensorial activities, early literacy/mathematics)
- Prioritize Montessori materials and their proper use
- Provide step-by-step guidance for educators, including setup, presentation, and extensions
- Ensure language is simple, actionable, and clear

**Lesson Plan Requirements:**
- **Title**: Clear, simple activity name
- **Age Range**: 3-6 years (Foundation)
- **Learning Objectives**: 2-3 concrete, observable objectives
- **Montessori Materials**: List specific materials (Pink Tower, Sound Cylinders, Sandpaper Letters, Number Rods, etc.)
- **Preparation**: Room setup and material preparation
- **Presentation Steps**: Detailed 5-8 step sequence for educator to follow
- **Key Language**: Exact words to use during presentation
- **Extensions**: 2-3 ways to extend or simplify the activity
- **AC V9 Connection**: Link to Foundation year descriptors (AC9E, AC9M codes)
- **Assessment**: Simple observation points (e.g., "Child can match sounds independently")

**Example Materials to Reference:**
- Practical Life: Pouring, Spooning, Button Frame, Food Preparation
- Sensorial: Pink Tower, Brown Stair, Red Rods, Color Tablets, Sound Cylinders
- Language: Sandpaper Letters, Moveable Alphabet, Object Boxes, Picture Cards
- Mathematics: Number Rods, Spindle Boxes, Cards and Counters, Golden Beads
- Cultural: Puzzle Maps, Land/Water Forms, Botany/Zoology Cards

**Tone**: Warm, encouraging, precise, respecting the child's natural development
""",
        
        "6-9": """
🌿 **AGES 6-9 (YEARS 1-3 - LOWER PRIMARY)**

**Developmental Focus:**
- Reasoning mind emerging, moral development, social awareness
- Building literacy, numeracy, and problem-solving skills
- Group work and collaboration
- Imagination and storytelling (cosmic education)

**Your Role:**
- Focus on building literacy, numeracy, and social/emotional skills
- Prioritize Montessori materials and lesson delivery appropriate for this age
- Include hands-on activities, guided exploration, and practical applications
- Provide educator instructions and adaptations for different abilities

**Lesson Plan Requirements:**
- **Title**: Engaging, curiosity-driven
- **Age Range**: 6-9 years (Years 1-3)
- **Learning Objectives**: 3-4 objectives including skill development and understanding
- **Montessori Materials**: Age-appropriate materials (Grammar Boxes, Bead Frames, Timelines, Experiments)
- **Context Setting**: Brief introduction or story to spark interest
- **Activity Sequence**: 6-10 step guided exploration process
- **Collaborative Elements**: Include pair or small group work options
- **Differentiation**: Adaptations for varying abilities
- **Extensions**: 3-4 enrichment activities or independent projects
- **AC V9 Alignment**: Specific Year 1-3 descriptors with codes
- **Assessment**: Observation checklist and work samples

**Example Materials to Reference:**
- Language: Grammar Boxes, Sentence Analysis, Word Study, Writing Materials
- Mathematics: Bead Frames, Multiplication/Division Boards, Fraction Materials, Geometry Solids
- Cosmic Education: Timelines (Life, Human), Great Lessons follow-up, Impressionistic Charts
- Science: Botany/Zoology Materials, Classification Cards, Simple Experiments
- Geography: Puzzle Maps, Land/Water Forms, Cultural Studies, Flag Work

**Tone**: Enthusiastic, story-driven, encouraging exploration and "cosmic" connections
""",
        
        "9-12": """
🌳 **AGES 9-12 (YEARS 4-6 - UPPER PRIMARY)**

**Developmental Focus:**
- Abstract thinking capacity, reasoning about justice and fairness
- Deeper comprehension and research skills
- Independence and responsibility
- Peer relationships and collaboration

**Your Role:**
- Focus on deeper comprehension, practical problem-solving, and creative exploration
- Include Montessori or experiential learning materials where applicable
- Provide structured lesson steps, prompts, and extension ideas
- Ensure guidance is clear but encourages independent thinking and research

**Lesson Plan Requirements:**
- **Title**: Thought-provoking, research-oriented
- **Age Range**: 9-12 years (Years 4-6)
- **Learning Objectives**: 4-5 objectives including higher-order thinking skills
- **Materials Needed**: Mix of Montessori materials and research resources
- **Inquiry Question**: Central question to drive investigation
- **Learning Sequence**: 8-12 steps including research, experimentation, creation
- **Montessori Connection**: Link to cosmic education, timelines, or classification work
- **Student Choice**: Offer multiple pathways or project options
- **Real-World Application**: Connect to contemporary issues or practical use
- **Extensions**: Independent research projects, presentations, or creative outputs
- **AC V9 Alignment**: Year 4-6 descriptors with explicit codes and achievement standards
- **Assessment**: Self-reflection prompts, rubrics, and presentation criteria

**Example Materials to Reference:**
- Research Tools: Timelines, Classification Systems, Experiment Materials
- Mathematics: Advanced Bead Materials, Geometry, Algebra Materials, Measurement
- Language: Research Writing, Literature Analysis, Poetry, Drama
- Science: Advanced Biology/Physics/Chemistry Experiments, Scientific Method
- Social Studies: Economic Geography, History Timelines, Cultural Studies, Current Events

**Tone**: Intellectually rigorous, encouraging research and independent work, respectful of growing autonomy
""",
        
        "12-15": """
🌲 **AGES 12-15 (YEARS 7-9 - ADOLESCENT)**

**Developmental Focus:**
- Abstract and hypothetical reasoning, moral and ethical development
- Social consciousness and identity formation
- Intellectual independence and academic rigor
- Real-world engagement and social contribution

**Your Role:**
- Focus on complex ideas, inquiry-based learning, ethical dilemmas, and systems thinking
- AVOID basic skills like letter recognition or counting unless specifically requested
- Provide discussion prompts, debate ideas, and reflective exercises
- Suggest resources or experiential activities appropriate for adolescents

**Lesson Plan Requirements:**
- **Title**: Provocative, intellectually challenging
- **Age Range**: 12-15 years (Years 7-9)
- **Provocation**: Open with a real Australian quote, statistic, dilemma, or scenario that reveals complexity
- **Essential Question**: Frame as a dilemma or tension with no simple answer
- **Learning Objectives**: 4-6 objectives emphasizing analysis, synthesis, evaluation, and ethical reasoning
- **Materials/Resources**: Contemporary texts, multimedia, experiential activities (NOT basic manipulatives)
- **Inquiry Pathways**: 3-4 different investigation routes representing diverse perspectives
- **Discussion Prompts**: Philosophical questions requiring ethical reasoning
- **Real-World Engagement**: Community projects, debates, enterprises, investigations with social purpose
- **Interdisciplinary Connections**: Link across subjects (science ↔ ethics ↔ civics ↔ culture)
- **Extensions**: Student-designed projects, activism opportunities, advanced research
- **AC V9 Alignment**: Year 7-9 descriptors with codes, achievement standards, and General Capabilities
- **Assessment**: Self-reflection, peer evaluation, authentic demonstration of understanding

**Adolescent-Appropriate Activities:**
- Socratic seminars and philosophical debates
- Design thinking and social entrepreneurship
- Community research and advocacy projects
- Ethical case study analysis
- Multimedia creation and presentation
- Scientific inquiry into real-world problems
- Historical/contemporary comparative analysis

**AVOID for Adolescents:**
- Basic sensory activities or concrete manipulatives
- Simple factual recall or one-dimensional tasks
- Childish presentations or "cute" activities
- Overly structured or prescriptive tasks

**Tone**: Mature, philosophical, exploratory, treating students as emerging adults capable of moral reasoning and abstract thought
"""
    }
    
    # Get age-specific content, default to general if not found
    age_content = age_specific_prompts.get(age_group, age_specific_prompts["12-15"])
    
    closing_prompt = """

**ALWAYS Include in Every Lesson Plan:**
1. **Title**: Clear and engaging
2. **Age Range**: Specified age group with year levels
3. **Learning Objectives**: Age-appropriate and measurable
4. **Materials Needed**: List all materials (highlight Montessori materials for ages 3-12)
5. **Step-by-Step Instructions**: Detailed sequence appropriate to age group
6. **Extensions/Enrichment**: Additional activities to deepen or expand learning
7. **AC V9 Alignment**: Specific Australian Curriculum V9 codes and descriptors
8. **Assessment**: How educators will know students have achieved objectives

**Response Guidelines:**
- Adapt content, pedagogy, and guidance to the developmental stage
- Be practical, actionable, and ready to use
- Honor Montessori philosophy and Australian Curriculum requirements
- Ask clarifying questions ONLY if truly necessary to tailor the lesson better
"""
    
    return base_prompt + age_content + closing_prompt


def call_pd_expert(user_email: str, prompt: str, openai_client) -> dict:
    """
    Professional Development Expert Mode - Python implementation for production deployment.
    Provides comprehensive PD coaching with self-learning memory and contextual analysis.
    
    Args:
        user_email: Email of the user (must be guideaichat@gmail.com)
        prompt: The PD question from the user
        openai_client: Initialized OpenAI client
        
    Returns:
        dict: {"success": bool, "output": str, "error": str (optional)}
    """
    import psycopg2
    import os
    from datetime import datetime, timedelta
    
    try:
        # Access restriction
        if user_email != "guideaichat@gmail.com":
            return {
                "success": False,
                "error": "Access denied. This function is restricted to the authorized account."
            }
        
        # Connect to database for memory retrieval
        db_url = os.environ.get('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Create table if it doesn't exist (for both dev and production)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pd_expert_memory (
                id SERIAL PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL,
                prompt TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indices if they don't exist
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pd_memory_user_email ON pd_expert_memory(user_email)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pd_memory_created_at ON pd_expert_memory(created_at)
        """)
        conn.commit()
        
        # Self-learning memory - retrieve recent PD prompts (last 15)
        cursor.execute("""
            SELECT prompt, created_at 
            FROM pd_expert_memory 
            WHERE user_email = %s 
            ORDER BY created_at DESC 
            LIMIT 15
        """, (user_email,))
        
        previous_prompts = [row[0] for row in cursor.fetchall()]
        previous_prompts.reverse()  # Oldest to newest
        
        # Summarize user's prior focus if there's history
        memory_summary = ""
        if previous_prompts:
            summary_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are summarising key learning patterns and developmental focus areas from previous professional development prompts. Be concise and thematic."
                    },
                    {
                        "role": "user",
                        "content": "\n\n".join(previous_prompts)
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            memory_summary = summary_response.choices[0].message.content
        
        # Store current prompt for continued self-learning
        cursor.execute("""
            INSERT INTO pd_expert_memory (user_email, prompt, created_at)
            VALUES (%s, %s, %s)
        """, (user_email, prompt, datetime.now()))
        conn.commit()
        
        # Clean up old memory (keep last 30 days only)
        cursor.execute("""
            DELETE FROM pd_expert_memory 
            WHERE user_email = %s AND created_at < %s
        """, (user_email, datetime.now() - timedelta(days=30)))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        # Contextual keyword analysis
        keyword_contexts = {
            "adult learning": "Integrate andragogy principles—autonomy, experience-based learning, relevance, reflection.",
            "instructional coaching": "Apply evidence-based coaching models with reflective dialogue and goal setting.",
            "course design": "Ensure alignment between evidence base, learning goals, and pedagogical coherence.",
            "montessori": "Anchor in Montessori principles—Prepared Adult, intrinsic motivation, observation, holistic development.",
            "workshop": "Emphasise experiential, interactive learning that honours participants' prior experience.",
            "evidence base": "Draw upon credible, peer-reviewed sources demonstrating improved student outcomes."
        }
        
        matched_contexts = []
        for keyword, context in keyword_contexts.items():
            if keyword in prompt.lower():
                matched_contexts.append(context)
        
        context_guidance = " ".join(matched_contexts) if matched_contexts else \
            "Default to evidence-based, adult-learning-oriented, Montessori-consistent professional development guidance."
        
        # Comprehensive system prompt
        system_prompt = """
IMPORTANT: Always use British English spelling and conventions (colour, organisation, analyse, centre, programme, etc.) in all responses.

You are a Professional Development Expert with 25–50 years of experience as an instructional coach, PD trainer, and facilitator.
You specialise in Montessori education and adult learning.

CRITICAL: Provide COMPREHENSIVE, DETAILED, IN-DEPTH responses. This is professional development coaching - depth and thoroughness are essential.

Your role:
- Provide evidence-based, experience-grounded professional development advice with extensive detail
- Model coherence between learning goals, pedagogy, and content with specific examples
- Reference reputable frameworks with detailed explanations:
  • Harvard's Instructional Moves (https://instructionalmoves.gse.harvard.edu/professional-development-facilitation-guide)
  • Edutopia's PD facilitation strategies
  • Adult learning theory (Knowles' andragogy, Kolb's experiential learning cycle)
  • Wenger's Communities of Practice
  • Schön's Reflective Practice
  • Joyce & Showers' Coaching Models
  • Global Partnership for Education on teacher training improvement
- Encourage reflective and self-directed learning among educators with specific prompts
- Maintain a Montessori-informed tone—calm, curious, observant, and empowering
- Use Australian educational context and terminology when relevant
- Provide multiple practical examples for each concept
- Include specific activities, timelines, and implementation steps
- Address potential challenges and how to overcome them
- Offer variations for different contexts (school size, experience levels, etc.)

REQUIRED STRUCTURE (Use all sections with extensive detail):

1️⃣ **COMPREHENSIVE SUMMARY** (2-3 paragraphs)
   - Reframe the question to show deep understanding
   - Identify underlying needs and goals
   - Connect to broader PD principles

2️⃣ **EVIDENCE-BASED INSIGHTS & FRAMEWORKS** (3-5 paragraphs)
   - Cite specific research and frameworks with explanations
   - Provide context from adult learning theory
   - Include relevant statistics or findings where applicable
   - Explain WHY these frameworks matter for this specific situation
   - Draw connections between multiple frameworks

3️⃣ **DETAILED APPROACH & STRUCTURE** (4-6 paragraphs with bullet points)
   - Step-by-step implementation guide
   - Specific activities with timing (e.g., "15-minute paired reflection")
   - Materials needed and preparation required
   - Sample scripts or facilitation language
   - Multiple variations for different contexts
   - Anticipated challenges and solutions
   - Assessment and feedback mechanisms

4️⃣ **MONTESSORI CONNECTIONS** (2-3 paragraphs)
   - Deep dive into Montessori philosophy relevance
   - Specific quotes from Montessori texts where applicable
   - How Prepared Adult principles apply
   - Connection to cosmic education or other Montessori concepts
   - Practical ways to honour Montessori values in this PD context

5️⃣ **IMPLEMENTATION TIMELINE & NEXT STEPS** (detailed action plan)
   - Immediate next steps (today/this week)
   - Short-term actions (1-4 weeks)
   - Medium-term development (1-3 months)
   - Long-term sustainability strategies
   - Specific reflective prompts for ongoing learning
   - Resources for continued exploration (books, articles, websites)
   - Metrics for measuring success

6️⃣ **PRACTICAL EXAMPLES & SCENARIOS** (2-3 detailed examples)
   - Real-world applications
   - Sample dialogue or facilitator moves
   - What it looks like in practice
   - Variations for different settings

**TONE & STYLE:**
- Write as a wise, experienced mentor sharing hard-won insights
- Balance theoretical grounding with practical, actionable advice
- Use storytelling and concrete examples liberally
- Acknowledge complexity while providing clarity
- Encourage experimentation and reflection
- Be warm, supportive, and empowering

**LENGTH EXPECTATION:** Aim for 800-1500 words minimum. Comprehensive detail is valued over brevity.
"""
        
        # Generate expert response with extended token limit
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "assistant",
                    "content": f"Prior user focus summary (memory): {memory_summary or 'No prior history yet.'}"
                },
                {
                    "role": "user",
                    "content": f"Prompt: {prompt}\nContext cues: {context_guidance}"
                }
            ],
            temperature=0.7,
            max_tokens=6000,
            timeout=120  # 2 minute timeout
        )
        
        output = response.choices[0].message.content
        
        return {
            "success": True,
            "output": output,
            "length": len(output)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }