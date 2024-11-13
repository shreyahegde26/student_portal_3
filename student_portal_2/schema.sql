-- Create the database
CREATE DATABASE IF NOT EXISTS student_portal_db;
USE student_portal_db;

-- Users table
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'student', 'faculty') NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL
);

-- Students table
CREATE TABLE students (
    srn VARCHAR(50) PRIMARY KEY,
    semester INT NOT NULL,
    branch VARCHAR(50) NOT NULL,
    section VARCHAR(10) NOT NULL,
    FOREIGN KEY (srn) REFERENCES users(user_id)
);

-- Courses table
CREATE TABLE courses (
    course_id VARCHAR(20) PRIMARY KEY,
    course_name VARCHAR(100) NOT NULL,
    faculty_id VARCHAR(50) NOT NULL,
    FOREIGN KEY (faculty_id) REFERENCES users(user_id)
);

-- Student_Courses table (for enrollment)
CREATE TABLE student_courses (
    srn VARCHAR(50),
    course_id VARCHAR(20),
    PRIMARY KEY (srn, course_id),
    FOREIGN KEY (srn) REFERENCES students(srn),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

CREATE TABLE course_faculty (
    course_id VARCHAR(20),
    faculty_id VARCHAR(50),
    PRIMARY KEY (course_id, faculty_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    FOREIGN KEY (faculty_id) REFERENCES users(user_id)
);

-- Course_Materials table
CREATE TABLE course_materials (
    material_id INT AUTO_INCREMENT PRIMARY KEY,
    course_id VARCHAR(20) NOT NULL,
    title VARCHAR(100) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- Assignments table
CREATE TABLE assignments (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    course_id VARCHAR(20) NOT NULL,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    deadline DATETIME NOT NULL,
    file_path VARCHAR(255),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- Notifications table
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Chat_Messages table
CREATE TABLE chat_messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id VARCHAR(50) NOT NULL,
    receiver_id VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(user_id),
    FOREIGN KEY (receiver_id) REFERENCES users(user_id)
);

-- Add a new table for assignment submissions
CREATE TABLE assignment_submissions (
    submission_id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_id INT NOT NULL,
    student_id VARCHAR(50) NOT NULL,
    submission_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    file_path VARCHAR(255),
    grade DECIMAL(5,2),
    feedback TEXT,
    FOREIGN KEY (assignment_id) REFERENCES assignments(assignment_id),
    FOREIGN KEY (student_id) REFERENCES students(srn)
);
-- Add faculty_id column to student_courses table
ALTER TABLE student_courses ADD COLUMN faculty_id VARCHAR(50);
ALTER TABLE student_courses ADD FOREIGN KEY (faculty_id) REFERENCES users(user_id);
-- Create course_faculty table if it doesn't exist
CREATE TABLE IF NOT EXISTS course_faculty (
    course_id VARCHAR(20),
    faculty_id VARCHAR(50),
    PRIMARY KEY (course_id, faculty_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    FOREIGN KEY (faculty_id) REFERENCES users(user_id)
);

-- Add is_google_form column to assignments table if it doesn't exist
-- Add an 'is_google_form' column to the assignments table
-- ALTER TABLE assignments ADD COLUMN is_google_form BOOLEAN DEFAULT FALSE;

-- Insert initial data
INSERT INTO users (user_id, password, role, name, email)
VALUES('ADMIN001', SHA2('admin123', 256), 'admin', 'Admin', 'admin@gmail.com');

INSERT INTO users (user_id, password, role, name, email)
VALUES 
('admin1', SHA2('password123', 256), 'admin', 'John Doe', 'john.doe@example.com'),
('admin2', SHA2('securepass456', 256), 'admin', 'Jane Smith', 'jane.smith@example.com'),
('admin3', SHA2('adminpass789', 256), 'admin', 'Bob Johnson', 'bob.johnson@example.com');
-- INSERT INTO users (user_id, password, role, name, email)
-- VALUES ('FACULTY1', SHA2('faculty_password', 256), 'faculty', 'John Doe', 'john.doe@example.com');

-- -- Now insert the course into the courses table
-- INSERT INTO courses (course_id, course_name, faculty_id)
-- VALUES ('UE22CS351A', 'Database Management System', 'FACULTY1');
-- Add faculty_id column to student_courses table if it doesn't exist
ALTER TABLE student_courses ADD COLUMN faculty_id VARCHAR(50);
ALTER TABLE student_courses ADD FOREIGN KEY (faculty_id) REFERENCES users(user_id);


