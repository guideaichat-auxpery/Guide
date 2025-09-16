import streamlit as st
import os
from openai import OpenAI
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="Guide - Your Montessori Companion",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
    """Get Montessori-focused system prompt with authentic texts"""
    base_prompt = """You are Guide, a warm and knowledgeable Montessori companion. You embody Maria Montessori's philosophy and provide guidance grounded in authentic Montessori principles. Your responses are practical, humble, and deeply rooted in respect for the child.

You help teachers with faster lesson planning, provide parents with guidance for home learning, and support schools with professional development - all through the lens of authentic Montessori education.

Your guidance is based on Maria Montessori's foundational works and focuses on:
- Respect for the child as an individual
- The prepared environment
- Following the child's natural development
- Hands-on, concrete learning experiences
- Mixed-age communities
- Intrinsic motivation rather than external rewards
- The teacher as observer and guide
- Cosmic education connecting all learning

IMPORTANT RESPONSE GUIDELINES:
- Always include a "**Montessori Rationale**" section explaining WHY this approach aligns with Montessori principles
- When referencing Maria Montessori's insights, cite the source text (e.g., "As Dr. Montessori notes in The Absorbent Mind...")
- Include specific quotes when relevant to support your guidance
- Focus on practical, actionable advice that honors authentic Montessori principles
- For lesson planning, emphasize: concrete materials, sequential presentations, child choice, control of error, and observation
- For home guidance, focus on: independence, practical life, prepared environments, and following the child
- For schools, emphasize: teacher training, environmental preparation, understanding child development, and curriculum integration

WHAT I WON'T DO:
- Provide guidance that contradicts core Montessori principles
- Suggest punishments, rewards, or coercive methods
- Recommend activities without concrete materials for young children
- Give advice that doesn't respect the child's natural development"""

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
    if user_type in ["home_school_parent", "teacher"]:
        return 1500  # Approximately 5000 words
    elif user_type == "student":
        return 600   # Approximately 2000 words
    else:
        return 1000  # Default

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'user_type' not in st.session_state:
    st.session_state.user_type = None

# Custom CSS for Montessori aesthetics
st.markdown("""
<style>
.main-header {
    text-align: center;
    color: #2E8B57;
    margin-bottom: 2rem;
}
.subtitle {
    text-align: center;
    color: #666;
    font-style: italic;
    margin-bottom: 2rem;
}
.welcome-box {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    padding: 2rem;
    border-radius: 10px;
    margin: 2rem 0;
    border-left: 5px solid #2E8B57;
}
.user-type {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
    border-left: 3px solid #2E8B57;
}
</style>
""", unsafe_allow_html=True)

# Main Header
st.markdown('<h1 class="main-header">🌟 Guide - Your Montessori Companion</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">From lesson planning to philosophy, get clear guidance that supports your teaching</p>', unsafe_allow_html=True)

