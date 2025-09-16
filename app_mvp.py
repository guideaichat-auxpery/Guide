import streamlit as st
import os
from openai import OpenAI
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="Maria - Your Montessori Companion",
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
    base_prompt = """You are Maria, a warm and knowledgeable Montessori companion. You embody Maria Montessori's philosophy and provide guidance grounded in authentic Montessori principles. Your responses are practical, humble, and deeply rooted in respect for the child.

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

Always provide practical, actionable advice that honors Montessori principles. When discussing lesson planning, emphasize concrete materials, sequential presentations, and child choice. For home guidance, focus on independence, practical life, and prepared environments. For schools, emphasize teacher training, environmental preparation, and understanding child development.

Reference the foundational Montessori texts when relevant, but keep your language accessible and practical."""

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

def call_openai_api(messages):
    """Call OpenAI API with error handling"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": get_montessori_system_prompt()}] + messages,
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling OpenAI API: {str(e)}")
        return None

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

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
st.markdown('<h1 class="main-header">🌟 Maria - Your Montessori Companion</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">From lesson planning to philosophy, get clear guidance that supports your teaching</p>', unsafe_allow_html=True)

# Welcome message
st.markdown("""
<div class="welcome-box">
    <h3>✨ An On-Demand Montessori Companion</h3>
    <p><em>"Education should no longer be mostly imparting of knowledge, but must take a new path, seeking the release of human potentials." - Maria Montessori</em></p>
    
    <div class="user-type">
        <strong>👩‍🏫 For Teachers:</strong> Get faster lesson planning with authentic Montessori-aligned guidance
    </div>
    
    <div class="user-type">
        <strong>👨‍👩‍👧‍👦 For Parents:</strong> Receive practical support for Montessori learning at home
    </div>
    
    <div class="user-type">
        <strong>🏫 For Schools:</strong> Access professional development and curriculum guidance
    </div>
    
    <p style="text-align: center; margin-top: 1rem;"><strong>Grounded in Maria Montessori's foundational texts:</strong><br>
    <em>The Montessori Method</em> • <em>The Absorbent Mind</em> • <em>Dr. Montessori's Own Handbook</em></p>
</div>
""", unsafe_allow_html=True)

# Main tabs for core functionality
main_tabs = st.tabs(["💬 Ask Maria", "📚 Lesson Planning", "🏠 Home Guidance", "🏫 School Support"])

with main_tabs[0]:  # Ask Maria - General Montessori Guidance
    st.markdown("### 💬 Chat with Maria")
    st.markdown("*Ask questions about Montessori philosophy, methods, and classroom guidance*")
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me about Montessori education, child development, or teaching approaches..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Reflecting on your question..."):
                response = call_openai_api(st.session_state.messages)
                
                if response:
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error("I'm having trouble right now. Please try again.")

with main_tabs[1]:  # Lesson Planning
    st.markdown("### 📚 Lesson Planning Assistant")
    st.markdown("*Get help creating Montessori-aligned lesson plans and activities*")
    
    # Quick lesson planning prompts
    st.markdown("#### Quick Start Examples:")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🌱 Practical Life Activity", use_container_width=True):
            example_prompt = "Help me design a practical life activity for 3-6 year olds that develops concentration and fine motor skills."
            st.session_state.messages.append({"role": "user", "content": example_prompt})
            st.rerun()
    
    with col2:
        if st.button("🔢 Sensorial Material", use_container_width=True):
            example_prompt = "Suggest a sensorial material exploration for helping children understand size and dimension."
            st.session_state.messages.append({"role": "user", "content": example_prompt})
            st.rerun()
    
    col3, col4 = st.columns(2)
    
    with col3:
        if st.button("📖 Language Lesson", use_container_width=True):
            example_prompt = "Create a language lesson using Montessori materials for beginning readers."
            st.session_state.messages.append({"role": "user", "content": example_prompt})
            st.rerun()
    
    with col4:
        if st.button("🔢 Math Presentation", use_container_width=True):
            example_prompt = "Design a math presentation using golden beads for teaching place value."
            st.session_state.messages.append({"role": "user", "content": example_prompt})
            st.rerun()
    
    # Lesson planning text area
    lesson_request = st.text_area(
        "Describe the lesson or activity you'd like help with:",
        placeholder="Example: I need a math lesson for 6-9 year olds about addition using concrete materials...",
        height=100
    )
    
    if st.button("✨ Create Lesson Plan", use_container_width=True):
        if lesson_request:
            enhanced_prompt = f"Please help me create a detailed Montessori lesson plan for: {lesson_request}. Include materials needed, presentation steps, variations, and extensions."
            st.session_state.messages.append({"role": "user", "content": enhanced_prompt})
            st.rerun()
        else:
            st.warning("Please describe what lesson you'd like help with.")

with main_tabs[2]:  # Home Guidance
    st.markdown("### 🏠 Home Learning Support")
    st.markdown("*Practical guidance for parents implementing Montessori principles at home*")
    
    # Common home scenarios
    st.markdown("#### Common Questions:")
    home_scenarios = [
        "How do I set up a prepared environment at home?",
        "My child won't concentrate - what should I do?",
        "What activities can I do with limited materials?",
        "How do I handle discipline the Montessori way?",
        "What's the best way to introduce practical life at home?"
    ]
    
    for scenario in home_scenarios:
        if st.button(f"💡 {scenario}", key=f"home_{scenario[:20]}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": scenario})
            st.rerun()
    
    # Custom home question
    home_question = st.text_area(
        "Ask your specific question about Montessori at home:",
        placeholder="Example: How can I help my 4-year-old become more independent with morning routines?",
        height=100
    )
    
    if st.button("🌟 Get Home Guidance", use_container_width=True):
        if home_question:
            st.session_state.messages.append({"role": "user", "content": home_question})
            st.rerun()
        else:
            st.warning("Please ask your question about Montessori at home.")

with main_tabs[3]:  # School Support
    st.markdown("### 🏫 School & Professional Development")
    st.markdown("*Resources for schools implementing Montessori principles and teacher training*")
    
    # Professional development topics
    st.markdown("#### Professional Development Topics:")
    professional_topics = [
        "How do I introduce Montessori methods to traditional teachers?",
        "What's the research behind Montessori education?", 
        "How do I assess student progress in a Montessori environment?",
        "What are the key principles of cosmic education?",
        "How do I create a prepared environment in my classroom?",
        "What training do teachers need for Montessori implementation?"
    ]
    
    for topic in professional_topics:
        if st.button(f"📖 {topic}", key=f"prof_{topic[:20]}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": topic})
            st.rerun()
    
    # Custom professional question
    professional_question = st.text_area(
        "Ask your question about Montessori implementation or training:",
        placeholder="Example: How can we transition our traditional curriculum to include more Montessori principles?",
        height=100
    )
    
    if st.button("🎓 Get Professional Guidance", use_container_width=True):
        if professional_question:
            st.session_state.messages.append({"role": "user", "content": professional_question})
            st.rerun()
        else:
            st.warning("Please ask your professional development question.")

# Clear chat button and footer
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
        Maria - Your Montessori Companion | Powered by OpenAI GPT-4o Mini<br>
        Grounded in authentic Montessori principles and foundational texts<br>
        <em>"The child is both a hope and a promise for mankind." - Maria Montessori</em>
    </div>
    """,
    unsafe_allow_html=True
)