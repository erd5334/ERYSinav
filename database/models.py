"""
Veritabanı modelleri
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, Float, DateTime
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Course(Base):
    __tablename__ = 'courses'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    department = Column(String(200), nullable=True)
    instructor = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)
    
    questions = relationship('Question', back_populates='course', cascade='all, delete-orphan')
    exams = relationship('Exam', back_populates='course', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Course(code='{self.code}', name='{self.name}')>"

class Question(Base):
    __tablename__ = 'questions'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    question_number = Column(String(50), nullable=True)
    question_text = Column(Text, nullable=False)
    question_image_path = Column(String(500), nullable=True)
    option_a = Column(Text, nullable=True)
    option_a_image_path = Column(String(500), nullable=True)
    option_b = Column(Text, nullable=True)
    option_b_image_path = Column(String(500), nullable=True)
    option_c = Column(Text, nullable=True)
    option_c_image_path = Column(String(500), nullable=True)
    option_d = Column(Text, nullable=True)
    option_d_image_path = Column(String(500), nullable=True)
    option_e = Column(Text, nullable=True)
    option_e_image_path = Column(String(500), nullable=True)
    correct_answer = Column(String(10), nullable=True)
    difficulty = Column(String(50), nullable=True)
    topic = Column(String(200), nullable=True)
    tags = Column(String(200), nullable=True)
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    
    course = relationship('Course', back_populates='questions')
    exam_questions = relationship('ExamQuestion', back_populates='question', cascade='all, delete-orphan')

    def increment_usage(self):
        self.usage_count += 1
        self.last_used = datetime.now()

    def __repr__(self):
        return f"<Question(id={self.id}, course_id={self.course_id})>"

class Exam(Base):
    __tablename__ = 'exams'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    exam_type = Column(String(50), nullable=False)
    exam_group = Column(String(50), nullable=True)
    exam_date = Column(DateTime, nullable=True)
    academic_year = Column(String(50), nullable=True)
    semester = Column(String(50), nullable=True)
    word_file_path = Column(String(500), nullable=True)
    pdf_file_path = Column(String(500), nullable=True)
    answer_key_path = Column(String(500), nullable=True)
    total_questions = Column(Integer, default=0)
    duration_minutes = Column(Integer, default=0)
    shuffle_questions = Column(Boolean, default=True)
    shuffle_answers = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    
    course = relationship('Course', back_populates='exams')
    exam_questions = relationship('ExamQuestion', back_populates='exam', cascade='all, delete-orphan')
    student_results = relationship('StudentResult', back_populates='exam', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Exam(id={self.id}, type='{self.exam_type}', group='{self.exam_group}')>"

class ExamQuestion(Base):
    __tablename__ = 'exam_questions'
    
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exams.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('questions.id'), nullable=False)
    question_order = Column(Integer, nullable=False)
    points = Column(Float, default=0.0)
    
    exam = relationship('Exam', back_populates='exam_questions')
    question = relationship('Question', back_populates='exam_questions')

    def __repr__(self):
        return f"<ExamQuestion(exam_id={self.exam_id}, question_id={self.question_id}, order={self.question_order})>"

class Student(Base):
    __tablename__ = 'students'
    
    id = Column(Integer, primary_key=True)
    student_no = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    department = Column(String(200), nullable=True)
    program = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    
    results = relationship('StudentResult', back_populates='student', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Student(no='{self.student_no}', name='{self.name}')>"

class StudentResult(Base):
    __tablename__ = 'student_results'
    
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exams.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False)
    score = Column(Float, default=0.0)
    correct_count = Column(Integer, default=0)
    wrong_count = Column(Integer, default=0)
    empty_count = Column(Integer, default=0)
    answers = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    exam = relationship('Exam', back_populates='student_results')
    student = relationship('Student', back_populates='results')

    def __repr__(self):
        return f"<StudentResult(exam_id={self.exam_id}, student_id={self.student_id}, score={self.score})>"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), nullable=True)
    full_name = Column(String(200), nullable=True)
    role = Column(String(50), default='user')
    password_hash = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"

class Settings(Base):
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Settings(key='{self.key}', value='{self.value}')>"