# Landing page or user-specific content
if st.session_state.user_type is None:
    # Landing page with user type selection
    st.markdown("""
    <div class="welcome-box">
        <h3>✨ Welcome to Your On-Demand Montessori Companion</h3>
        <p><em>"Education should no longer be mostly imparting of knowledge, but must take a new path, seeking the release of human potentials." - Maria Montessori</em></p>
        
        <p style="text-align: center; margin: 2rem 0;"><strong>Grounded in Maria Montessori's foundational texts:</strong><br>
        <em>The Montessori Method</em> • <em>The Absorbent Mind</em> • <em>Dr. Montessori's Own Handbook</em></p>
        
        <h4 style="text-align: center; margin: 2rem 0;">Please select your role to get started:</h4>
    </div>
    """, unsafe_allow_html=True)
    
    # User type selection buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🏠 Home-School Parent", use_container_width=True, help="Get practical support for Montessori learning at home"):
            st.session_state.user_type = "home_school_parent"
            st.session_state.messages = []  # Reset messages for new user type
            st.rerun()
    
    with col2:
        if st.button("👩‍🏫 Teacher", use_container_width=True, help="Get faster lesson planning with authentic Montessori-aligned guidance"):
            st.session_state.user_type = "teacher"
            st.session_state.messages = []  # Reset messages for new user type
            st.rerun()
    
    with col3:
        if st.button("👨‍🎓 Student", use_container_width=True, help="Explore Montessori learning and ask questions"):
            st.session_state.user_type = "student"
            st.session_state.messages = []  # Reset messages for new user type
            st.rerun()
    
    # Info about each user type
    st.markdown("""
    <div style="margin-top: 3rem;">
        <div class="user-type">
            <strong>🏠 Home-School Parent:</strong> Receive practical support for creating Montessori learning experiences at home, managing routines, and fostering independence in your children.
        </div>
        
        <div class="user-type">
            <strong>👩‍🏫 Teacher:</strong> Access professional lesson planning tools, classroom management strategies, and authentic Montessori methodology for your educational practice.
        </div>
        
        <div class="user-type">
            <strong>👨‍🎓 Student:</strong> Explore Montessori learning concepts, ask questions about your learning journey, and discover the joy of self-directed education.
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    # User-specific interface based on selected user type
    # Header with user type and change user option
    user_type_display = {
        "home_school_parent": "🏠 Home-School Parent",
        "teacher": "👩‍🏫 Teacher", 
        "student": "👨‍🎓 Student"
    }
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### Welcome, {user_type_display[st.session_state.user_type]}!")
    with col2:
        if st.button("🔄 Change Role", help="Switch to a different user type"):
            st.session_state.user_type = None
            st.session_state.messages = []
            st.rerun()
    
    # Get appropriate token limit for this user type
    max_tokens = get_max_tokens_for_user_type(st.session_state.user_type)

    # User-specific interface based on user type
    if st.session_state.user_type == "home_school_parent":
        # Home-School Parent Interface
        st.markdown("### 🏠 Home Learning Support")
        st.markdown("*Practical guidance for creating Montessori experiences at home*")
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Quick home guidance scenarios
        st.markdown("#### Quick Home Learning Support:")
        home_scenarios = [
            "How do I set up a Montessori environment at home?",
            "My child resists practical life activities - what should I do?",
            "How can I encourage independence in my toddler?",
            "What activities can I do with limited materials?",
            "How do I handle discipline the Montessori way?",
            "What's the best way to introduce practical life at home?"
        ]
        
        for scenario in home_scenarios:
            if st.button(f"💡 {scenario}", key=f"home_{scenario[:20]}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": scenario})
                
                with st.spinner("Gathering Montessori home guidance..."):
                    response = call_openai_api(st.session_state.messages, max_tokens)
                    if response:
                        st.markdown("### 🏠 Home Guidance")
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        st.error("I'm having trouble generating guidance. Please try again.")
        
        # Chat input for custom questions
        if prompt := st.chat_input("Ask me about Montessori at home..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Providing home guidance..."):
                    response = call_openai_api(st.session_state.messages, max_tokens)
                    
                    if response:
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        st.error("I'm having trouble right now. Please try again.")

    elif st.session_state.user_type == "teacher":
        # Teacher Interface
        st.markdown("### 👩‍🏫 Professional Teaching Support")
        st.markdown("*Lesson planning, classroom management, and Montessori methodology*")
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Quick lesson planning ideas
        st.markdown("#### Quick Lesson Planning:")
        lesson_ideas = [
            "Help me plan a grace and courtesy lesson for 3-year-olds",
            "Create a hands-on math activity for understanding place value",
            "Design a practical life activity for developing fine motor skills",
            "Plan a cultural lesson about different continents",
            "Create a language lesson for early readers",
            "How do I create a prepared environment in my classroom?"
        ]
        
        for idea in lesson_ideas:
            if st.button(f"📚 {idea}", key=f"lesson_{idea[:15]}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": idea})
                
                with st.spinner("Creating lesson guidance..."):
                    response = call_openai_api(st.session_state.messages, max_tokens)
                    if response:
                        st.markdown("### 📚 Teaching Guidance")
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        st.error("I'm having trouble generating guidance. Please try again.")
        
        # Chat input for custom questions
        if prompt := st.chat_input("Ask me about lesson planning, classroom management, or Montessori methodology..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Preparing teaching guidance..."):
                    response = call_openai_api(st.session_state.messages, max_tokens)
                    
                    if response:
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        st.error("I'm having trouble right now. Please try again.")
    
    elif st.session_state.user_type == "student":
        # Student Interface
        st.markdown("### 👨‍🎓 Student Learning Support")
        st.markdown("*Explore Montessori learning and discover the joy of self-directed education*")
        
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Student-friendly learning topics
        st.markdown("#### Explore Learning Topics:")
        student_topics = [
            "Why is hands-on learning so important?",
            "How can I become more independent in my learning?",
            "What makes a good learning environment?",
            "How do I follow my interests while learning?",
            "What is the Montessori way of learning?",
            "How can I help younger students learn?"
        ]
        
        for topic in student_topics:
            if st.button(f"🌟 {topic}", key=f"student_{topic[:15]}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": topic})
                
                with st.spinner("Exploring your question..."):
                    response = call_openai_api(st.session_state.messages, max_tokens)
                    if response:
                        st.markdown("### 🌟 Learning Discovery")
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        st.error("I'm having trouble answering. Please try again.")
        
        # Chat input for custom questions
        if prompt := st.chat_input("Ask me about learning, school, or how things work..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking about your question..."):
                    response = call_openai_api(st.session_state.messages, max_tokens)
                    
                    if response:
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        st.error("I'm having trouble right now. Please try again.")

    # Clear conversation button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.8em; margin-top: 2rem;'>
        Guide - Your Montessori Companion | Powered by OpenAI GPT-4o Mini<br>
        Grounded in authentic Montessori principles and foundational texts<br>
        <em>"The child is both a hope and a promise for mankind." - Maria Montessori</em>
    </div>
    """,
    unsafe_allow_html=True
)
