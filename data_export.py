"""
Data export functionality for GDPR/privacy compliance
Allows users to download all their data in structured format
"""

import io
import json
import logging
import zipfile
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class DataExporter:
    """Export user data for GDPR compliance"""
    
    def export_user_data_zip(self, db, user_id: int) -> Optional[bytes]:
        """
        Export all user data as a ZIP file
        Includes lesson plans, conversations, settings, analytics
        Returns: ZIP file bytes or None on error
        """
        try:
            from database import (
                get_db, User, LessonPlan, ChatConversation, ConversationHistory,
                PlanningNote, GreatStory, EducatorAnalytics
            )
            
            # Get user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found")
                return None
            
            # Create ZIP file in memory
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add user profile
                profile_data = {
                    'user_id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'user_type': user.user_type,
                    'created_at': user.created_at.isoformat(),
                    'subscription_status': user.subscription_status,
                    'subscription_plan': user.subscription_plan,
                    'institution_name': user.institution_name
                }
                zf.writestr('profile.json', json.dumps(profile_data, indent=2, default=str))
                
                # Add lesson plans
                lesson_plans = db.query(LessonPlan).filter(
                    LessonPlan.creator_id == user_id
                ).all()
                
                lesson_plans_data = []
                for lp in lesson_plans:
                    lesson_plans_data.append({
                        'id': lp.id,
                        'title': lp.title,
                        'description': lp.description,
                        'content': lp.content,
                        'age_group': lp.age_group,
                        'created_at': lp.created_at.isoformat(),
                        'updated_at': lp.updated_at.isoformat(),
                        'curriculum_codes': lp.australian_curriculum_codes,
                        'montessori_principles': lp.montessori_principles
                    })
                zf.writestr('lesson_plans.json', json.dumps(lesson_plans_data, indent=2, default=str))
                
                # Add planning notes
                planning_notes = db.query(PlanningNote).filter(
                    PlanningNote.educator_id == user_id
                ).all()
                
                planning_notes_data = []
                for pn in planning_notes:
                    planning_notes_data.append({
                        'id': pn.id,
                        'title': pn.title,
                        'content': pn.content,
                        'created_at': pn.created_at.isoformat(),
                        'updated_at': pn.updated_at.isoformat()
                    })
                zf.writestr('planning_notes.json', json.dumps(planning_notes_data, indent=2, default=str))
                
                # Add great stories
                great_stories = db.query(GreatStory).filter(
                    GreatStory.educator_id == user_id
                ).all()
                
                great_stories_data = []
                for gs in great_stories:
                    great_stories_data.append({
                        'id': gs.id,
                        'title': gs.title,
                        'theme': gs.theme,
                        'content': gs.content,
                        'age_group': gs.age_group,
                        'keywords': gs.keywords,
                        'created_at': gs.created_at.isoformat(),
                        'updated_at': gs.updated_at.isoformat()
                    })
                zf.writestr('great_stories.json', json.dumps(great_stories_data, indent=2, default=str))
                
                # Add conversations summary
                conversations = db.query(ChatConversation).filter(
                    ChatConversation.user_id == user_id
                ).all()
                
                conversations_data = []
                for conv in conversations:
                    # Get conversation history
                    history = db.query(ConversationHistory).filter(
                        ConversationHistory.session_id == conv.session_id
                    ).all()
                    
                    messages = []
                    for msg in history:
                        messages.append({
                            'role': msg.role,
                            'content': msg.content,
                            'created_at': msg.created_at.isoformat()
                        })
                    
                    conversations_data.append({
                        'title': conv.title,
                        'interface_type': conv.interface_type,
                        'subject_tag': conv.subject_tag,
                        'created_at': conv.created_at.isoformat(),
                        'message_count': len(messages),
                        'messages': messages
                    })
                zf.writestr('conversations.json', json.dumps(conversations_data, indent=2, default=str))
                
                # Add analytics summary
                analytics = db.query(EducatorAnalytics).filter(
                    EducatorAnalytics.user_id == user_id
                ).all()
                
                analytics_data = {
                    'total_prompts': len(analytics),
                    'total_tokens_estimated': sum(a.tokens_used or 0 for a in analytics),
                    'interfaces_used': list(set(a.interface_type for a in analytics)),
                    'first_interaction': min(a.created_at for a in analytics).isoformat() if analytics else None,
                    'last_interaction': max(a.created_at for a in analytics).isoformat() if analytics else None
                }
                zf.writestr('analytics_summary.json', json.dumps(analytics_data, indent=2, default=str))
                
                # Add export metadata
                metadata = {
                    'export_date': datetime.utcnow().isoformat(),
                    'data_format_version': '1.0',
                    'user_id': user_id,
                    'files_included': [
                        'profile.json',
                        'lesson_plans.json',
                        'planning_notes.json',
                        'great_stories.json',
                        'conversations.json',
                        'analytics_summary.json'
                    ]
                }
                zf.writestr('_metadata.json', json.dumps(metadata, indent=2, default=str))
            
            zip_buffer.seek(0)
            logger.info(f"Data export created for user {user_id}")
            return zip_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting user data: {str(e)}")
            return None


# Singleton instance
_data_exporter = None

def get_data_exporter() -> DataExporter:
    """Get or create data exporter instance"""
    global _data_exporter
    if _data_exporter is None:
        _data_exporter = DataExporter()
    return _data_exporter
