import re
from flask import Flask, request, redirect, session, render_template, flash
import sqlite3
import PyPDF2
import pdfplumber
import os
import random

def extract_skills_from_pdf(text):
    # Common skills ki list
    skill_keywords = [
        'python', 'java', 'javascript', 'react', 'node', 'sql', 'html', 'css',
        'flask', 'django', 'git', 'aws', 'docker', 'excel', 'powerpoint',
        'communication', 'leadership', 'management', 'marketing', 'sales'
    ]
    
    found_skills = []
    text_lower = text.lower()
    
    for skill in skill_keywords:
        if skill in text_lower:
            found_skills.append(skill)
    
    return found_skills

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            skills TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    conn.close()

init_db()

app = Flask(__name__)  
app.secret_key = 'hirehub_secret_key_123' 
if not os.path.exists('uploads'):
    os.makedirs('uploads')

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('index.html')  

def validate_password(password):
    if len(password) < 8:
        return "Password 8 character ka hona chahiye"
    if not re.search("[a-z]", password):
        return "Ek chhota letter daal"
    if not re.search("[A-Z]", password):
        return "Ek bada letter daal"
    if not re.search("[0-9]", password):
        return "Ek number daal"
    if not re.search("[!@#$%^&*]", password):
        return "Ek special character daal:!@#$%^&*"
    return None

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role')  
        
        # Strong password check
        error = validate_password(password)
        if error:
            return render_template('signup.html', error=error)  
        
        if not role:  # <-- ROLE CHECK ADD KIYA
            return render_template('signup.html', error="Role select karo")
        
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                      (name, email, password, role))
        conn.commit()
        conn.close()
        flash('Signup success! Ab login karo.')
        return redirect('/login')
    
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            # Session mein data daal de - YE ZARURI HAI
            session['user_id'] = user[0] # id
            session['name'] = user[1] # name
            session['email'] = user[2] # email
            session['role'] = user[4] # role - ye 4th index pe hai
            return redirect('/dashboard')
        else:
            return render_template('login.html', error="Galat email ya password")

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row

    user = conn.execute('SELECT * FROM users WHERE id =?',
                       (session['user_id'],)).fetchone()

    user_skills = []
    if user['skills']and user['skills'].strip():
        user_skills = [s.strip().lower() for s in user['skills'].split(',')]

    # Ye 3 line important hain - check kar ye hain ya nahi
    applied_jobs = conn.execute('SELECT job_id FROM applications WHERE user_id =?',
                               (session['user_id'],)).fetchall()
    applied_job_ids = [row[0] for row in applied_jobs]

    jobs_data = conn.execute('SELECT * FROM jobs').fetchall() # Ye line miss thi

    conn.close()

    jobs_with_match = []
    for job in jobs_data:
        job_skills = [s.strip().lower() for s in job['skills'].split(',')]
        matched = set(user_skills) & set(job_skills)
        if len(job_skills) > 0:
            match_percent = int((len(matched) / len(job_skills)) * 100)
        else:
            match_percent = 0

        is_applied = job['id'] in applied_job_ids

        jobs_with_match.append({
            'id': job['id'],
            'title': job['title'],
            'company': job['company'],
            'skills': job['skills'],
            'description': job['description'],
            'match': match_percent,
            'applied': is_applied
        })

    jobs_with_match.sort(key=lambda x: x['match'], reverse=True)

    return render_template('dashboard.html', user=user, jobs=jobs_with_match)
    

@app.route('/add_job', methods=['GET', 'POST'])
def add_job():
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        title = request.form['title']
        company = request.form['company']
        location = request.form.get('location', 'Remote')
        salary = request.form.get('salary', 'Not disclosed')
        skills = request.form.get('skills', '')
        description = request.form.get('description', '')
        
        conn = sqlite3.connect('database.db')
        conn.execute('INSERT INTO jobs (title, company, location, salary, skills, description, posted_by) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (title, company, location, salary, skills, description, session['user_id']))
        conn.commit()
        conn.close()
        flash('Job posted successfully!', 'success')
        return redirect('/dashboard')
    
    return render_template('add_job.html')
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        if 'resume' not in request.files:
            return "No file uploaded! <a href='/upload'>Try again</a>"
            
        file = request.files['resume']
        if file.filename == '':
            return "No file selected! <a href='/upload'>Try again</a>"

        if file and file.filename.endswith('.pdf'):
            text = ""
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()

                 # Skills extract karo
        found_skills = extract_skills_from_pdf(text)  # text variable use kar, resume_text nahi
        skills_string = ','.join(found_skills)
        
        # Database mein update karo
        conn = sqlite3.connect('database.db')
        conn.execute('UPDATE users SET skills = ? WHERE id = ?', 
                    (skills_string, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Resume uploaded! Skills found: ' + skills_string)
        return redirect('/dashboard') 

    return render_template('upload.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
@app.route('/apply/<int:job_id>')
def apply(job_id):
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect('/login')
    
    user_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    
    # Check kar ki pehle se apply toh nahi kiya
    already_applied = conn.execute('SELECT * FROM applications WHERE user_id=? AND job_id=?', 
                                  (user_id, job_id)).fetchone()
    
    if already_applied:
        flash('You have already applied to this job!', 'error')
    else:
        # Apply kar de
        conn.execute('INSERT INTO applications (user_id, job_id) VALUES (?,?)', 
                    (user_id, job_id))
        conn.commit()
        flash('Applied successfully! ✅', 'success')
    
    conn.close()
    return redirect('/dashboard')

@app.route('/my_applications')
def my_applications():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    # Ye query un saari jobs ko layegi jinke liye user ne apply kiya hai
    applied_jobs = conn.execute('''
        SELECT j.* FROM jobs j
        JOIN applications a ON j.id = a.job_id
        WHERE a.user_id = ?
    ''', (user_id,)).fetchall()
    conn.close()
    
    return render_template('my_applications.html', jobs=applied_jobs, name=session['name'])

@app.route('/search')
def search():
    print("search route hit hua")
    query = request.args.get('q')
    print("query mili:",query)
    if not query:
        return redirect('/')
    
    # Database connection yahan banega
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Isse dict jaisa data milega
    cursor = conn.cursor()  # <-- Ye line missing thi
    
    jobs = cursor.execute("""
    SELECT * FROM jobs 
    WHERE title LIKE ? OR description LIKE ? OR company LIKE ?
""", ('%'+query+'%', '%'+query+'%', '%'+query+'%')).fetchall()
    
    conn.close()  
    return render_template('search_results.html', jobs=jobs, search_query=query)

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)

