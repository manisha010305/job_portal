from flask import Flask, request, redirect, session, render_template, flash
import sqlite3
import PyPDF2
import pdfplumber
import os

app = Flask(__name__)
app.secret_key = 'secret123'  # Session ke liye zaroori hai

# Uploads folder bana de agar nahi hai to
if not os.path.exists('uploads'):
    os.makedirs('uploads')

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('index.html')  

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('database.db')
        try:
            conn.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', 
                        (name, email, password))
            conn.commit()
            conn.close()
            return redirect('/login')
        except:
            conn.close()
            return "Email already exists! <a href='/signup'>Try again</a>"
    
    return render_template('signup.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', 
                           (email, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['name'] = user['name']
            flash('login successfull welcome','success')
            return redirect('/dashboard')
        else:
            flash('wrong email or password','error')
            return "Invalid email or password! <a href='/login'>Try again</a>"
    
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
    if user['skills']:
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
            # Tera resume extraction wala code yahan rahega
            text = ""
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()

            # Skills extract karo
            found_skills = []
            skill_keywords = ['python', 'java', 'html', 'css', 'javascript', 'sql', 'excel', 'ms excel', 'ms word', 'c programming', 'problem solving']
            
            text_lower = text.lower()
            for skill in skill_keywords:
                if skill in text_lower:
                    found_skills.append(skill.title())

            # Duplicate hatao
            skills_str = ', '.join(list(dict.fromkeys(found_skills)))

            # Database mein update karo
            conn = sqlite3.connect('database.db')
            conn.execute('UPDATE users SET skills = ? WHERE id = ?', 
                        (skills_str, session['user_id']))
            conn.commit()
            conn.close()

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
    query = request.args.get('q')
    if not query:
        return redirect('/')
    
    # Database connection yahan banega
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Isse dict jaisa data milega
    cursor = conn.cursor()  # <-- Ye line missing thi
    
    jobs = cursor.execute("SELECT * FROM jobs WHERE title LIKE ?", ('%'+query+'%',)).fetchall()
    
    conn.close()  
    return render_template('dashboard.html', jobs=jobs, name="Guest", skills="") 

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)

