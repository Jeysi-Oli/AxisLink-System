# ==============================================================================
# MODULE: app.py
# DESCRIPTION: Main entry point for the Flask web application. Handles routing, 
#              role-based authentication, user registration, and module-specific
#              dashboards (Employer and Learner).
# ==============================================================================

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
import mysql.connector

app = Flask(__name__)

# Secret key for session security
app.secret_key = 'axislink_super_secret_key'

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'axislink_admin', 
    'password': 'axislink_password', 
    'database': 'axislink_db'
}

# --- ROUTE 1: PUBLIC FRONT PAGE ---
@app.route('/')
def home():
    """
    Renders the public landing page.
    """
    return render_template('index.html')

# --- ROUTE 2: AUTHENTICATION (LOGIN) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handles user authentication.
    Validates credentials against the database, sets secure session variables, 
    and redirects the user to their role-specific dashboard.
    """
    error_message = None
    
    if request.method == 'POST':
        form_email = request.form['email']
        form_password = request.form['password']
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # Query the central user account table
        sql_account = "SELECT * FROM tbl_user_account WHERE email_address = %s"
        cursor.execute(sql_account, (form_email,))
        account = cursor.fetchone()
        
        # Verify account existence and password hash integrity
        if account and check_password_hash(account['password_hash'], form_password):
            role = account['role_type']
            session['role'] = role
            
            # Route dynamically based on user role
            if role == 'Employer':
                sql_employer = "SELECT employer_id, company_name FROM tbl_employer WHERE account_id = %s"
                cursor.execute(sql_employer, (account['account_id'],))
                emp_data = cursor.fetchone()
                
                if emp_data:
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
                    session['learner_id'] = learner_data['learner_id']
                    session['user_id'] = f"{learner_data['first_name']} {learner_data['last_name']}"
                    cursor.close()
                    connection.close()
                    
                    # Direct user to Learner Dashboard upon successful login
                    return redirect(url_for('learner_dashboard'))
        else:
            error_message = "Invalid email or password. Please try again."
            
        cursor.close()
        connection.close()
            
    return render_template('login.html', error=error_message)

# --- ROUTE 3: REGISTRATION ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Processes new user registrations.
    Hashes the password and segregates profile data insertion into either 
    the employer or learner tables based on the selected role.
    """
    if request.method == 'POST':
        form_email = request.form['email']
        form_password = request.form['password']
        form_role = request.form['role'] 
        
        hashed_password = generate_password_hash(form_password)
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        try:
            # Insert root account record
            sql_account = """
                INSERT INTO tbl_user_account (email_address, password_hash, role_type, account_status) 
                VALUES (%s, %s, %s, 'Active')
            """
            cursor.execute(sql_account, (form_email, hashed_password, form_role))
            
            # Retrieve the newly generated primary key
            new_account_id = cursor.lastrowid
            
            # Segregate insertion based on role type
            if form_role == 'Learner':
                form_fname = request.form.get('first_name')
                form_lname = request.form.get('last_name')
                
                # Insert learner with default placeholders to satisfy database constraints
                sql_learner = """
                    INSERT INTO tbl_learner 
                    (account_id, first_name, last_name, middle_name, suffix, date_of_birth, gender, nationality, highest_educational_attainment, home_address, contact_number) 
                    VALUES (%s, %s, %s, '', '', '2000-01-01', 'Male', 'Filipino', 'None', 'To be updated', 'To be updated')
                """
                cursor.execute(sql_learner, (new_account_id, form_fname, form_lname))
                
            elif form_role == 'Employer':
                form_company = request.form.get('company_name')
                
                # Insert employer with default placeholders to satisfy database constraints
                sql_employer = """
                    INSERT INTO tbl_employer 
                    (account_id, company_name, industry_sector, company_address, contact_person, contact_number) 
                    VALUES (%s, %s, 'To be updated', 'To be updated', 'To be updated', 'To be updated')
                """
                cursor.execute(sql_employer, (new_account_id, form_company))
                
            # Finalize transaction
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
    """
    Renders the employer dashboard.
    Fetches active job postings and corresponding skill-gap matches 
    specifically associated with the authenticated employer.
    """
    # Authorization verification
    if 'role' not in session or session.get('role') != 'Employer':
        return redirect(url_for('login'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # Retrieve specific employer's job postings
    cursor.execute("""
        SELECT employer.company_name, job.job_title, job.employment_type
        FROM tbl_job_posting job
        JOIN tbl_employer employer ON job.employer_id = employer.employer_id
        WHERE job.employer_id = %s
    """, (session.get('employer_id'),))
    jobs_data = cursor.fetchall()

    # Retrieve potential learner matches based on required skills
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
    """
    Processes the creation of a new job posting.
    Ensures the posting is tied to the currently authenticated employer.
    """
    # Authorization verification
    if 'employer_id' not in session:
        return redirect(url_for('login'))

    form_job_title = request.form['job_title']
    form_job_desc = request.form['job_description']
    form_emp_type = request.form['employment_type']
    
    current_employer_id = session.get('employer_id')

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

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
    """
    Terminates the user session and redirects to the landing page.
    """
    session.clear()
    return redirect(url_for('home'))

# --- ROUTE 7: LEARNER DASHBOARD ---
@app.route('/learner')
def learner_dashboard():
    """
    Renders the learner dashboard.
    Aggregates profile details, open job markets, available certifications, 
    and the user's acquired credentials.
    """
    if 'role' not in session or session.get('role') != 'Learner':
        return redirect(url_for('login'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # 1. Retrieve base profile information
    cursor.execute("""
        SELECT l.first_name, l.last_name, l.highest_educational_attainment AS education, a.email_address AS email
        FROM tbl_learner l
        JOIN tbl_user_account a ON l.account_id = a.account_id
        WHERE l.learner_id = %s
    """, (session.get('learner_id'),))
    learner_data = cursor.fetchone()

    # 2. Retrieve open job postings globally
    cursor.execute("""
        SELECT employer.company_name, job.job_title, job.employment_type
        FROM tbl_job_posting job
        JOIN tbl_employer employer ON job.employer_id = employer.employer_id
        WHERE job.posting_status = 'Open'
    """)
    jobs_data = cursor.fetchall()

    # 3. Retrieve system-wide available credentials for UI population
    cursor.execute("SELECT credential_id, credential_name FROM tbl_credential")
    credentials_data = cursor.fetchall()

    # 4. Retrieve credentials acquired by the current learner
    cursor.execute("""
        SELECT c.credential_name 
        FROM tbl_learner_credential lc
        JOIN tbl_credential c ON lc.credential_id = c.credential_id
        WHERE lc.learner_id = %s
    """, (session.get('learner_id'),))
    my_credentials_data = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('learner_dashboard.html', 
                           learner_info=learner_data, 
                           jobs_list=jobs_data, 
                           credentials_list=credentials_data,
                           my_credentials_list=my_credentials_data)

# --- ROUTE 8: LEARNER PROFILE UPDATER ---
@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    """
    Handles learner profile modifications.
    Supports GET for rendering current data and POST for applying updates.
    """
    if 'role' not in session or session.get('role') != 'Learner':
        return redirect(url_for('login'))

    current_learner_id = session.get('learner_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        f_name = request.form['first_name']
        m_name = request.form['middle_name']
        l_name = request.form['last_name']
        dob = request.form['date_of_birth']
        gender = request.form['gender']
        nationality = request.form['nationality']
        contact = request.form['contact_number']
        education = request.form['education']
        address = request.form['home_address']

        # Update existing learner record
        sql_update = """
            UPDATE tbl_learner 
            SET first_name = %s, middle_name = %s, last_name = %s, date_of_birth = %s, 
                gender = %s, nationality = %s, contact_number = %s, 
                highest_educational_attainment = %s, home_address = %s
            WHERE learner_id = %s
        """
        values = (f_name, m_name, l_name, dob, gender, nationality, contact, education, address, current_learner_id)
        
        cursor.execute(sql_update, values)
        connection.commit()
        
        cursor.close()
        connection.close()
        return redirect(url_for('learner_dashboard'))

    else:
        # Pre-populate the form with current data on GET request
        cursor.execute("SELECT * FROM tbl_learner WHERE learner_id = %s", (current_learner_id,))
        current_data = cursor.fetchone()
        
        cursor.close()
        connection.close()
        return render_template('update_profile.html', learner=current_data)

# --- ROUTE 9: ADD CREDENTIAL ---
@app.route('/add_credential', methods=['POST'])
def add_credential():
    """
    Associates a selected credential with the authenticated learner's profile.
    Silently handles duplicate entry exceptions.
    """
    if 'role' not in session or session.get('role') != 'Learner':
        return redirect(url_for('login'))

    current_learner_id = session.get('learner_id')
    selected_credential_id = request.form.get('credential_id')

    if selected_credential_id:
        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()

            sql_insert = """
                INSERT INTO tbl_learner_credential (learner_id, credential_id) 
                VALUES (%s, %s)
            """
            cursor.execute(sql_insert, (current_learner_id, selected_credential_id))
            connection.commit()

            cursor.close()
            connection.close()
            
        except Exception as e:
            # Catch exceptions (e.g., duplicate unique key constraints)
            print(f"Database Error: {e}")

    return redirect(url_for('learner_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)