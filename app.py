from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
import mysql.connector

app = Flask(__name__)

# Secret key for session security
app.secret_key = 'axislink_super_secret_key'

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'axislink_admin', # Update this if needed
    'password': 'axislink_password', # Update this if needed
    'database': 'axislink_db'
}

# --- ROUTE 1: PUBLIC FRONT PAGE ---
@app.route('/')
def home():
    # Public display page only; no database logic needed here
    return render_template('index.html')

# --- ROUTE 2: AUTHENTICATION (LOGIN) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    
    if request.method == 'POST':
        form_email = request.form['email']
        form_password = request.form['password']
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # Step 1: Query the central user account table first
        sql_account = "SELECT * FROM tbl_user_account WHERE email_address = %s"
        cursor.execute(sql_account, (form_email,))
        account = cursor.fetchone()
        
        # Step 2: Verify account existence and password hash
        if account and check_password_hash(account['password_hash'], form_password):
            role = account['role_type']
            session['role'] = role
            
            # Step 3: Route dynamically based on user role
            if role == 'Employer':
                sql_employer = "SELECT employer_id, company_name FROM tbl_employer WHERE account_id = %s"
                cursor.execute(sql_employer, (account['account_id'],))
                emp_data = cursor.fetchone()
                
                if emp_data:
                    # Save specific employer details to session
                    session['employer_id'] = emp_data['employer_id']
                    session['user_id'] = emp_data['company_name']
                    cursor.close()
                    connection.close()
                    return redirect(url_for('employer_dashboard'))
                    
            elif role == 'Learner':
                sql_learner = "SELECT learner_id, first_name, last_name FROM tbl_learner WHERE account_id = %s"
                cursor.execute(sql_learner, (account['account_id'],))
                learner_data = cursor.fetchone()
                
                if learner_data:
                    # Save specific learner details to session
                    session['learner_id'] = learner_data['learner_id']
                    session['user_id'] = f"{learner_data['first_name']} {learner_data['last_name']}"
                    cursor.close()
                    connection.close()
                    # Redirect to home for now until learner_dashboard is built
                    return redirect(url_for('home'))
        else:
            # Handle failed login attempt
            error_message = "Invalid email or password. Please try again."
            
        cursor.close()
        connection.close()
            
    return render_template('login.html', error=error_message)

# --- ROUTE 3: REGISTRATION ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        form_email = request.form['email']
        form_password = request.form['password']
        form_role = request.form['role'] 
        
        # Hash the password before database insertion
        hashed_password = generate_password_hash(form_password)
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        try:
            # Insert into central user account table
            sql_account = """
                INSERT INTO tbl_user_account (email_address, password_hash, role_type, account_status) 
                VALUES (%s, %s, %s, 'Active')
            """
            cursor.execute(sql_account, (form_email, hashed_password, form_role))
            
            # Retrieve the newly generated account_id
            new_account_id = cursor.lastrowid
            
            # Segregate and insert based on role type
            if form_role == 'Learner':
                form_fname = request.form.get('first_name')
                form_lname = request.form.get('last_name')
                
                # Insert learner with required placeholders to prevent Not Null errors
                sql_learner = """
                    INSERT INTO tbl_learner 
                    (account_id, first_name, last_name, middle_name, suffix, date_of_birth, gender, nationality, highest_educational_attainment, home_address, contact_number) 
                    VALUES (%s, %s, %s, 'N/A', 'N/A', '2000-01-01', 'N/A', 'N/A', 'N/A', 'To be updated', 'To be updated')
                """
                cursor.execute(sql_learner, (new_account_id, form_fname, form_lname))
                
            elif form_role == 'Employer':
                form_company = request.form.get('company_name')
                
                # Insert employer with required placeholders to prevent Not Null errors
                sql_employer = """
                    INSERT INTO tbl_employer 
                    (account_id, company_name, industry_sector, company_address, contact_person, contact_number) 
                    VALUES (%s, %s, 'To be updated', 'To be updated', 'To be updated', 'To be updated')
                """
                cursor.execute(sql_employer, (new_account_id, form_company))
                
            # Commit transaction if all queries succeed
            connection.commit()
            
        except mysql.connector.Error as err:
            print(f"Database Error: {err}")
            connection.rollback()
            return "Registration failed. Please check the terminal logs."
            
        finally:
            cursor.close()
            connection.close()
            
        return redirect(url_for('login'))

    return render_template('register.html')

# --- ROUTE 4: EMPLOYER DASHBOARD ---
@app.route('/employer')
def employer_dashboard():
    # Session verification layer
    if 'role' not in session or session.get('role') != 'Employer':
        return redirect(url_for('login'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # Fetch active job postings for this specific employer
    cursor.execute("""
        SELECT employer.company_name, job.job_title, job.employment_type
        FROM tbl_job_posting job
        JOIN tbl_employer employer ON job.employer_id = employer.employer_id
        WHERE job.employer_id = %s
    """, (session.get('employer_id'),))
    jobs_data = cursor.fetchall()

    # Fetch skill-gap matches
    cursor.execute("""
        SELECT 
            employer.company_name AS company,
            job.job_title AS position,
            learner.first_name AS f_name,
            learner.last_name AS l_name,
            skill.skill_name AS matched_skill
        FROM tbl_job_posting job
        JOIN tbl_employer employer ON job.employer_id = employer.employer_id
        JOIN tbl_job_skill js ON job.job_id = js.job_id
        JOIN tbl_skill skill ON js.skill_id = skill.skill_id
        JOIN tbl_credential_skill cs ON skill.skill_id = cs.skill_id
        JOIN tbl_learner_credential lc ON cs.credential_id = lc.credential_id
        JOIN tbl_learner learner ON lc.learner_id = learner.learner_id
        WHERE job.employer_id = %s
    """, (session.get('employer_id'),))
    matches_data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('employer_dashboard.html', jobs_list=jobs_data, matches_list=matches_data)

# --- ROUTE 5: ADD JOB POSTING ---
@app.route('/add_job', methods=['POST'])
def add_job():
    # Security check: Ensure only authenticated employers can post jobs
    if 'employer_id' not in session:
        return redirect(url_for('login'))

    form_job_title = request.form['job_title']
    form_job_desc = request.form['job_description']
    form_emp_type = request.form['employment_type']
    
    # Retrieve the dynamic employer ID from the current session
    current_employer_id = session.get('employer_id')

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    # Insert job posting with dynamic employer_id and current date
    sql_query = """
        INSERT INTO tbl_job_posting 
        (employer_id, job_title, job_description, employment_type, posting_status, date_posted) 
        VALUES (%s, %s, %s, %s, 'Open', CURDATE())
    """
    values = (current_employer_id, form_job_title, form_job_desc, form_emp_type)
    
    cursor.execute(sql_query, values)
    connection.commit()
    
    cursor.close()
    connection.close()

    return redirect(url_for('employer_dashboard'))

# --- ROUTE 6: LOGOUT ---
@app.route('/logout')
def logout():
    # Clear all session data safely
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)