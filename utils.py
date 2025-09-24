import streamlit as st
import os
from openai import OpenAI
from datetime import datetime

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

def call_openai_api(messages, max_tokens=1000):
    """Call OpenAI API with error handling and configurable token limit"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": get_montessori_system_prompt()}] + messages,
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling OpenAI API: {str(e)}")
        return None

def get_max_tokens_for_user_type(user_type):
    """Get appropriate token limit based on user type"""
    if user_type in ["educator"]:
        return 1500  # Approximately 5000 words for educational planning
    elif user_type == "student":
        return 600   # Approximately 2000 words
    else:
        return 1000  # Default