import streamlit as st
import mysql.connector
from mysql.connector import Error
import hashlib
import os
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd


# Database connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="shreya@123",
            database="student_portal_db"
        )
        return connection
    except Error as e:
        st.error(f"Error connecting to MySQL database: {e}")
        return None

# Password hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# User authentication
def authenticate_user(user_id, password):
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        if user and user['password'] == hash_password(password):
            return user
        return None
    finally:
        cursor.close()
        conn.close()

# User creation
def create_user(user_id: str, password: str, role: str, name: str, email: str, 
                semester: Optional[int] = None, branch: Optional[str] = None, 
                section: Optional[str] = None, courses: Optional[List[Dict[str, str]]] = None) -> bool:
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        hashed_password = hash_password(password)

        # Insert into users table
        cursor.execute("""
            INSERT INTO users (user_id, password, role, name, email)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, hashed_password, role, name, email))

        # If the role is 'student', insert into the students table
        if role == 'student':
            cursor.execute("""
                INSERT INTO students (srn, semester, branch, section)
                VALUES (%s, %s, %s, %s)
            """, (user_id, semester, branch, section))

        # If the role is 'faculty', insert courses and link them to the faculty
        elif role == 'faculty' and courses:
            for course in courses:
                # Insert the course
                cursor.execute("""
                    INSERT INTO courses (course_id, course_name, faculty_id)
                    VALUES (%s, %s, %s)
                """, (course['course_id'], course['course_name'], user_id))
                
                # Link the course to the faculty in the course_faculty table
                cursor.execute("""
                    INSERT INTO course_faculty (course_id, faculty_id)
                    VALUES (%s, %s)
                """, (course['course_id'], user_id))

        conn.commit()
        return True
    except Error as e:
        st.error(f"Error creating user: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


# Admin Dashboard
def show_admin_dashboard():
    st.header("Admin Dashboard")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Register User", "Manage Users", "View Enrollments", "Enroll Students", "Courses and Faculty"])
    
    with tab1:
        register_user()
    
    with tab2:
        manage_users()
    
    with tab3:
        view_enrollments()
    
    with tab4:
        enroll_student()
    
    with tab5:
        show_courses_and_faculty()

# Register User
def register_user():
    st.subheader("Register New User")
    role = st.selectbox("Role", ["Student", "Faculty", "Admin"], key="register_user_role")
    name = st.text_input("Name", key="register_user_name")
    email = st.text_input("Email", key="register_user_email")
    user_id = st.text_input("User ID", key="register_user_id")
    password = st.text_input("Password", type="password", key="register_user_password")

    # If the role is 'student', ask for additional details
    semester = branch = section = None
    if role == "Student":
        semester = st.number_input("Semester", min_value=1, max_value=8, step=1, key="register_user_semester")
        branch = st.text_input("Branch", key="register_user_branch")
        section = st.text_input("Section", key="register_user_section")
    
    # If the role is 'Faculty', ask for course details
    courses: List[Dict[str, str]] = []
    if role == 'Faculty':
        st.subheader("Add Courses")
        num_courses = st.number_input("Number of courses", min_value=1, max_value=5, value=1, step=1)
        for i in range(num_courses):
            col1, col2 = st.columns(2)
            with col1:
                course_id = st.text_input(f"Course ID #{i+1}", key=f"course_id_{i}")
            with col2:
                course_name = st.text_input(f"Course Name #{i+1}", key=f"course_name_{i}")
            if course_id and course_name:
                courses.append({"course_id": course_id, "course_name": course_name})
    
    if st.button("Register User", key="register_user_button"):
        if create_user(user_id, password, role.lower(), name, email, semester, branch, section, courses):
            st.success("User registered successfully!")
        else:
            st.error("Failed to register user.")

def manage_users():
    st.subheader("Manage Users")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, role, name, email FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    st.table(users)
def view_enrollments():
    st.subheader("View Enrollments")
    conn = get_db_connection()
    if not conn:
        st.error("Failed to connect to the database.")
        return

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                s.srn, 
                u.name AS student_name, 
                c.course_id,
                c.course_name, 
                f.name AS faculty_name,
                s.semester, 
                s.branch, 
                s.section
            FROM student_courses sc
            JOIN students s ON sc.srn = s.srn
            JOIN users u ON s.srn = u.user_id
            JOIN courses c ON sc.course_id = c.course_id
            JOIN users f ON sc.faculty_id = f.user_id
            ORDER BY c.course_name, u.name
        """)
        enrollments = cursor.fetchall()

        if not enrollments:
            st.warning("No enrollments found.")
        else:
            # Group enrollments by course
            enrollments_by_course = {}
            for enrollment in enrollments:
                course_id = enrollment['course_id']
                if course_id not in enrollments_by_course:
                    enrollments_by_course[course_id] = {
                        'course_name': enrollment['course_name'],
                        'faculty_name': enrollment['faculty_name'],
                        'students': []
                    }
                enrollments_by_course[course_id]['students'].append({
                    'srn': enrollment['srn'],
                    'name': enrollment['student_name'],
                    'semester': enrollment['semester'],
                    'branch': enrollment['branch'],
                    'section': enrollment['section']
                })

            # Display enrollments
            for course_id, course_data in enrollments_by_course.items():
                with st.expander(f"{course_data['course_name']} ({course_id})"):
                    st.write(f"**Faculty:** {course_data['faculty_name']}")
                    st.write("**Enrolled Students:**")
                    student_data = [
                        {
                            "SRN": student['srn'],
                            "Name": student['name'],
                            "Semester": student['semester'],
                            "Branch": student['branch'],
                            "Section": student['section']
                        } for student in course_data['students']
                    ]
                    st.table(student_data)

    except mysql.connector.Error as e:
        st.error(f"An error occurred while fetching enrollments: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Get all students
def get_all_students():
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT srn, name FROM students JOIN users ON students.srn = users.user_id")
        students = cursor.fetchall()
        return students
    finally:
        cursor.close()
        conn.close()

# Get all courses
def get_all_courses():
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT course_id, course_name FROM courses")
        courses = cursor.fetchall()
        return courses
    finally:
        cursor.close()
        conn.close()

def get_faculty_for_course(course_id):
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.user_id, u.name 
            FROM course_faculty cf
            JOIN users u ON cf.faculty_id = u.user_id
            WHERE cf.course_id = %s
        """, (course_id,))
        faculty = cursor.fetchall()
        return faculty
    finally:
        cursor.close()
        conn.close()


def enroll_student():
    st.subheader("Enroll Student in a Course")
    
    students = get_all_students()
    courses = get_all_courses()
    
    student = st.selectbox("Select Student", options=students, format_func=lambda x: f"{x['name']} ({x['srn']})", key="enroll_student_select")
    course = st.selectbox("Select Course", options=courses, format_func=lambda x: f"{x['course_name']} ({x['course_id']})", key="enroll_course_select")
    
    if course:
        faculty_options = get_faculty_for_course(course['course_id'])
        if faculty_options:
            faculty = st.selectbox("Select Faculty", options=faculty_options, format_func=lambda x: x['name'], key="enroll_faculty_select")
        else:
            st.warning("No faculty assigned to this course.")
            faculty = None
    else:
        faculty = None
    
    if st.button("Enroll Student", key="enroll_student_button"):
        if student and course and faculty:
            if enroll_in_course(student['srn'], course['course_id'], faculty['user_id']):
                st.success(f"Student {student['name']} enrolled in course {course['course_name']} under faculty {faculty['name']}!")
            else:
                st.error("Failed to enroll student in the course.")
        else:
            st.error("Please select a student, course, and faculty.")

def enroll_in_course(student_id, course_id, faculty_id):
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if the student is already enrolled in the course
        cursor.execute("""
            SELECT * FROM student_courses 
            WHERE srn = %s AND course_id = %s
        """, (student_id, course_id))
        
        if cursor.fetchone():
            st.warning("Student is already enrolled in this course.")
            return False
        
        # Insert the student into the student_courses table
        cursor.execute("""
            INSERT INTO student_courses (srn, course_id, faculty_id)
            VALUES (%s, %s, %s)
        """, (student_id, course_id, faculty_id))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error enrolling student: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def show_courses_and_faculty():
    st.subheader("Courses and Faculty")
    
    conn = get_db_connection()
    if not conn:
        st.error("Failed to connect to the database.")
        return

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Fetch all courses with their associated faculty
        cursor.execute("""
            SELECT c.course_id, c.course_name, GROUP_CONCAT(u.name SEPARATOR ', ') as faculty_names
            FROM courses c
            LEFT JOIN course_faculty cf ON c.course_id = cf.course_id
            LEFT JOIN users u ON cf.faculty_id = u.user_id
            GROUP BY c.course_id, c.course_name
            ORDER BY c.course_name
        """)
        courses = cursor.fetchall()

        if not courses:
            st.write("No courses found.")
        else:
            # Display courses and faculty
            for course in courses:
                with st.expander(f"{course['course_name']} ({course['course_id']})"):
                    st.write(f"**Course ID:** {course['course_id']}")
                    st.write(f"**Course Name:** {course['course_name']}")
                    st.write(f"**Faculty:** {course['faculty_names'] or 'No faculty assigned'}")

        # Add new course
        st.subheader("Add New Course")
        new_course_id = st.text_input("Course ID")
        new_course_name = st.text_input("Course Name")
        if st.button("Add Course"):
            if new_course_id and new_course_name:
                cursor.execute("""
                    INSERT INTO courses (course_id, course_name)
                    VALUES (%s, %s)
                """, (new_course_id, new_course_name))
                conn.commit()
                st.success(f"Course {new_course_name} added successfully!")
            else:
                st.error("Please provide both Course ID and Course Name.")

        # Assign faculty to course
        st.subheader("Assign Faculty to Course")
        course_id = st.selectbox("Select Course", [c['course_id'] for c in courses])
        cursor.execute("SELECT user_id, name FROM users WHERE role = 'faculty'")
        faculty = cursor.fetchall()
        faculty_id = st.selectbox("Select Faculty", [f['user_id'] for f in faculty])
        if st.button("Assign Faculty"):
            try:
                cursor.execute("""
                    INSERT INTO course_faculty (faculty_id, course_id)
                    VALUES (%s, %s)
                """, (faculty_id, course_id))
                conn.commit()
                st.success(f"Faculty assigned to course successfully!")
            except mysql.connector.IntegrityError:
                st.error("This faculty is already assigned to the course.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()

# Student Dashboard
def show_student_dashboard():
    st.header("Student Dashboard")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Courses", "Timetable", "Assignments", "Course Materials", "Chat", "Notifications"])
    
    with tab1:
        show_enrolled_courses()
    
    with tab2:
        show_timetable()
    
    with tab3:
        show_assignments()
    
    with tab4:
        show_course_materials()
    
    with tab5:
        show_chat()
    with tab6:
        show_notifications()

def show_enrolled_courses():
    st.subheader("Enrolled Courses")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.course_name, u.name as faculty_name
        FROM student_courses sc
        JOIN courses c ON sc.course_id = c.course_id
        JOIN users u ON c.faculty_id = u.user_id
        WHERE sc.srn = %s
    """, (st.session_state.user['user_id'],))
    courses = cursor.fetchall()
    cursor.close()
    conn.close()

    st.table(courses)

