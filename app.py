# ==============================================================================
# MODULE: app.py
# DESCRIPTION: Final Master File for AxisLink (Unified Direct Issuance Update)
# ==============================================================================

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
import mysql.connector

app = Flask(__name__)
app.secret_key = 'axislink_super_secret_key'

db_config = {
    'host': 'localhost',
    'user': 'axislink_admin', 
    'password': 'axislink_password', 
    'database': 'axislink_db'
}

# ==============================================================================
# PUBLIC & AUTHENTICATION ROUTES
# ==============================================================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST':
        form_email = request.form['email']
        form_password = request.form['password']
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        sql_account = "SELECT * FROM tbl_user_account WHERE email_address = %s"
        cursor.execute(sql_account, (form_email,))
        account = cursor.fetchone()
        
        if account and check_password_hash(account['password_hash'], form_password):
            role = account['role_type']
            session['role'] = role
            session['account_id'] = account['account_id']
            
            if role == 'Admin':
                session['admin_id'] = account['account_id']
                session['user_id'] = 'System Administrator'
                cursor.close()
                connection.close()
                return redirect(url_for('admin_dashboard'))
        
            elif role == 'Learner':
                sql_learner = "SELECT learner_id, first_name, middle_name, last_name FROM tbl_learner WHERE account_id = %s"
                cursor.execute(sql_learner, (account['account_id'],))
                learner_data = cursor.fetchone()
                if learner_data:
                    session['learner_id'] = learner_data['learner_id']
                    f_name = learner_data['first_name']
                    m_name = learner_data['middle_name']
                    l_name = learner_data['last_name']
                    if m_name and m_name.strip() != '':
                        session['user_id'] = f"{f_name} {m_name.strip()[0].upper()}. {l_name}"
                    else:
                        session['user_id'] = f"{f_name} {l_name}"
                    cursor.close()
                    connection.close()
                    return redirect(url_for('learner_dashboard'))
            
            elif role == 'Institution':
                sql_inst = "SELECT institution_id, institution_name FROM tbl_institution WHERE account_id = %s"
                cursor.execute(sql_inst, (account['account_id'],))
                inst_data = cursor.fetchone()
                if inst_data:
                    session['institution_id'] = inst_data['institution_id']
                    session['user_id'] = inst_data['institution_name']
                    cursor.close()
                    connection.close()
                    return redirect(url_for('institution_dashboard'))
            
            elif role == 'Employer':
                sql_employer = "SELECT employer_id, company_name FROM tbl_employer WHERE account_id = %s"
                cursor.execute(sql_employer, (account['account_id'],))
                emp_data = cursor.fetchone()
                if emp_data:
                    session['employer_id'] = emp_data['employer_id']
                    session['user_id'] = emp_data['company_name']
                    cursor.close()
                    connection.close()
                    return redirect(url_for('employer_dashboard'))
            
        else:
            error_message = "Invalid email or password. Please try again."
        cursor.close()
        connection.close()
    return render_template('login.html', error=error_message)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        form_email = request.form['email']
        form_password = request.form['password']
        form_role = request.form['role'] 
        
        hashed_password = generate_password_hash(form_password)
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        try:
            sql_account = "INSERT INTO tbl_user_account (email_address, password_hash, role_type, account_status) VALUES (%s, %s, %s, 'Active')"
            cursor.execute(sql_account, (form_email, hashed_password, form_role))
            new_account_id = cursor.lastrowid
            
            if form_role == 'Learner':
                form_fname = request.form.get('first_name')
                form_lname = request.form.get('last_name')
                sql_learner = """
                    INSERT INTO tbl_learner 
                    (account_id, first_name, last_name, middle_name, suffix, date_of_birth, gender, nationality, highest_educational_attainment, home_address, contact_number) 
                    VALUES (%s, %s, %s, '', '', '2000-01-01', 'Male', 'Filipino', 'None', 'To be updated', 'To be updated')
                """
                cursor.execute(sql_learner, (new_account_id, form_fname, form_lname))
                
            elif form_role == 'Employer':
                form_company = request.form.get('company_name')
                sql_employer = """
                    INSERT INTO tbl_employer 
                    (account_id, company_name, industry_sector, company_address, contact_person, contact_number) 
                    VALUES (%s, %s, 'To be updated', 'To be updated', 'To be updated', 'To be updated')
                """
                cursor.execute(sql_employer, (new_account_id, form_company))

            elif form_role == 'Institution':
                form_inst_name = request.form.get('institution_name')
                sql_institution = """
                    INSERT INTO tbl_institution 
                    (account_id, institution_name, accreditation_type, headquarters_address, contact_person, contact_number) 
                    VALUES (%s, %s, 'Other', 'To be updated', 'To be updated', 'To be updated')
                """
                cursor.execute(sql_institution, (new_account_id, form_inst_name))
                
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Database Error: {err}")
            connection.rollback()
        finally:
            cursor.close()
            connection.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ==============================================================================
