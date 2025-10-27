import streamlit as st
import pandas as pd
from datetime import datetime
from database import get_db, User, Student
from io import StringIO

def show_admin_dashboard():
    """Admin dashboard for viewing and exporting user data"""
    
    # Check admin access
    user_email = st.session_state.get('user_email', '')
    
    # Restrict access to admin users
    ADMIN_EMAILS = ["guideaichat@gmail.com", "ben@hmswairoa.net"]
    
    if user_email not in ADMIN_EMAILS:
        st.error("🔒 Access Denied - Admin privileges required")
        st.info("This dashboard is restricted to authorized administrators only.")
        return
    
    st.markdown("## 🔧 Admin Dashboard")
    st.markdown("---")
    
    db = get_db()
    if not db:
        st.error("Database connection unavailable")
        return
    
    try:
        # Fetch all educators
        educators = db.query(User).order_by(User.created_at.desc()).all()
        
        # Fetch all students
        students = db.query(Student).order_by(Student.created_at.desc()).all()
        
        # Display statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Educators", len(educators))
        
        with col2:
            st.metric("Total Students", len(students))
        
        with col3:
            total_users = len(educators) + len(students)
            st.metric("Total Users", total_users)
        
        st.markdown("---")
        
        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["📧 Educators", "👨‍🎓 Students", "📊 Export Data"])
        
        with tab1:
            st.subheader("Registered Educators")
            
            if educators:
                # Create DataFrame for display
                educator_data = []
                for edu in educators:
                    educator_data.append({
                        "ID": edu.id,
                        "Email": edu.email,
                        "Full Name": edu.full_name,
                        "Institution": edu.institution_name or "Not Set",
                        "Created At": edu.created_at.strftime("%Y-%m-%d %H:%M") if edu.created_at else "N/A",
                        "Active": "✅" if edu.is_active else "❌"
                    })
                
                df_educators = pd.DataFrame(educator_data)
                st.dataframe(df_educators, use_container_width=True, hide_index=True)
                
                # Email list for easy copying
                st.markdown("### 📋 Email List (Copy-Friendly)")
                email_list = "\n".join([edu.email for edu in educators if edu.email])
                st.code(email_list, language=None)
                
                # Download button for educator emails
                st.download_button(
                    label="📥 Download Educator Emails (TXT)",
                    data=email_list,
                    file_name=f"educator_emails_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )
            else:
                st.info("No educators registered yet")
        
        with tab2:
            st.subheader("Registered Students")
            
            if students:
                # Create DataFrame for display
                student_data = []
                for stu in students:
                    # Get educator email
                    educator = db.query(User).filter(User.id == stu.educator_id).first()
                    educator_email = educator.email if educator else "Unknown"
                    
                    student_data.append({
                        "ID": stu.id,
                        "Username": stu.username,
                        "Full Name": stu.full_name,
                        "Age Group": stu.age_group or "Not Set",
                        "Educator": educator_email,
                        "Created At": stu.created_at.strftime("%Y-%m-%d %H:%M") if stu.created_at else "N/A",
                        "Active": "✅" if stu.is_active else "❌"
                    })
                
                df_students = pd.DataFrame(student_data)
                st.dataframe(df_students, use_container_width=True, hide_index=True)
            else:
                st.info("No students registered yet")
        
        with tab3:
            st.subheader("Export All User Data")
            
            # Export educators to CSV
            if educators:
                st.markdown("#### 📧 Educator Data Export")
                
                educator_export = []
                for edu in educators:
                    educator_export.append({
                        "Email": edu.email,
                        "Full Name": edu.full_name,
                        "Institution": edu.institution_name or "",
                        "User Type": edu.user_type,
                        "Active": edu.is_active,
                        "Created Date": edu.created_at.strftime("%Y-%m-%d") if edu.created_at else "",
                        "Created Time": edu.created_at.strftime("%H:%M:%S") if edu.created_at else ""
                    })
                
                df_export = pd.DataFrame(educator_export)
                csv_educators = df_export.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download All Educators (CSV)",
                    data=csv_educators,
                    file_name=f"all_educators_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                st.dataframe(df_export, use_container_width=True, hide_index=True)
            
            # Export students to CSV
            if students:
                st.markdown("#### 👨‍🎓 Student Data Export")
                
                student_export = []
                for stu in students:
                    educator = db.query(User).filter(User.id == stu.educator_id).first()
                    
                    student_export.append({
                        "Username": stu.username,
                        "Full Name": stu.full_name,
                        "Age Group": stu.age_group or "",
                        "Educator Email": educator.email if educator else "",
                        "Educator Name": educator.full_name if educator else "",
                        "Active": stu.is_active,
                        "Created Date": stu.created_at.strftime("%Y-%m-%d") if stu.created_at else "",
                        "Created Time": stu.created_at.strftime("%H:%M:%S") if stu.created_at else ""
                    })
                
                df_student_export = pd.DataFrame(student_export)
                csv_students = df_student_export.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download All Students (CSV)",
                    data=csv_students,
                    file_name=f"all_students_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                st.dataframe(df_student_export, use_container_width=True, hide_index=True)
            
            # Combined export
            if educators or students:
                st.markdown("#### 📊 Combined Summary Export")
                
                summary_data = {
                    "Total Educators": [len(educators)],
                    "Total Students": [len(students)],
                    "Total Users": [len(educators) + len(students)],
                    "Active Educators": [sum(1 for e in educators if e.is_active)],
                    "Active Students": [sum(1 for s in students if s.is_active)],
                    "Export Date": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                }
                
                df_summary = pd.DataFrame(summary_data)
                csv_summary = df_summary.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download Summary Report (CSV)",
                    data=csv_summary,
                    file_name=f"user_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        st.markdown("---")
        st.info("💡 **Tip:** Use the Export Data tab to download complete user lists in CSV format for your records.")
        
    except Exception as e:
        st.error(f"Error loading admin dashboard: {str(e)}")
    finally:
        db.close()
