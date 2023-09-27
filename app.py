import flask
from flask import Flask, redirect, url_for, jsonify
from flask import request, flash
from flask import abort, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from functools import wraps
from sqlalchemy import text
import json

app = Flask(__name__)
app.secret_key = 'shhh'

with app.app_context():
    # Setup
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite3"
    db = SQLAlchemy(app)
    #Sets up admin page
    admin = Admin(app)
    #Sets up login manager
    login_manager = LoginManager()
    login_manager.login_view = 'logIn'
    login_manager.init_app(app)
    
    # Database
    student_classes = db.Table('student_classes',
        db.Column('student_id', db.Integer, db.ForeignKey('student.id'), primary_key = True),
        db.Column('classes_id', db.Integer, db.ForeignKey('classes.id'), primary_key = True)
    )

    roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
    )

    class Enrollment(db.Model):
        __tablename__ = "enrollment"
        id = db.Column(db.Integer, primary_key=True)
        grade = db.Column(db.Integer, unique = False, nullable = False)
        # Foreign Key From student.id
        classes_id = db.Column(db.Integer, db.ForeignKey('classes.id'), unique = False)
        # Relationship enrollment-class
        classes = db.relationship('Classes', back_populates='enrollment')
        # Foreign Key From class.id
        student_id = db.Column(db.Integer, db.ForeignKey('student.id'), unique = False)
        # Relationship enrollment-student
        student = db.relationship('Student', back_populates='enrollment')
   
    class Role(db.Model):
        __tablename__ = "role"
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(80), unique=True)

        def __repr__(self):
            return self.name

    class User(UserMixin, db.Model):
        __tablename__ = "user"
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String, unique = True, nullable=False)
        password = db.Column(db.String, unique = False, nullable = False)
        # Relationship User-Role
        roles = db.relationship('Role', secondary=roles_users,backref=db.backref('users', lazy='dynamic'))
        # Relationship User-Student
        student = db.relationship('Student', back_populates='user', uselist=False)
        # Relationship User-Teacher
        teacher = db.relationship('Teacher', back_populates='user', uselist=False)
        
        def has_role(self, role_name):
            #Does the user have this permission?
            my_role = Role.query.filter_by(name=role_name).first()
            if my_role in self.roles:
                return True
            else:
                return False
        def __repr__(self):
            return self.username
    def require_role(role):
        #make sure user has this role
        def decorator(func):
            @wraps(func)
            def wrapped_function(*args, **kwargs):
                if not current_user.has_role(role):
                    return redirect("/")
                else:
                    return func(*args, **kwargs)
            return wrapped_function
        return decorator
    #A user loader tells Flask-Login how to find a specific user from the ID that is stored in their session cookie
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    class Student(db.Model):
        __tablename__ = "student"
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String, unique=False, nullable=False)
        # Foreign Key From user.id
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique = True, nullable = False)
        # Relationship User-Student
        user = db.relationship('User', back_populates='student', uselist=False)
        # Relationship Enrollment-Student
        enrollment = db.relationship('Enrollment', back_populates='student')
        # Relationship Classes-Student
        classes = db.relationship('Classes',secondary='student_classes', back_populates='student')
        
        def __repr__(self):
            return self.name

    class Teacher(db.Model):
        __tablename__ = "teacher"
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String, unique=False, nullable=False)
        # Foreign Key From user.id
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique = True, nullable = False)
        # Relationship User-Teacher
        user = db.relationship('User', back_populates='teacher', uselist=False)
        # Relationship Classes-Teacher
        classes = db.relationship('Classes', back_populates='teacher')

        def __repr__(self):
            return self.name

    class Classes(db.Model):
        __tablename__ = "classes"
        id = db.Column(db.Integer, primary_key=True)
        course_name = db.Column(db.String, unique = True, nullable=False)
        number_enrolled = db.Column(db.Integer, unique = False, nullable=False)
        capacity = db.Column(db.String, unique = False, nullable=False)
        time = db.Column(db.String, unique = False, nullable=False)
        # Foreign Key From teacher.id
        teacher_ID = db.Column(db.String, db.ForeignKey('teacher.id'), unique = False, nullable=False)
        # Relationship Classes-Teacher
        teacher = db.relationship('Teacher', back_populates='classes')
        # Relationship Enrollment-Student
        enrollment = db.relationship('Enrollment', back_populates='classes')
        # Relationship Class-Student
        student = db.relationship('Student', secondary='student_classes', back_populates='classes')
        def __repr__(self):
            return self.course_name
    db.create_all()

    # Admin
    class UserView(ModelView):
        form_excluded_columns = ['student', 'teacher']
        form_choices = {
            'teachORstudent': [
                     ('Student', 'Student'),
                     ('Teacher', 'Teacher')
                    
                ]
           }
    class StudentView(ModelView):
        form_excluded_columns = []
        
    class TeacherView(ModelView):
        form_excluded_columns = ['classes']
        
    class ClassView(ModelView):
        form_excluded_columns = ['student']
        
    admin.add_view(UserView(User, db.session))
    admin.add_view(ModelView(Role, db.session))
    admin.add_view(StudentView(Student, db.session))
    admin.add_view(TeacherView(Teacher, db.session))
    admin.add_view(ClassView(Classes, db.session))
    admin.add_view(ModelView(Enrollment, db.session))

    def __init__(self):
            super(UserView, self).__init__(User, db.session)