# EMPLOYER ECOSYSTEM SUB-SYSTEM
# ==============================================================================

@app.route('/employer')
def employer_dashboard():
    if 'role' not in session or session.get('role') != 'Employer':
        return redirect(url_for('login'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT e.*, a.email_address 
        FROM tbl_employer e
        JOIN tbl_user_account a ON e.account_id = a.account_id
        WHERE e.employer_id = %s
    """, (session.get('employer_id'),))
    employer_info = cursor.fetchone()

    cursor.execute("""
        SELECT job_id, company_name, job_title, employment_type
        FROM tbl_job_posting job
        JOIN tbl_employer employer ON job.employer_id = employer.employer_id
        WHERE job.employer_id = %s
    """, (session.get('employer_id'),))
    jobs_data = cursor.fetchall()

    cursor.execute("SELECT * FROM tbl_skill ORDER BY skill_category, skill_name")
    master_skills = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT learner.learner_id, job.job_id, employer.company_name AS company,
            job.job_title AS position, learner.first_name AS f_name, learner.middle_name AS m_name, learner.last_name AS l_name
        FROM tbl_job_posting job
        JOIN tbl_employer employer ON job.employer_id = employer.employer_id
        JOIN tbl_job_skill js ON job.job_id = js.job_id
        JOIN tbl_credential_skill cs ON js.skill_id = cs.skill_id
        JOIN tbl_learner_credential lc ON cs.credential_id = lc.credential_id
        JOIN tbl_learner learner ON lc.learner_id = learner.learner_id
        WHERE job.employer_id = %s AND lc.visibility_status = 'Public'
    """, (session.get('employer_id'),))
    matches_data = cursor.fetchall()

    cursor.close()
    connection.close()
    return render_template('employer_dashboard.html', employer=employer_info, jobs_list=jobs_data, matches_list=matches_data, skills=master_skills)

@app.route('/update_employer_profile', methods=['GET', 'POST'])
def update_employer_profile():
    if 'role' not in session or session.get('role') != 'Employer':
        return redirect(url_for('login'))
        
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    
    if request.method == 'POST':
        comp_name = request.form['company_name']
        ind_sector = request.form['industry_sector']
        comp_add = request.form['company_address']
        cont_person = request.form['contact_person']
        cont_num = request.form['contact_number']
        
        cursor.execute("""
            UPDATE tbl_employer 
            SET company_name=%s, industry_sector=%s, company_address=%s, contact_person=%s, contact_number=%s
            WHERE employer_id=%s
        """, (comp_name, ind_sector, comp_add, cont_person, cont_num, session.get('employer_id')))
        connection.commit()
        session['user_id'] = comp_name
        session.modified = True
        cursor.close()
        connection.close()
        return redirect(url_for('employer_dashboard'))
    else:
        cursor.execute("SELECT * FROM tbl_employer WHERE employer_id=%s", (session.get('employer_id'),))
        data = cursor.fetchone()
        cursor.close()
        connection.close()
        return render_template('update_employer_profile.html', employer=data)

@app.route('/add_job', methods=['POST'])
def add_job():
    if 'employer_id' not in session:
        return redirect(url_for('login'))
    
    form_job_title = request.form['job_title']
    form_job_desc = request.form['job_description']
    form_emp_type = request.form['employment_type']
    selected_skills = request.form.getlist('skills')

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    
    cursor.execute("INSERT INTO tbl_job_posting (employer_id, job_title, job_description, employment_type, posting_status) VALUES (%s, %s, %s, %s, 'Open')", 
                   (session.get('employer_id'), form_job_title, form_job_desc, form_emp_type))
    new_job_id = cursor.lastrowid 
    
    for skill_id in selected_skills:
        cursor.execute("INSERT INTO tbl_job_skill (job_id, skill_id) VALUES (%s, %s)", (new_job_id, skill_id))
        
    connection.commit()
    cursor.close()
    connection.close()
    return redirect(url_for('employer_dashboard'))

@app.route('/delete_job/<int:job_id>')
def delete_job(job_id):
    if 'role' not in session or session.get('role') != 'Employer':
        return redirect(url_for('login'))
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM tbl_job_skill WHERE job_id = %s", (job_id,))
    cursor.execute("DELETE FROM tbl_job_posting WHERE job_id = %s AND employer_id = %s", (job_id, session.get('employer_id')))
    connection.commit()
    cursor.close()
    connection.close()
    return redirect(url_for('employer_dashboard'))

@app.route('/calculate_gap', methods=['POST'])
def calculate_gap():
    if 'role' not in session or session.get('role') != 'Employer':
        return redirect(url_for('login'))
    form_learner_id = request.form['learner_id']
    form_job_id = request.form['job_id']
    learner_full_name = request.form['learner_name']
    job_position = request.form['job_title']
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    try:
        cursor.execute("CALL sp_calculate_skill_gap(%s, %s, @match_percentage)", (form_learner_id, form_job_id))
        cursor.execute("SELECT @match_percentage")
        result = cursor.fetchone()
        final_score = result[0] if result[0] else 0
    finally:
        cursor.close()
        connection.close()
    return render_template('match_result.html', score=final_score, applicant=learner_full_name, role=job_position)

@app.route('/view_learner/<int:learner_id>')
def view_learner(learner_id):
    if 'role' not in session or session.get('role') != 'Employer':
        return redirect(url_for('login'))
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT l.*, a.email_address FROM tbl_learner l
        JOIN tbl_user_account a ON l.account_id = a.account_id WHERE l.learner_id = %s
    """, (learner_id,))
    learner_info = cursor.fetchone()
    cursor.execute("""
        SELECT c.credential_name, i.institution_name, lc.date_acquired 
        FROM tbl_learner_credential lc
        JOIN tbl_credential c ON lc.credential_id = c.credential_id
        JOIN tbl_institution i ON c.institution_id = i.institution_id
        WHERE lc.learner_id = %s AND lc.visibility_status = 'Public'
    """, (learner_id,))
    portfolio_data = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('learner_profile_view.html', learner=learner_info, portfolio=portfolio_data)

# ==============================================================================
# LEARNER ECOSYSTEM SUB-SYSTEM
# ==============================================================================

@app.route('/learner')
def learner_dashboard():
    if 'role' not in session or session.get('role') != 'Learner':
        return redirect(url_for('login'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    learner_id = session.get('learner_id')

    cursor.execute("""
        SELECT l.first_name, l.middle_name, l.last_name, l.highest_educational_attainment AS education, a.email_address AS email
        FROM tbl_learner l
        JOIN tbl_user_account a ON l.account_id = a.account_id
        WHERE l.learner_id = %s
    """, (learner_id,))
    learner_data = cursor.fetchone()

    cursor.execute("""
        SELECT employer.company_name, job.job_title, job.employment_type
        FROM tbl_job_posting job
        JOIN tbl_employer employer ON job.employer_id = employer.employer_id
        WHERE job.posting_status = 'Open'
    """)
    jobs_data = cursor.fetchall()

    cursor.execute("""
        SELECT lc.learner_credential_id, c.credential_name, lc.visibility_status 
        FROM tbl_learner_credential lc
        JOIN tbl_credential c ON lc.credential_id = c.credential_id
        WHERE lc.learner_id = %s
    """, (learner_id,))
    my_credentials_data = cursor.fetchall()

    cursor.close()
    connection.close()
    return render_template('learner_dashboard.html', 
                           learner_info=learner_data, 
                           jobs_list=jobs_data, 
                           my_credentials_list=my_credentials_data)

@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
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

        cursor.execute("""
            UPDATE tbl_learner 
            SET first_name = %s, middle_name = %s, last_name = %s, date_of_birth = %s, 
                gender = %s, nationality = %s, contact_number = %s, 
                highest_educational_attainment = %s, home_address = %s
            WHERE learner_id = %s
        """, (f_name, m_name, l_name, dob, gender, nationality, contact, education, address, current_learner_id))
        connection.commit()
        
        if m_name and m_name.strip() != '':
            session['user_id'] = f"{f_name} {m_name.strip()[0].upper()}. {l_name}"
        else:
            session['user_id'] = f"{f_name} {l_name}"
            
        session.modified = True 
        cursor.close()
        connection.close()
        return redirect(url_for('learner_dashboard'))

    else:
        cursor.execute("SELECT * FROM tbl_learner WHERE learner_id = %s", (current_learner_id,))
        current_data = cursor.fetchone()
        cursor.close()
        connection.close()
        return render_template('update_profile.html', learner=current_data)

@app.route('/toggle_visibility/<int:lc_id>')
def toggle_visibility(lc_id):
    if 'role' not in session or session.get('role') != 'Learner':
        return redirect(url_for('login'))
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE tbl_learner_credential 
        SET visibility_status = IF(visibility_status = 'Private', 'Public', 'Private')
        WHERE learner_credential_id = %s AND learner_id = %s
    """, (lc_id, session.get('learner_id')))
    connection.commit()
    cursor.close()
    connection.close()
    return redirect(url_for('learner_dashboard'))