def show_timetable():
    st.subheader("Timetable")
    st.write("Embed Google Calendar here")
    st.components.v1.iframe("https://calendar.google.com/calendar/embed?src=your_calendar_id", height=600)

    

def show_assignments():
    st.subheader("Assignments")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.assignment_id, a.title, a.description, a.deadline, c.course_name, a.file_path,
               COALESCE(s.submission_id, 0) as submitted, s.grade, s.feedback
        FROM assignments a
        JOIN courses c ON a.course_id = c.course_id
        JOIN student_courses sc ON c.course_id = sc.course_id
        LEFT JOIN assignment_submissions s ON a.assignment_id = s.assignment_id AND s.student_id = sc.srn
        WHERE sc.srn = %s
        ORDER BY a.deadline
    """, (st.session_state.user['user_id'],))
    assignments = cursor.fetchall()
    cursor.close()
    conn.close()

    for assignment in assignments:
        with st.expander(f"{assignment['title']} - {assignment['course_name']}"):
            st.write(f"**Description:** {assignment['description']}")
            st.write(f"**Deadline:** {assignment['deadline']}")
            
            # Add download button for assignment file
            if assignment['file_path']:
                file_name = os.path.basename(assignment['file_path'])
                try:
                    with open(assignment['file_path'], "rb") as file:
                        st.download_button(
                            label="Download Assignment",
                            data=file,
                            file_name=file_name,
                            mime="application/octet-stream",
                            key=f"download_assignment_{assignment['assignment_id']}"
                        )
                except FileNotFoundError:
                    st.error(f"Assignment file not found: {assignment['file_path']}")
            else:
                st.info("No file attached to this assignment.")
            
            if assignment['submitted']:
                st.write("**Status:** Submitted")
                if assignment['grade'] is not None:
                    st.write(f"**Grade:** {assignment['grade']}")
                    st.write(f"**Feedback:** {assignment['feedback']}")
                else:
                    st.write("**Status:** Grading in progress")
            else:
                st.write("**Status:** Not submitted")
                
                uploaded_file = st.file_uploader(f"Upload your assignment for {assignment['title']}", key=f"assignment_{assignment['assignment_id']}")
                if uploaded_file is not None:
                    if st.button(f"Submit {assignment['title']}", key=f"submit_{assignment['assignment_id']}"):
                        submit_assignment(assignment['assignment_id'], uploaded_file)


def submit_assignment(assignment_id, file):
    file_path = f"submissions/{st.session_state.user['user_id']}_{assignment_id}_{file.name}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(file.getbuffer())

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO assignment_submissions (assignment_id, student_id, file_path)
            VALUES (%s, %s, %s)
        """, (assignment_id, st.session_state.user['user_id'], file_path))
        conn.commit()
        st.success("Assignment submitted successfully!")
    except Error as e:
        st.error(f"Error submitting assignment: {e}")
    finally:
        cursor.close()
        conn.close()
        