@app.route('/')
def index():
    return redirect(url_for('logIn'))

# Log In Method
@app.route('/login')
def logIn():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    #Get login information from the form
    username = request.form.get('uname')
    password = request.form.get('password')
    #get user information
    user = User.query.filter_by(username=username).first()
    #check if user exists
    if not user or not user.password == password:
        flash('Please check your login details and try again.')
        return redirect(url_for('logIn'))

    #if user role is teacher then login as teacher
    if user.has_role('Teacher'):
        login_user(user)
        return redirect(url_for('teacher_home'))
    #if user role is student then login as student
    elif user.has_role('Student'):
        login_user(user)
        return redirect(url_for('student_your_courses'))
    return "Can not log in: Do not know type of Role"

@app.route('/logout')
@login_required
def logOut():
    logout_user()
    return redirect(url_for('logIn'))

@app.route('/student/yourCourses')
@login_required
@require_role(role='Student')
def student_your_courses():
    student = Student.query.filter_by(user_id=current_user.id).first()
    name = Student.query.filter_by(user_id=current_user.id).first()
    sql = text(''' 
    SELECT course_name, teacher.name AS teacher_name, classes.time, classes.number_enrolled, classes.capacity, enrollment.grade
    FROM enrollment, classes, student, teacher
    WHERE enrollment.classes_id = classes.id
    AND student.id = enrollment.student_id
    AND teacher.id = classes.teacher_ID
    AND student.name = :x
    ''')
    name = {'x': student.name}
    result = db.session.execute(sql, name)

    results = result.mappings().all()
    
    # course = row.course_name, teacher = row.teacher_name, time = row.time, num_enrolled = row.number_enrolled,
    return render_template('your_student.html', prefix=' ', person=student, classes = results)





@app.route('/student/addCourses')
@login_required
@require_role(role='Student')
def student_add_courses():
    if request.method == "POST":
        course = request.form["course"]
        print(course)
        #new_enrollment = Enrollment(classes_id = )
    student = Student.query.filter_by(user_id=current_user.id).first()
    enrolled = Enrollment.query.filter_by(student_id=student.id).all()
    sql = text('''
    SELECT course_name, teacher.name, classes.time, classes.number_enrolled, classes.capacity, classes.id
    FROM  classes, teacher
    WHERE teacher.id = classes.teacher_ID
    ''')
    result =  db.session.execute(sql)
    results = result.mappings().all()
    return render_template('add_student.html', prefix=' ', person=student, classes=results, enrolled=enrolled)


@app.route('/student/addCourses/<class_id>/remove')
@login_required
@require_role(role='Student')
def remove(class_id):
    student = Student.query.filter_by(user_id=current_user.id).first()
    remove_enrolled = Enrollment.query.filter_by(classes_id=class_id, student_id=student.id).first()
    db.session.delete(remove_enrolled)
    decrement = Classes.query.filter_by(id=class_id).first()
    if decrement.number_enrolled > 0:
        decrement.number_enrolled -= 1
    db.session.commit()
    return redirect(url_for('student_add_courses'))

@app.route('/student/addCourses/<class_id>/add')
@login_required
@require_role(role='Student')
def add(class_id):
    student = Student.query.filter_by(user_id=current_user.id).first()
    add_enrolled = Enrollment(grade=0,classes_id=class_id, student_id=student.id)
    increment = Classes.query.filter_by(id=class_id).first()
    increment.number_enrolled += 1
    db.session.add(add_enrolled)
    db.session.commit()
    return redirect(url_for('student_add_courses'))


@app.route('/teacher')
@login_required
@require_role(role='Teacher')
def teacher_home():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    name = Teacher.query.filter_by(user_id=current_user.id).first()
    sql = text(''' 
    SELECT course_name, teacher.name, classes.time, classes.number_enrolled, classes.capacity, classes.id
    FROM  classes, teacher
    WHERE teacher.id = classes.teacher_ID
    AND teacher_ID = :x
    ''')
    name = {'x': teacher.id}
    result = db.session.execute(sql, name)

    results = result.mappings().all()
    

    return render_template('teacher.html', prefix=' Dr. ', person=teacher, rows = results)
@app.route('/teacher/<course_id>')
@login_required
@require_role(role='Teacher')
def teacher_course(course_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    classes = Classes.query.filter_by(id=course_id).first()
    sql = text(''' 
    SELECT student.name, enrollment.grade, course_name, enrollment.id AS enrollment_id
    FROM student, enrollment, classes
    WHERE student.id = enrollment.student_id
    AND classes.id = enrollment.classes_id
    AND classes.id = :x
    ''')
    name = {'x': classes.id}
    result = db.session.execute(sql, name)
    results = result.mappings().all()
    print(results)
    return render_template('teacher_course.html', prefix=' Dr. ', person=teacher, rows = results, course=course_id)

@app.route('/teacher/<enroll_id>', methods=['POST'])
@login_required
@require_role(role='Teacher')
def edit_grade(enroll_id):
    enrollment = Enrollment.query.filter_by(id=enroll_id).first()
    print(enrollment.grade)
    grade = request.form.get('grade')
    print(grade)
    enrollment.grade = grade
    print(enrollment.grade)
    db.session.commit()
    return redirect(url_for('teacher_course', course_id=enrollment.classes_id))






if __name__ == '__main__':
    app.run()