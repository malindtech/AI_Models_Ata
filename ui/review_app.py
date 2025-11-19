# ui/review_app.py
"""
Day 8: Human-in-the-Loop Review Interface
Streamlit app for reviewing and improving AI-generated content
"""
import os
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import streamlit as st
import httpx
from loguru import logger

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FEEDBACK_CSV = Path("data/human_feedback.csv")
TIMEOUT = 600  # 10 minutes for slow LLM models (increased for llama3:8b)

# Ensure feedback directory exists
FEEDBACK_CSV.parent.mkdir(parents=True, exist_ok=True)

# Initialize feedback CSV if it doesn't exist
if not FEEDBACK_CSV.exists():
    with open(FEEDBACK_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp', 'session_id', 'content_type', 'topic', 'tone',
            'input_prompt', 'retrieved_context', 'generated_headline', 
            'generated_body', 'decision', 'edited_headline', 'edited_body',
            'reviewer_notes', 'validation_issues', 'latency_s'
        ])

# Page config
st.set_page_config(
    page_title="AI Content Review System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .status-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .status-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
    }
    .status-error {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .context-box {
        background-color: #f8f9fa;
        color: #212529;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3498db;
        margin: 0.5rem 0;
        font-family: monospace;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    /* Chat Interface Styles */
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .chat-message {
        margin-bottom: 1rem;
        display: flex;
        align-items: flex-start;
    }
    .chat-message.user {
        justify-content: flex-end;
    }
    .chat-message.assistant {
        justify-content: flex-start;
    }
    .message-bubble {
        max-width: 70%;
        padding: 0.75rem 1rem;
        border-radius: 1rem;
        word-wrap: break-word;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .message-bubble.user {
        background-color: #007bff;
        color: white;
        border-bottom-right-radius: 0.25rem;
    }
    .message-bubble.assistant {
        background-color: #ffffff;
        color: #333;
        border-bottom-left-radius: 0.25rem;
        border-left: 3px solid #28a745;
    }
    .message-label {
        font-size: 0.75rem;
        font-weight: bold;
        margin-bottom: 0.25rem;
        opacity: 0.8;
    }
    .message-bubble.user .message-label {
        color: #e3f2fd;
    }
    .message-bubble.assistant .message-label {
        color: #666;
    }
</style>
""", unsafe_allow_html=True)


class ValidationRules:
    """Content validation rules for human review"""
    
    @staticmethod
    def check_empty(text: str) -> tuple[bool, str]:
        """Check if output is empty"""
        if not text or not text.strip():
            return False, "Content is empty"
        return True, ""
    
    @staticmethod
    def check_too_short(text: str, min_length: int = 20) -> tuple[bool, str]:
        """Check if output is too short"""
        if len(text.strip()) < min_length:
            return False, f"Content too short ({len(text)} chars, min {min_length})"
        return True, ""
    
    @staticmethod
    def check_required_fields(headline: str, body: str) -> tuple[bool, str]:
        """Check if required fields are present"""
        issues = []
        if not headline or not headline.strip():
            issues.append("Missing headline")
        if not body or not body.strip():
            issues.append("Missing body")
        
        if issues:
            return False, "; ".join(issues)
        return True, ""
    
    @staticmethod
    def check_profanity(text: str) -> tuple[bool, str]:
        """Basic profanity detection with word boundaries"""
        import re
        profanity_list = [
            'damn', 'hell', 'shit', 'fuck', 'bitch',
            'stupid', 'idiot', 'moron', 'dumb', 'crap'
        ]
        
        text_lower = text.lower()
        found = []
        for word in profanity_list:
            # Use word boundaries to avoid false positives (e.g., "ass" in "harness", "class")
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, text_lower):
                found.append(word)
        
        if found:
            return False, f"Contains inappropriate language: {', '.join(found)}"
        return True, ""
    
    @staticmethod
    def check_unsafe_content(text: str) -> tuple[bool, str]:
        """Check for potentially unsafe content patterns"""
        unsafe_patterns = [
            'click here', 'free money', 'act now', 'limited time',
            'guaranteed', '100% free', 'no obligation'
        ]
        
        text_lower = text.lower()
        found = [pattern for pattern in unsafe_patterns if pattern in text_lower]
        
        if found:
            return False, f"Contains suspicious patterns: {', '.join(found)}"
        return True, ""
    
    @classmethod
    def validate_all(cls, headline: str, body: str) -> Dict[str, any]:
        """Run all validation checks"""
        results = {
            'valid': True,
            'issues': []
        }
        
        checks = [
            cls.check_empty(headline + body),
            cls.check_too_short(body),
            cls.check_required_fields(headline, body),
            cls.check_profanity(headline + " " + body),
            cls.check_unsafe_content(headline + " " + body)
        ]
        
        for passed, message in checks:
            if not passed:
                results['valid'] = False
                results['issues'].append(message)
        
        return results


def generate_content_api(content_type: str, topic: str, tone: str) -> Optional[Dict]:
    """Call backend API to generate content"""
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(
                f"{BACKEND_URL}/v1/generate/content",
                json={
                    "content_type": content_type,
                    "topic": topic,
                    "tone": tone
                }
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        logger.error(f"Content generation failed: {e}")
        return None


def retrieve_context_api(query: str, collection: Optional[str] = None, top_k: int = 3) -> Optional[Dict]:
    """Call backend API to retrieve RAG context"""
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(
                f"{BACKEND_URL}/v1/retrieve",
                json={
                    "query": query,
                    "collection": collection,
                    "top_k": top_k
                }
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.warning(f"Context retrieval failed: {e}")
        return None


def save_feedback(data: Dict):
    """Save human feedback to CSV"""
    try:
        with open(FEEDBACK_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                data.get('timestamp'),
                data.get('session_id'),
                data.get('content_type'),
                data.get('topic'),
                data.get('tone'),
                data.get('input_prompt'),
                data.get('retrieved_context'),
                data.get('generated_headline'),
                data.get('generated_body'),
                data.get('decision'),
                data.get('edited_headline', ''),
                data.get('edited_body', ''),
                data.get('reviewer_notes', ''),
                data.get('validation_issues', ''),
                data.get('latency_s', 0.0)
            ])
        logger.info(f"Feedback saved: {data.get('decision')} for {data.get('content_type')}")
        return True
    except Exception as e:
        st.error(f"Failed to save feedback: {e}")
        logger.error(f"Feedback save failed: {e}")
        return False


def load_feedback_stats() -> Dict:
    """Load feedback statistics from CSV"""
    if not FEEDBACK_CSV.exists():
        return {'total': 0, 'approved': 0, 'rejected': 0, 'edited': 0}
    
    try:
        stats = {'total': 0, 'approved': 0, 'rejected': 0, 'edited': 0}
        with open(FEEDBACK_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['total'] += 1
                decision = row.get('decision', '').lower()
                if decision == 'approved':
                    stats['approved'] += 1
                elif decision == 'rejected':
                    stats['rejected'] += 1
                elif decision == 'edited':
                    stats['edited'] += 1
        return stats
    except Exception as e:
        logger.error(f"Failed to load stats: {e}")
        return {'total': 0, 'approved': 0, 'rejected': 0, 'edited': 0}


def display_metrics(stats: Dict):
    """Display review statistics"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Reviewed", stats['total'])
    with col2:
        st.metric("✅ Approved", stats['approved'], 
                 delta=f"{stats['approved']/stats['total']*100:.1f}%" if stats['total'] > 0 else "0%")
    with col3:
        st.metric("❌ Rejected", stats['rejected'],
                 delta=f"{stats['rejected']/stats['total']*100:.1f}%" if stats['total'] > 0 else "0%")
    with col4:
        st.metric("✏️ Edited", stats['edited'],
                 delta=f"{stats['edited']/stats['total']*100:.1f}%" if stats['total'] > 0 else "0%")


def multi_turn_chat_interface():
    """Multi-turn conversation interface for support replies"""
    st.markdown('<div class="section-header">💬 Multi-Turn Support Chat</div>', unsafe_allow_html=True)
    
    # Initialize conversation state
    if 'conversation_history' not in st.session_state:
        st.session_state['conversation_history'] = []
    if 'conversation_id' not in st.session_state:
        st.session_state['conversation_id'] = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Sidebar for conversation controls
    with st.sidebar:
        st.header("💬 Conversation Controls")
        
        # Backend health check
        try:
            with httpx.Client(timeout=5) as client:
                health = client.get(f"{BACKEND_URL}/health")
                if health.status_code == 200:
                    st.success("✅ Backend Connected")
                else:
                    st.error("❌ Backend Unavailable")
        except:
            st.error("❌ Backend Unavailable")
        
        st.divider()
        
        st.metric("Conversation Turns", len(st.session_state['conversation_history']))
        st.caption(f"ID: {st.session_state['conversation_id']}")
        
        if st.button("🔄 New Conversation", use_container_width=True):
            st.session_state['conversation_history'] = []
            st.session_state['conversation_id'] = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.rerun()
        
        st.divider()
        
        # Tone selector
        tone = st.selectbox(
            "Reply Tone",
            ["empathetic", "professional", "friendly", "formal"],
            index=0
        )
    
    # Display conversation history
    st.markdown("### 💬 Conversation")
    
    if len(st.session_state['conversation_history']) == 0:
        st.info("👋 Start a new conversation by typing a customer message below.")
    else:
        # Create a container with light background for chat
        chat_container = st.container()
        
        with chat_container:
            for i, turn in enumerate(st.session_state['conversation_history']):
                # Customer message (user) - aligned right
                with st.chat_message("user", avatar="👤"):
                    st.write(turn["user"])
                
                # Assistant message - aligned left
                with st.chat_message("assistant", avatar="🤖"):
                    st.write(turn["assistant"])
    
    # Input for new message
    st.markdown("### ✍️ New Message")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_message = st.text_area(
            "Customer Message",
            placeholder="Enter the customer's message here...",
            height=100,
            key="user_input"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        send_btn = st.button("🚀 Send", type="primary", use_container_width=True)
    
    if send_btn and user_message:
        with st.spinner("⏳ Generating reply..."):
            try:
                # Build conversation history in correct format for backend
                # Backend expects ConversationTurn objects with role='customer'|'agent' and message field
                conversation_turns = []
                for turn in st.session_state['conversation_history']:
                    conversation_turns.append({
                        "role": "customer",
                        "message": turn["user"]
                    })
                    conversation_turns.append({
                        "role": "agent",
                        "message": turn["assistant"]
                    })
                
                # Call API - backend expects async_mode as query parameter
                with httpx.Client(timeout=TIMEOUT) as client:
                    response = client.post(
                        f"{BACKEND_URL}/v1/generate/reply?async_mode=false",
                        json={
                            "message": user_message,
                            "conversation_history": conversation_turns
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                
                # Extract reply
                if isinstance(result, dict):
                    assistant_reply = result.get("reply", result.get("response", str(result)))
                else:
                    assistant_reply = str(result)
                
                # Add to conversation history
                st.session_state['conversation_history'].append({
                    "user": user_message,
                    "assistant": assistant_reply
                })
                
                st.success("✅ Reply generated!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to generate reply: {e}")
                logger.error(f"Reply generation failed: {e}")


def main():
    """Main Streamlit app"""
    
    # Header
    st.markdown('<div class="main-header">🔍 AI Content Review System</div>', unsafe_allow_html=True)
    
    # Sidebar - Configuration (moved up to determine mode visibility)
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Backend health check
        try:
            with httpx.Client(timeout=5) as client:
                health = client.get(f"{BACKEND_URL}/health")
                if health.status_code == 200:
                    st.success("✅ Backend Connected")
                else:
                    st.error("❌ Backend Unavailable")
        except:
            st.error("❌ Backend Unavailable")
        
        st.divider()
        
        # Content generation settings
        st.subheader("Content Generation")
        
        content_type = st.selectbox(
            "Content Type",
            ["blog", "product_description", "ad_copy", "email_newsletter", "social_media", "support_reply"],
            index=0
        )
    
    # Mode selector - only show multi-turn for support_reply
    if content_type == "support_reply":
        mode = st.radio(
            "Select Mode",
            ["📝 Single Generation", "💬 Multi-Turn Chat (Support)"],
            horizontal=True,
            help="Single Generation: Generate one-off content. Multi-Turn: Have a conversation for support replies."
        )
        
        if mode == "💬 Multi-Turn Chat (Support)":
            multi_turn_chat_interface()
            return
    
    # Original single-generation interface continues below...
    
    # Continue sidebar configuration
    with st.sidebar:
        
        topic = st.text_input("Topic/Subject", value="AI-powered customer service")
        
        tone = st.selectbox(
            "Tone",
            ["neutral", "empathetic", "formal", "friendly", "professional", "casual"],
            index=3
        )
        
        enable_rag = st.checkbox("Enable RAG Context", value=True)
        
        generate_btn = st.button("🚀 Generate Content", type="primary", use_container_width=True)
        
        st.divider()
        
        # Statistics
        st.subheader("📊 Review Statistics")
        stats = load_feedback_stats()
        st.metric("Total Reviewed", stats['total'])
        st.metric("Approved", stats['approved'])
        st.metric("Rejected", stats['rejected'])
        st.metric("Edited", stats['edited'])
        
        if stats['total'] > 0:
            approval_rate = stats['approved'] / stats['total'] * 100
            st.progress(approval_rate / 100)
            st.caption(f"Approval Rate: {approval_rate:.1f}%")
    
    # Main content area
    if generate_btn:
        if not topic:
            st.warning("⚠️ Please enter a topic")
            return
        
        # Show progress with estimated time
        progress_placeholder = st.empty()
        progress_placeholder.info("🔄 Generating content... This may take 1-2 minutes for large models.")
        
        start_time = datetime.utcnow()
        
        with st.spinner("⏳ Please wait... Model is processing your request"):
            # Generate content
            result = generate_content_api(content_type, topic, tone)
            
            if result:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                progress_placeholder.success(f"✅ Content generated in {elapsed:.1f}s!")
                
                # Store in session state
                st.session_state['current_task'] = {
                    'content_type': content_type,
                    'topic': topic,
                    'tone': tone,
                    'headline': result.get('headline', ''),
                    'body': result.get('body', ''),
                    'latency_s': result.get('latency_s', elapsed),
                    'timestamp': datetime.utcnow().isoformat(),
                    'session_id': st.session_state.get('session_id', datetime.now().strftime('%Y%m%d_%H%M%S')),
                    'raw_response': result  # Store full raw response for debugging
                }
                
                # Retrieve context if enabled
                if enable_rag:
                    with st.spinner("📚 Retrieving relevant context..."):
                        context_result = retrieve_context_api(topic, collection=None, top_k=3)
                        if context_result:
                            st.session_state['current_task']['retrieved_context'] = context_result
                
                st.rerun()
            else:
                progress_placeholder.error("❌ Content generation failed. Check backend logs or try again.")
    
    # Display current task for review
    if 'current_task' in st.session_state and st.session_state['current_task']:
        task = st.session_state['current_task']
        
        # Display metrics
        st.markdown('<div class="section-header">📋 Task Overview</div>', unsafe_allow_html=True)
        display_metrics(load_feedback_stats())
        
        # Input Information
        st.markdown('<div class="section-header">📥 Input Information</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"**Content Type:** {task['content_type']}")
        with col2:
            st.info(f"**Tone:** {task['tone']}")
        with col3:
            st.info(f"**Latency:** {task['latency_s']:.2f}s")
        
        st.text_area("Topic/Prompt", value=task['topic'], height=80, disabled=True)
        
        # Retrieved Context
        if 'retrieved_context' in task:
            st.markdown('<div class="section-header">🔍 Retrieved Context (RAG)</div>', unsafe_allow_html=True)
            
            context_data = task['retrieved_context']
            st.caption(f"Found {context_data.get('num_results', 0)} relevant documents ({context_data.get('latency_ms', 0):.0f}ms)")
            
            with st.expander("📚 View Retrieved Documents", expanded=False):
                for idx, doc in enumerate(context_data.get('results', [])[:3], 1):
                    st.markdown(f"**Document {idx}** (Collection: `{doc.get('collection', 'unknown')}`, Distance: {doc.get('distance', 0):.3f})")
                    st.markdown(f'<div class="context-box">{doc.get("text", "")[:300]}...</div>', unsafe_allow_html=True)
                    st.divider()
        
        # Generated Output
        st.markdown('<div class="section-header">🤖 Generated Output</div>', unsafe_allow_html=True)
        
        # Validation check
        validation = ValidationRules.validate_all(task['headline'], task['body'])
        
        if not validation['valid']:
            st.markdown('<div class="status-box status-warning">⚠️ <strong>Validation Issues Detected:</strong><br>' + 
                       '<br>'.join([f"• {issue}" for issue in validation['issues']]) + 
                       '</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-box status-success">✅ All validation checks passed</div>', 
                       unsafe_allow_html=True)
        
        # Display generated content (read-only first)
        st.text_area("Headline", value=task['headline'], height=80, disabled=True, key="display_headline")
        st.text_area("Body", value=task['body'], height=300, disabled=True, key="display_body")
        
        # Show raw response for debugging
        with st.expander("🔍 View Raw API Response", expanded=False):
            if 'raw_response' in task:
                st.json(task['raw_response'])
            else:
                st.info("Raw response not available for this task")
        
        # Review Actions
        st.markdown('<div class="section-header">✍️ Review Actions</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ Approve", type="primary", use_container_width=True):
                feedback_data = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'session_id': task['session_id'],
                    'content_type': task['content_type'],
                    'topic': task['topic'],
                    'tone': task['tone'],
                    'input_prompt': task['topic'],
                    'retrieved_context': json.dumps(task.get('retrieved_context', {})) if 'retrieved_context' in task else '',
                    'generated_headline': task['headline'],
                    'generated_body': task['body'],
                    'decision': 'approved',
                    'edited_headline': '',
                    'edited_body': '',
                    'reviewer_notes': '',
                    'validation_issues': '',
                    'latency_s': task['latency_s']
                }
                
                if save_feedback(feedback_data):
                    st.success("✅ Content approved and saved!")
                    st.session_state['current_task'] = None
                    st.rerun()
        
        with col2:
            if st.button("❌ Reject", type="secondary", use_container_width=True):
                st.session_state['show_reject_form'] = True
        
        with col3:
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state['show_edit_form'] = True
        
        # Reject form
        if st.session_state.get('show_reject_form', False):
            st.markdown("---")
            st.subheader("❌ Rejection Feedback")
            
            rejection_reason = st.text_area(
                "Why are you rejecting this content?",
                placeholder="Explain the issues with the generated content...",
                height=100
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Confirm Rejection", type="primary"):
                    feedback_data = {
                        'timestamp': datetime.utcnow().isoformat(),
                        'session_id': task['session_id'],
                        'content_type': task['content_type'],
                        'topic': task['topic'],
                        'tone': task['tone'],
                        'input_prompt': task['topic'],
                        'retrieved_context': json.dumps(task.get('retrieved_context', {})) if 'retrieved_context' in task else '',
                        'generated_headline': task['headline'],
                        'generated_body': task['body'],
                        'decision': 'rejected',
                        'edited_headline': '',
                        'edited_body': '',
                        'reviewer_notes': rejection_reason,
                        'validation_issues': '; '.join(validation['issues']),
                        'latency_s': task['latency_s']
                    }
                    
                    if save_feedback(feedback_data):
                        st.success("❌ Content rejected and feedback saved!")
                        st.session_state['current_task'] = None
                        st.session_state['show_reject_form'] = False
                        st.rerun()
            
            with col2:
                if st.button("Cancel"):
                    st.session_state['show_reject_form'] = False
                    st.rerun()
        
        # Edit form
        if st.session_state.get('show_edit_form', False):
            st.markdown("---")
            st.subheader("✏️ Edit Content")
            
            edited_headline = st.text_area(
                "Edit Headline",
                value=task['headline'],
                height=80,
                key="edit_headline"
            )
            
            edited_body = st.text_area(
                "Edit Body",
                value=task['body'],
                height=300,
                key="edit_body"
            )
            
            editor_notes = st.text_area(
                "Editor Notes (optional)",
                placeholder="Describe what you changed and why...",
                height=100
            )
            
            # Validate edited content
            edited_validation = ValidationRules.validate_all(edited_headline, edited_body)
            
            if not edited_validation['valid']:
                st.warning("⚠️ Edited content still has validation issues:\n" + 
                          '\n'.join([f"• {issue}" for issue in edited_validation['issues']]))
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Edits", type="primary", disabled=not edited_validation['valid']):
                    feedback_data = {
                        'timestamp': datetime.utcnow().isoformat(),
                        'session_id': task['session_id'],
                        'content_type': task['content_type'],
                        'topic': task['topic'],
                        'tone': task['tone'],
                        'input_prompt': task['topic'],
                        'retrieved_context': json.dumps(task.get('retrieved_context', {})) if 'retrieved_context' in task else '',
                        'generated_headline': task['headline'],
                        'generated_body': task['body'],
                        'decision': 'edited',
                        'edited_headline': edited_headline,
                        'edited_body': edited_body,
                        'reviewer_notes': editor_notes,
                        'validation_issues': '; '.join(validation['issues']),
                        'latency_s': task['latency_s']
                    }
                    
                    if save_feedback(feedback_data):
                        st.success("✏️ Edited content saved!")
                        st.session_state['current_task'] = None
                        st.session_state['show_edit_form'] = False
                        st.rerun()
            
            with col2:
                if st.button("Cancel Edit"):
                    st.session_state['show_edit_form'] = False
                    st.rerun()
    
    else:
        # No task loaded - show welcome
        st.info("👈 Configure settings in the sidebar and click 'Generate Content' to start reviewing!")
        
        # Show recent feedback
        st.markdown('<div class="section-header">📜 Recent Reviews</div>', unsafe_allow_html=True)
        
        if FEEDBACK_CSV.exists():
            try:
                import pandas as pd
                df = pd.read_csv(FEEDBACK_CSV)
                
                if len(df) > 0:
                    # Show last 10 reviews
                    recent = df.tail(10).sort_values('timestamp', ascending=False)
                    
                    st.dataframe(
                        recent[['timestamp', 'content_type', 'topic', 'decision', 'validation_issues']],
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.caption("No reviews yet. Start by generating and reviewing content!")
            except Exception as e:
                st.caption(f"Unable to load recent reviews: {e}")
        else:
            st.caption("No reviews yet. Start by generating and reviewing content!")


if __name__ == "__main__":
    # Initialize session state
    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    main()