# ==============================================================================
# INSTITUTION ECOSYSTEM SUB-SYSTEM
# ==============================================================================

@app.route('/institution')
def institution_dashboard():
    if 'role' not in session or session.get('role') != 'Institution':
        return redirect(url_for('login'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT i.*, a.email_address 
        FROM tbl_institution i
        JOIN tbl_user_account a ON i.account_id = a.account_id
        WHERE i.institution_id = %s
    """, (session.get('institution_id'),))
    inst_info = cursor.fetchone()

    cursor.execute("SELECT * FROM tbl_skill ORDER BY skill_category, skill_name")
    master_skills = cursor.fetchall()

    cursor.execute("""
        SELECT lc.learner_credential_id, l.first_name, l.last_name, c.credential_name, lc.date_acquired 
        FROM tbl_learner_credential lc
        JOIN tbl_learner l ON lc.learner_id = l.learner_id
        JOIN tbl_credential c ON lc.credential_id = c.credential_id
        WHERE c.institution_id = %s
        ORDER BY lc.date_acquired DESC
    """, (session.get('institution_id'),))
    issued_list = cursor.fetchall()
    
    cursor.close()
    connection.close()
    return render_template('institution_dashboard.html', institution=inst_info, issued_credentials=issued_list, skills=master_skills)

@app.route('/update_institution_profile', methods=['GET', 'POST'])
def update_institution_profile():
    if 'role' not in session or session.get('role') != 'Institution':
        return redirect(url_for('login'))
        
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    
    if request.method == 'POST':
        inst_name = request.form['institution_name']
        acc_type = request.form['accreditation_type']
        hq_add = request.form['headquarters_address']
        cont_person = request.form['contact_person']
        cont_num = request.form['contact_number']
        
        cursor.execute("""
            UPDATE tbl_institution 
            SET institution_name=%s, accreditation_type=%s, headquarters_address=%s, contact_person=%s, contact_number=%s
            WHERE institution_id=%s
        """, (inst_name, acc_type, hq_add, cont_person, cont_num, session.get('institution_id')))
        connection.commit()
        session['user_id'] = inst_name
        session.modified = True
        cursor.close()
        connection.close()
        return redirect(url_for('institution_dashboard'))
    else:
        cursor.execute("SELECT * FROM tbl_institution WHERE institution_id=%s", (session.get('institution_id'),))
        data = cursor.fetchone()
        cursor.close()
        connection.close()
        return render_template('update_institution_profile.html', institution=data)

# UNIFIED ROUTE: DIRECT ISSUANCE
@app.route('/issue_direct_credential', methods=['POST'])
def issue_direct_credential():
    if 'role' not in session or session.get('role') != 'Institution':
        return redirect(url_for('login'))

    form_name = request.form['credential_name']
    form_desc = request.form.get('credential_description', '')
    form_validity = request.form.get('validity_years', 0)
    selected_skills = request.form.getlist('skills')
    learner_email = request.form.get('learner_email')

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT l.learner_id FROM tbl_learner l
        JOIN tbl_user_account a ON l.account_id = a.account_id WHERE a.email_address = %s
    """, (learner_email,))
    learner = cursor.fetchone()

    if learner:
        cursor.execute("INSERT INTO tbl_credential (institution_id, credential_name, credential_description, validity_years) VALUES (%s, %s, %s, %s)", 
                       (session.get('institution_id'), form_name, form_desc, form_validity))
        new_cred_id = cursor.lastrowid 
        
        for skill_id in selected_skills:
            cursor.execute("INSERT INTO tbl_credential_skill (credential_id, skill_id) VALUES (%s, %s)", (new_cred_id, skill_id))

        cursor.execute("""
            INSERT INTO tbl_learner_credential (learner_id, credential_id, date_acquired, expiration_date, credential_status, visibility_status)
            VALUES (%s, %s, CURDATE(), IF(%s = 0, '2099-12-31', DATE_ADD(CURDATE(), INTERVAL %s YEAR)), 'ACTIVE', 'Private')
        """, (learner['learner_id'], new_cred_id, form_validity, form_validity))

        connection.commit()
    
    cursor.close()
    connection.close()
    return redirect(url_for('institution_dashboard'))

@app.route('/revoke_issued_credential/<int:lc_id>')
def revoke_issued_credential(lc_id):
    if 'role' not in session or session.get('role') != 'Institution':
        return redirect(url_for('login'))
        
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM tbl_learner_credential WHERE learner_credential_id = %s", (lc_id,))
    connection.commit()
    cursor.close()
    connection.close()
    return redirect(url_for('institution_dashboard'))

# ==============================================================================
# ACCOUNT DELETION CORE ROUTINE (Cascading Protection Layer)
# ==============================================================================

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'account_id' not in session:
        return redirect(url_for('login'))

    account_id = session.get('account_id')
    role = session.get('role')
    
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
    
    try:
        if role == 'Learner':
            learner_id = session.get('learner_id')
            cursor.execute("DELETE FROM tbl_learner_credential WHERE learner_id = %s", (learner_id,))
            cursor.execute("DELETE FROM tbl_learner WHERE account_id = %s", (account_id,))
            
        elif role == 'Employer':
            employer_id = session.get('employer_id')
            cursor.execute("DELETE FROM tbl_job_skill WHERE job_id IN (SELECT job_id FROM tbl_job_posting WHERE employer_id = %s)", (employer_id,))
            cursor.execute("DELETE FROM tbl_job_posting WHERE employer_id = %s", (employer_id,))
            cursor.execute("DELETE FROM tbl_employer WHERE account_id = %s", (account_id,))
            
        elif role == 'Institution':
            inst_id = session.get('institution_id')
            cursor.execute("DELETE FROM tbl_learner_credential WHERE credential_id IN (SELECT credential_id FROM tbl_credential WHERE institution_id = %s)", (inst_id,))
            cursor.execute("DELETE FROM tbl_credential_skill WHERE credential_id IN (SELECT credential_id FROM tbl_credential WHERE institution_id = %s)", (inst_id,))
            cursor.execute("DELETE FROM tbl_credential WHERE institution_id = %s", (inst_id,))
            cursor.execute("DELETE FROM tbl_institution WHERE account_id = %s", (account_id,))
        
        cursor.execute("DELETE FROM tbl_user_account WHERE account_id = %s", (account_id,))
        connection.commit()
        
    except mysql.connector.Error as err:
        print(f"Cascading Deletion Aborted: {err}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()
        
    session.clear()
    return redirect(url_for('home'))

@app.route('/admin')
def admin_dashboard():
    if 'role' not in session or session.get('role') != 'Admin':
        return redirect(url_for('login'))
    return "<h1>Admin Dashboard (Under Construction)</h1><a href='/logout'>Logout</a>"

if __name__ == '__main__':
    app.run(debug=True)