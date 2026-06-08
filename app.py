from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import csv
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'dev_secret_key_change_in_production'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEN_CSV_FILEPATH = os.path.join(BASE_DIR, 'Sen List V1.csv')
POS_CSV_FILEPATH = os.path.join(BASE_DIR, 'Position Code.csv')
SALARY_CSV_FILEPATH = os.path.join(BASE_DIR, 'salary_scales.csv')
EQ_CSV_FILEPATH = os.path.join(BASE_DIR, 'Equity-scales.csv') # NEW: Equity Scales DB

# Authentication Database (In-Memory for PoC; resets on server restart)
users = {
    "admin": generate_password_hash("admin123")
}

def login_required(f):
    def wrapper(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        if username in users and check_password_hash(users[username], password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid credentials")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    # Capture separate search queries for all tables
    search_sen = request.args.get('search_sen', '').strip().lower()
    search_pos = request.args.get('search_pos', '').strip().lower()
    search_sal = request.args.get('search_sal', '').strip().lower()
    search_eq = request.args.get('search_eq', '').strip().lower() # NEW
    
    sen_data, headers = [], []
    pos_data, pos_headers = [], []
    sal_data, sal_headers = [], []
    eq_data, eq_headers = [], [] # NEW
    
    # 1. Load Seniority List Data
    if os.path.exists(SEN_CSV_FILEPATH):
        with open(SEN_CSV_FILEPATH, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader, [])
            for row in reader:
                if search_sen:
                    if any(search_sen in cell.lower() for cell in row):
                        sen_data.append(row)
                else:
                    sen_data.append(row)
                    
    # 2. Load Position Code Data
    if os.path.exists(POS_CSV_FILEPATH):
        with open(POS_CSV_FILEPATH, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            pos_headers = next(reader, [])
            for row in reader:
                if search_pos:
                    if any(search_pos in cell.lower() for cell in row):
                        pos_data.append(row)
                else:
                    pos_data.append(row)

    # 3. Load Salary Scales Data
    if os.path.exists(SALARY_CSV_FILEPATH):
        with open(SALARY_CSV_FILEPATH, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            sal_headers = next(reader, [])
            for row in reader:
                if search_sal:
                    if any(search_sal in cell.lower() for cell in row):
                        sal_data.append(row)
                else:
                    sal_data.append(row)

    # 4. Load Equity Scales Data (NEW)
    if os.path.exists(EQ_CSV_FILEPATH):
        with open(EQ_CSV_FILEPATH, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            eq_headers = next(reader, [])
            for row in reader:
                if search_eq:
                    if any(search_eq in cell.lower() for cell in row):
                        eq_data.append(row)
                else:
                    eq_data.append(row)
            
    return render_template('index.html', 
                           headers=headers, sen_data=sen_data, search_sen=request.args.get('search_sen', ''),
                           pos_headers=pos_headers, pos_data=pos_data, search_pos=request.args.get('search_pos', ''),
                           sal_headers=sal_headers, sal_data=sal_data, search_sal=request.args.get('search_sal', ''),
                           eq_headers=eq_headers, eq_data=eq_data, search_eq=request.args.get('search_eq', ''))

@app.route('/update_csv', methods=['POST'])
@login_required
def update_csv():
    data = request.json
    row_idx = int(data.get('row'))
    col_idx = int(data.get('col'))
    new_value = data.get('value')
    file_type = data.get('file_type') # Identifies which table was edited

    # Route the save action to the correct CSV file
    if file_type == 'position':
        target_filepath = POS_CSV_FILEPATH
    elif file_type == 'salary':
        target_filepath = SALARY_CSV_FILEPATH
    elif file_type == 'equity':
        target_filepath = EQ_CSV_FILEPATH
    else:
        target_filepath = SEN_CSV_FILEPATH

    if os.path.exists(target_filepath):
        with open(target_filepath, mode='r', encoding='utf-8') as file:
            reader = list(csv.reader(file))

        if row_idx + 1 < len(reader) and col_idx < len(reader[row_idx + 1]):
            reader[row_idx + 1][col_idx] = new_value

        with open(target_filepath, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(reader)

        return jsonify({"status": "success", "message": "CSV updated."})
    return jsonify({"status": "error", "message": "File not found."})

# UTILITY ROUTE: Add New User
@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    data = request.json
    new_username = data.get('username', '').strip()
    new_password = data.get('password', '')

    if not new_username or not new_password:
        return jsonify({"status": "error", "message": "Username and password required."})
    
    if new_username in users:
        return jsonify({"status": "error", "message": "User already exists."})

    users[new_username] = generate_password_hash(new_password)
    return jsonify({"status": "success", "message": f"User '{new_username}' added successfully!"})

# UTILITY ROUTE: Change Password
@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    data = request.json
    current_user = session.get('username')
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if current_user in users and check_password_hash(users[current_user], old_password):
        users[current_user] = generate_password_hash(new_password)
        return jsonify({"status": "success", "message": "Password updated successfully!"})
    
    return jsonify({"status": "error", "message": "Incorrect current password."})

if __name__ == '__main__':
    app.run(debug=True)