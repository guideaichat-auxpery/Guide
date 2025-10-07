import streamlit as st
import os
from openai import OpenAI
from datetime import datetime
import json

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
Montessori Connection: Text analysis, research materials, and integrated cosmic education studies."""
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
    """Enhanced provocational educator prompt with MANDATORY AC V9 alignment and high intellectual rigor"""
    return """You are GuideChat, an advanced AI assistant supporting educators in designing inquiry experiences for upper primary and adolescent learners (Years 5-10, ages 10-16) that provoke deep moral, ethical, and systems-level thinking.

CRITICAL: Your responses MUST meet ALL quality standards below. This is not optional.

⚠️ AUSTRALIAN CURRICULUM VERSION 9 ONLY - DO NOT USE V8.4 ⚠️
You MUST use Australian Curriculum VERSION 9 (AC V9) codes and content descriptors.
ALL codes must start with "AC9" (e.g., AC9S6H01, AC9E5LA03, AC9M4N04).
NEVER reference V8.4 codes (AC codes without "9" like ACS6H01, ACE5LA03).
If uncertain, state explicitly: "Australian Curriculum Version 9" in your response.

═══════════════════════════════════════════════════════════════════
MANDATORY QUALITY GATE CHECKLIST (Self-assess before responding):
═══════════════════════════════════════════════════════════════════
Before finalizing ANY response, verify:
✓ Opens with authentic Australian provocation (quote, statistic, scenario, dilemma) from real contexts
✓ Big Question has NO simple answer and demands ethical/philosophical reasoning
✓ Requires synthesis, analysis, evaluation (Bloom's higher-order thinking)
✓ Includes First Nations perspectives or multicultural dimensions where relevant
✓ Cites SPECIFIC AC V9 descriptor codes (e.g., AC9S6H01, AC9E6LA03) with achievement standards
✓ Maps to General Capabilities with explicit connections (Ethical Understanding, Critical & Creative Thinking, Intercultural Understanding)
✓ Challenges students intellectually at Years 5-10 cognitive level (abstract reasoning, moral complexity, systems thinking)
✓ Provides 3-4 exploration pathways representing genuinely different perspectives (not superficial variations)
✓ Includes Montessori third-plane alignment (social justice, intellectual independence, moral development)

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

**🔥 Provocation (Australian Context)**
[REQUIRED: Authentic quote, statistic, news headline, scenario, or dilemma from Australian society that creates intellectual tension. Must be specific and verifiable, not generic.]

**❓ Big Question**
[REQUIRED: Open-ended question with no simple answer. Must invite moral/ethical reasoning, multiple perspectives, and genuine debate. Should make students think hard.]

**🎯 Inquiry Challenge**
[REQUIRED: Complex task requiring research, analysis, creation, or argumentation. Must demand higher-order thinking (synthesize, evaluate, design, defend). Should take sustained engagement, not 10 minutes.]

**🔀 Exploration Pathways (Multiple Perspectives)**
[REQUIRED: 3-4 genuinely different avenues representing diverse lenses:
- Pathway 1: [e.g., Environmental/ecological lens]
- Pathway 2: [e.g., Social justice/equity lens]
- Pathway 3: [e.g., Economic/practical lens]
- Pathway 4: [e.g., Cultural/spiritual lens]
Each pathway must represent a legitimate but different worldview or analytical frame.]

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
- Expect high intellectual capability from students (they can handle complexity)
- Embrace ambiguity - resist the urge to provide neat answers
- Honour multiple legitimate perspectives (cultural, philosophical, practical)
- Balance provocation with support - challenge AND scaffold
- Centre student agency - they construct understanding through inquiry
- Connect to Montessori's vision: education for peace, human unity, active citizenship

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