def show_course_materials():
    st.subheader("Course Materials")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT cm.title, cm.file_path, c.course_name, cm.upload_date
        FROM course_materials cm
        JOIN courses c ON cm.course_id = c.course_id
        JOIN student_courses sc ON c.course_id = sc.course_id
        WHERE sc.srn = %s
    """, (st.session_state.user['user_id'],))
    materials = cursor.fetchall()
    cursor.close()
    conn.close()

    for idx, material in enumerate(materials):
        st.write(f"**{material['title']}** - {material['course_name']}")
        st.write(f"Uploaded on: {material['upload_date']}")
        st.download_button(
            label="Download",
            data=open(material['file_path'], 'rb').read(),
            file_name=material['file_path'].split('/')[-1],
            mime="application/octet-stream",
            key=f"download_material_{idx}"
        )

def show_chat():
    st.subheader("Chat Forum")
    st.write("Chat functionality to be implemented")
def view_and_grade_assignments():
    st.subheader("View and Grade Assignments")

    conn = get_db_connection()
    if not conn:
        st.error("Failed to connect to the database.")
        return

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Fetch courses taught by the faculty
        cursor.execute("""
            SELECT c.course_id, c.course_name
            FROM courses c
            JOIN course_faculty cf ON c.course_id = cf.course_id
            WHERE cf.faculty_id = %s
        """, (st.session_state.user['user_id'],))
        courses = cursor.fetchall()

        if not courses:
            st.warning("You are not assigned to any courses.")
            return

        selected_course = st.selectbox(
            "Select Course",
            options=courses,
            format_func=lambda x: x['course_name'],
            key="view_grade_assignments_course_select"
        )

        if selected_course:
            # Fetch assignments for the selected course
            cursor.execute("""
                SELECT a.assignment_id, a.title, a.deadline
                FROM assignments a
                WHERE a.course_id = %s
            """, (selected_course['course_id'],))
            assignments = cursor.fetchall()

            if not assignments:
                st.info("No assignments found for this course.")
                return

            selected_assignment = st.selectbox(
                "Select Assignment",
                options=assignments,
                format_func=lambda x: f"{x['title']} (Due: {x['deadline']})",
                key="view_grade_assignments_assignment_select"
            )

            if selected_assignment:
                # Fetch submissions for the selected assignment
                cursor.execute("""
                    SELECT ass.submission_id, ass.student_id, u.name as student_name, 
                           ass.submission_date, ass.file_path, ass.grade, ass.feedback
                    FROM assignment_submissions ass
                    JOIN users u ON ass.student_id = u.user_id
                    WHERE ass.assignment_id = %s
                    ORDER BY ass.submission_date DESC
                """, (selected_assignment['assignment_id'],))
                submissions = cursor.fetchall()

                if not submissions:
                    st.info("No submissions found for this assignment.")
                    return

                for index, submission in enumerate(submissions):
                    with st.expander(f"{submission['student_name']} - Submitted on {submission['submission_date']}"):
                        st.write(f"**Student ID:** {submission['student_id']}")
                        st.write(f"**Submission Date:** {submission['submission_date']}")
                        
                        if submission['file_path']:
                            file_name = os.path.basename(submission['file_path'])
                            try:
                                with open(submission['file_path'], "rb") as file:
                                    st.download_button(
                                        label="Download Submission",
                                        data=file,
                                        file_name=file_name,
                                        mime="application/octet-stream",
                                        key=f"download_submission_{submission['submission_id']}"
                                    )
                            except FileNotFoundError:
                                st.error(f"File not found: {submission['file_path']}")
                        else:
                            st.warning("No file submitted for this assignment.")
                        
                        grade = st.number_input(
                            "Grade",
                            min_value=0,
                            max_value=10,
                            value=int(submission['grade']) if submission['grade'] else 0,
                            key=f"grade_input_{submission['submission_id']}"
                        )
                        feedback = st.text_area(
                            "Feedback",
                            value=submission['feedback'] or "",
                            key=f"feedback_input_{submission['submission_id']}"
                        )
                        
                        if st.button(
                            "Update Grade and Feedback",
                            key=f"update_button_{submission['submission_id']}"
                        ):
                            update_grade_and_feedback(submission['submission_id'], grade, feedback)
                            st.success("Grade and feedback updated successfully!")

    except Error as e:
        st.error(f"An error occurred: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def update_grade_and_feedback(submission_id: int, grade: float, feedback: str):
    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE assignment_submissions
            SET grade = %s, feedback = %s
            WHERE submission_id = %s
        """, (grade, feedback, submission_id))
        conn.commit()
    except Error as e:
        st.error(f"Error updating grade and feedback: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def show_faculty_dashboard():
    st.header("Faculty Dashboard")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Upload Material",
        "Upload Assignment",
        "View Students",
        "Grade Assignments",
        "View All Submissions",
        "Chat"
    ])
    
    with tab1:
        upload_course_material()
    
    with tab2:
        upload_assignment()
    
    with tab3:
        view_enrolled_students()
    
    with tab4:
        view_and_grade_assignments()
    
    with tab5:
        view_all_submissions()
    
    with tab6:
        show_chat()


