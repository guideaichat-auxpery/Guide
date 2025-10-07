import streamlit as st
import os
from openai import OpenAI
from datetime import datetime
import json
import re

# ---- CURRICULUM KEYWORD MAPPING ----
# Maps subjects to key curriculum terms from AC V9 descriptors
CURRICULUM_KEYWORDS = {
    "Geography": [
        # Multi-word AC V9 topic names (Year 7-9)
        "Geographies of Interconnections", "geographies of interconnections",
        "Biomes and Food Security", "biomes and food security",
        "Water in the World", "water in the world",
        "Place and Liveability", "place and liveability",
        "Landforms and Landscapes", "landforms and landscapes",
        "Changing Nations", "changing nations",
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

def get_montessori_system_prompt():
    """Get Montessori-focused system prompt with authentic texts and Australian Curriculum V.9 integration"""
    base_prompt = """You are Guide, a warm and knowledgeable Montessori educational planning companion. You embody Maria Montessori's philosophy and provide guidance grounded in authentic Montessori principles while ensuring alignment with the Australian Curriculum V.9 for auditing purposes.

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
                    subject=None, subjects=None, year_level=None, curriculum_type="Blended", use_conversation_history=True):
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
    """
    try:
        # Determine max_tokens if not specified
        if max_tokens is None:
            max_tokens = get_max_tokens_for_user_type("student" if is_student else "educator")
        
        # Use enhanced prompts if no custom system prompt provided
        if system_prompt is None:
            if is_student:
                system_prompt = get_enhanced_student_prompt(age_group)
            else:
                system_prompt = get_enhanced_educator_prompt()
        
        # Manage conversation history if enabled
        conversation_messages = messages
        if use_conversation_history and len(messages) > 0:
            conversation_messages = get_conversation_context(messages, max_messages=10)
        
        # Extract curriculum keywords from user input
        keyword_context = ""
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
                all_keywords = []
                for subj in subject_list:
                    found_keywords = extract_curriculum_keywords(subj, last_user_message)
                    if found_keywords:
                        all_keywords.extend(found_keywords)
                
                # Create keyword context if keywords found
                if all_keywords:
                    unique_keywords = list(set(all_keywords))
                    keyword_context = f"🎯 Curriculum Keywords Detected: {', '.join(unique_keywords)}\nFocus on these curriculum-aligned concepts in your response.\n\n"
        
        # Fetch curriculum context for all selected subjects
        curriculum_context = ""
        
        # Determine which subjects to process
        subject_list = subjects if subjects else ([subject] if subject else [])
        
        if subject_list:
            # Get year level (from parameter or auto-map from age)
            target_year_level = year_level
            if not target_year_level and age_group:
                target_year_level = get_primary_year_level(age_group)
            
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
        
        # Add curriculum context as system message if available
        if curriculum_context:
            api_messages.append({
                "role": "system", 
                "content": f"Curriculum Context:\n{curriculum_context}"
            })
        
        # Add conversation messages
        api_messages.extend(conversation_messages)
        
        # Make API call with enhanced parameters
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=api_messages,
            max_tokens=max_tokens,
            temperature=0.75,  # Balanced creativity as per JavaScript implementation
            presence_penalty=0.3,  # Encourage diverse responses
            frequency_penalty=0.2  # Reduce repetition
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling OpenAI API: {str(e)}")
        return None

def get_max_tokens_for_user_type(user_type):
    """Get appropriate token limit based on user type"""
    if user_type in ["educator"]:
        return 3000  # Enhanced for ChatGPT-level detail (approximately 10,000 words)
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

def get_primary_year_level(age_group):
    """Get the primary/middle year level for an age group (for curriculum lookup)"""
    year_levels = map_age_to_year_levels(age_group)
    if not year_levels:
        return None
    # Return the middle year level for the age group
    if "Foundation" in year_levels:
        return "Foundation"
    elif len(year_levels) >= 2:
        return year_levels[1]  # Return middle year (e.g., Year 2 for 6-9, Year 5 for 9-12)
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

def get_enhanced_educator_prompt():
    """Enhanced provocational educator prompt with MANDATORY AC V9 alignment and adolescent intellectual sophistication"""
    return """You are GuideChat, an advanced AI teaching assistant that designs learning experiences grounded in Montessori philosophy and the Australian Curriculum V9.

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
    """Enhanced student system prompt based on GuideChat JavaScript implementation"""
    age_context = ""
    if age_group:
        age_context = f"\n\nStudent Age Group: {age_group}\nAdjust language complexity and scaffolding appropriately for this developmental stage."
    
    return f"""You are GuideChat, a supportive AI learning companion for students.

Your goal is to help learners think critically and independently using Montessori principles.
Provide **scaffolded guidance**, NOT full answers.
Encourage curiosity, discovery, and reflection.{age_context}

When helping students:
- Offer hints, guiding questions, or examples that lead to discovery
- Connect learning to Montessori materials or real-life experiences when possible
- Break complex problems into smaller, manageable steps
- Avoid giving complete answers—guide toward understanding
- Use a warm, encouraging, patient tone
- End responses with one reflective question to encourage deeper thought
- Celebrate effort and thinking process, not just correct answers
- Make connections to the cosmic curriculum and the student's place in the universe

Remember: Your role is to guide, not to do the work for them. 
Help them develop independence, critical thinking, and a love of learning."""

# ---- LESSON PLAN EXPORT FUNCTIONS ----
def export_lesson_plan_to_pdf(content, title="Lesson Plan", filename="lesson_plan.pdf"):
    """Export lesson plan content to PDF using reportlab"""
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
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
    for line in lines:
        line = line.strip()
        if not line:
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
            text = line.replace('**', '<b>').replace('**', '</b>')
            story.append(Paragraph(text, styles['Normal']))
        else:
            # Regular paragraph
            story.append(Paragraph(line, styles['Normal']))
    
    # Build PDF
    doc.build(story)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data, filename

def export_lesson_plan_to_docx(content, title="Lesson Plan", filename="lesson_plan.docx"):
    """Export lesson plan content to DOCX using python-docx"""
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
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
    
    for line in lines:
        line_stripped = line.strip()
        
        if not line_stripped:
            current_paragraph = None
            doc.add_paragraph()
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