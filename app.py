from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# --- DATABASE CONFIGURATION ---
db_config = {
    'host': 'localhost',
    'user': 'axislink_admin',
    'password': 'axislink_password', # I-update ito!
    'database': 'axislink_db'
}

# --- ROUTE 1: Ang Front Door (Nagpapakita ng Tables at Form) ---
@app.route('/')
def home():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # 1. Kunin ang Job Postings Data
    cursor.execute("""
        SELECT employer.company_name, job.job_title, job.employment_type
        FROM tbl_job_posting job
        JOIN tbl_employer employer ON job.employer_id = employer.employer_id
    """)
    jobs_data = cursor.fetchall()

    # 2. Kunin ang Skill-Gap Matcher Data (Ang Mega-JOIN)
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
    """)
    matches_data = cursor.fetchall()

    cursor.close()
    connection.close()

    # Ipadala ang dalawang listahan papunta sa HTML
    return render_template('index.html', jobs_list=jobs_data, matches_list=matches_data)

# --- ROUTE 2: Ang Taga-Salo ng Form (Tatanggap ng POST request) ---
@app.route('/add_job', methods=['POST'])
def add_job():
    # Kukunin ang tatlong data mula sa form
    form_job_title = request.form['job_title']
    form_job_desc = request.form['job_description']
    form_emp_type = request.form['employment_type']
    
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    # I-insert ang bagong trabaho (kasama na ang job_description)
    sql_query = """
        INSERT INTO tbl_job_posting (employer_id, job_title, job_description, employment_type, posting_status)
        VALUES (1, %s, %s, %s, 'Open')
    """
    values = (form_job_title, form_job_desc, form_emp_type)
    
    cursor.execute(sql_query, values)
    connection.commit()

    cursor.close()
    connection.close()

    # Ibalik ang user sa home page para makita ang na-update na table
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)