def view_all_submissions():
    st.subheader("View All Submissions")

    conn = get_db_connection()
    if not conn:
        st.error("Failed to connect to the database.")
        return

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Fetch courses taught by the faculty
        cursor.execute("""
            SELECT c.course_id, c.course_name
            FROM courses c
            JOIN course_faculty cf ON c.course_id = cf.course_id
            WHERE cf.faculty_id = %s
        """, (st.session_state.user['user_id'],))
        courses = cursor.fetchall()

        if not courses:
            st.warning("You are not assigned to any courses.")
            return

        selected_course = st.selectbox(
            "Select Course",
            options=courses,
            format_func=lambda x: x['course_name'],
            key="view_all_submissions_course_select"
        )

        if selected_course:
            # Fetch all assignments for the selected course
            cursor.execute("""
                SELECT a.assignment_id, a.title, a.deadline
                FROM assignments a
                WHERE a.course_id = %s
                ORDER BY a.deadline DESC
            """, (selected_course['course_id'],))
            assignments = cursor.fetchall()

            if not assignments:
                st.info("No assignments found for this course.")
                return

            # Fetch all submissions for all assignments in the course
            cursor.execute("""
                SELECT 
                    a.title AS assignment_title,
                    a.deadline,
                    u.name AS student_name,
                    ass.submission_date,
                    ass.grade,
                    ass.feedback
                FROM assignments a
                LEFT JOIN assignment_submissions ass ON a.assignment_id = ass.assignment_id
                LEFT JOIN users u ON ass.student_id = u.user_id
                WHERE a.course_id = %s
                ORDER BY a.deadline DESC, u.name ASC
            """, (selected_course['course_id'],))
            submissions = cursor.fetchall()

            if not submissions:
                st.info("No submissions found for this course.")
                return

            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(submissions)
            
            # Display summary statistics
            st.subheader("Summary Statistics")
            total_assignments = len(assignments)
            total_submissions = df['student_name'].notna().sum()
            average_grade = df['grade'].mean()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Assignments", total_assignments)
            col2.metric("Total Submissions", total_submissions)
            col3.metric("Average Grade", f"{average_grade:.2f}")

            # Display submissions in an interactive table
            st.subheader("All Submissions")
            st.dataframe(df)

            # Allow downloading the data as CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name=f"{selected_course['course_name']}_submissions.csv",
                mime="text/csv",
            )

    except Error as e:
        st.error(f"An error occurred: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def upload_course_material():
    st.subheader("Upload Course Material")
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT course_id, course_name FROM courses WHERE faculty_id = %s", (st.session_state.user['user_id'],))
    courses = cursor.fetchall()
    cursor.close()
    conn.close()

    course = st.selectbox("Select Course", options=courses, format_func=lambda x: x['course_name'], key="upload_material_course")
    title = st.text_input("Material Title", key="upload_material_title")
    file = st.file_uploader("Choose a file", type=["pdf", "docx", "pptx"], key="upload_material_file")

    if file and title and st.button("Upload", key="upload_material_button"):
        file_path = f"course_materials/{course['course_id']}_{file.name}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO course_materials (course_id, title, file_path, upload_date)
            VALUES (%s, %s, %s, %s)
        """, (course['course_id'], title, file_path, datetime.now()))
        conn.commit()

        cursor.close()
        conn.close()

        st.success("Material uploaded successfully!")

def upload_assignment():
    st.subheader("Upload Assignment")
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.course_id, c.course_name
        FROM courses c
        JOIN course_faculty cf ON c.course_id = cf.course_id
        WHERE cf.faculty_id = %s
    """, (st.session_state.user['user_id'],))
    courses = cursor.fetchall()
    cursor.close()
    conn.close()

    course = st.selectbox("Select Course", options=courses, format_func=lambda x: x['course_name'], key="upload_assignment_course")
    title = st.text_input("Assignment Title")
    description = st.text_area("Assignment Description")
    deadline = st.date_input("Deadline")
    file = st.file_uploader("Choose a file (optional)", type=["pdf", "docx"])

    if title and description and deadline and st.button("Upload", key="upload_assignment_button"):
        file_path = None
        if file:
            file_path = f"assignments/{course['course_id']}_{file.name}"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO assignments (course_id, title, description, deadline, file_path)
                VALUES (%s, %s, %s, %s, %s)
            """, (course['course_id'], title, description, deadline, file_path))
            
            # Create notifications for students
                        # Create notifications for students
            cursor.execute("""
                INSERT INTO notifications (user_id, message)
                SELECT sc.srn, %s
                FROM student_courses sc
                WHERE sc.course_id = %s
            """, (f"New assignment '{title}' has been uploaded for {course['course_name']}. Deadline: {deadline}", course['course_id']))
            
            conn.commit()
            st.success("Assignment uploaded successfully and notifications sent to students!")
        except Error as e:
            st.error(f"Error uploading assignment: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

def show_notifications():
    st.subheader("Notifications")
    
    conn = get_db_connection()
    if not conn:
        st.error("Failed to connect to the database.")
        return

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT message, created_at, is_read
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (st.session_state.user['user_id'],))
        notifications = cursor.fetchall()

        if not notifications:
            st.info("No notifications.")
        else:
            for notification in notifications:
                with st.expander(f"Notification from {notification['created_at']}"):
                    st.write(notification['message'])
                    if not notification['is_read']:
                        if st.button("Mark as Read", key=f"mark_read_{notification['created_at']}"):
                            mark_notification_as_read(notification['created_at'])
                            st.rerun()

    except Error as e:
        st.error(f"An error occurred: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def mark_notification_as_read(created_at):
    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE notifications
            SET is_read = TRUE
            WHERE user_id = %s AND created_at = %s
        """, (st.session_state.user['user_id'], created_at))
        conn.commit()
    except Error as e:
        st.error(f"Error marking notification as read: {e}")
    finally:
        cursor.close()
        conn.close()

# Update the view_enrolled_students function in the faculty dashboard
def view_enrolled_students():
    st.subheader("Enrolled Students and Assignments")
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch courses taught by the faculty
    cursor.execute("""
        SELECT course_id, course_name
        FROM courses
        WHERE faculty_id = %s
    """, (st.session_state.user['user_id'],))
    courses = cursor.fetchall()
    
    selected_course = st.selectbox("Select Course", options=courses, format_func=lambda x: x['course_name'])
    
    if selected_course:
        # Fetch students enrolled in the selected course
        cursor.execute("""
            SELECT u.name, s.srn, s.semester, s.branch, s.section
            FROM student_courses sc
            JOIN students s ON sc.srn = s.srn
            JOIN users u ON s.srn = u.user_id
            WHERE sc.course_id = %s
        """, (selected_course['course_id'],))
        students = cursor.fetchall()
        
        # Fetch assignments for the selected course
        cursor.execute("""
            SELECT assignment_id, title
            FROM assignments
            WHERE course_id = %s
        """, (selected_course['course_id'],))
        assignments = cursor.fetchall()
        
        if students:
            st.write("### Enrolled Students")
            for student in students:
                with st.expander(f"{student['name']} ({student['srn']})"):
                    st.write(f"Semester: {student['semester']}")
                    st.write(f"Branch: {student['branch']}")
                    st.write(f"Section: {student['section']}")
                    
                    if assignments:
                        st.write("### Assignments")
                        for assignment in assignments:
                            cursor.execute("""
                                SELECT submission_id, submission_date, file_path, grade, feedback
                                FROM assignment_submissions
                                WHERE assignment_id = %s AND student_id = %s
                            """, (assignment['assignment_id'], student['srn']))
                            submission = cursor.fetchone()
                            
                            st.write(f"**{assignment['title']}**")
                            if submission:
                                st.write(f"Submitted on: {submission['submission_date']}")
                                st.write(f"File: {submission['file_path']}")
                                
                                grade = st.number_input(
                                        f"Grade for {assignment['title']}",
                                        min_value=0,
                                        max_value=10,
                                        value=int(submission['grade']) if submission['grade'] else 0,  # Ensure the value is an int
                                        key=f"grade_{submission['submission_id']}"
                                    )
                                feedback = st.text_area(f"Feedback for {assignment['title']}", 
                                                        value=submission['feedback'] if submission['feedback'] else "",
                                                        key=f"feedback_{submission['submission_id']}")
                                
                                if st.button(f"Update Grade and Feedback for {assignment['title']}", 
                                             key=f"update_{submission['submission_id']}"):
                                    update_grade_and_feedback(submission['submission_id'], grade, feedback)
                            else:
                                st.write("Not submitted yet")
        else:
            st.write("No students enrolled in this course.")
    
    cursor.close()
    conn.close()

def update_grade_and_feedback(submission_id, grade, feedback):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE assignment_submissions
            SET grade = %s, feedback = %s
            WHERE submission_id = %s
        """, (grade, feedback, submission_id))
        conn.commit()
        st.success("Grade and feedback updated successfully!")
    except Error as e:
        st.error(f"Error updating grade and feedback: {e}")
    finally:
        cursor.close()
        conn.close()
# Main app
def main():
    st.set_page_config(page_title="Student Management System", layout="wide")

    if 'user' not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        show_login_page()
    else:
        show_dashboard()

def show_login_page():
    st.title("Student Management System")
    role = st.selectbox("Select your role:", ["Admin", "Student", "Faculty"])
    user_id = st.text_input("User ID")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = authenticate_user(user_id, password)
        if user and user['role'].lower() == role.lower():
            st.session_state.user = user
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid credentials or role mismatch.")

def show_dashboard():
    user = st.session_state.user
    st.title(f"Welcome, {user['name']}!")

    if user['role'] == 'admin':
        show_admin_dashboard()
    elif user['role'] == 'student':
        show_student_dashboard()
    elif user['role'] == 'faculty':
        show_faculty_dashboard()

    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()

if __name__ == "__main__":
    main()
