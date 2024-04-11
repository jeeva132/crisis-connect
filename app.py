from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from sklearn.svm import SVC
from flask_mysqldb import MySQL
import hashlib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import os

app = Flask(__name__)
# app.config['MYSQL_HOST'] = 'localhost'
# app.config['MYSQL_USER'] = 'root'
# app.config['MYSQL_PASSWORD'] = ''
# app.config['MYSQL_DB'] = 'crisis'
app.secret_key = os.environ.get('SECRET_KEY')

app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST')
app.config['MYSQL_PORT'] = int(os.environ.get('MYSQL_PORT'))
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB')
app.config['MYSQL_SSL_MODE'] = os.environ.get('MYSQL_SSL_MODE', 'REQUIRED')

mysql = MySQL(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/regi')
def regi():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')



# Modify your login() route in app.py
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    cur = mysql.connection.cursor()

    if email.endswith('gmail.com'):
        cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, hashed_password))
        user = cur.fetchone()

        if user:
            session['id'] = user[0]  # Assuming user ID is the first column in your users table
            flash('Login successful', 'success')
            return redirect(url_for('user'))
        else:
            flash('Login unsuccessful. Please check your email and password.', 'danger')
            return redirect(url_for('home'))

    elif email.endswith('dept.com'):
        cur.execute("SELECT * FROM departmentdetails WHERE Email = %s AND Password = %s", (email, password))
        user = cur.fetchone()

        if user:
            session['DepartmentID'] = user[1]  # Assuming DepartmentID is the second column in your departmentdetails table
            flash('Login successful', 'success')
            return redirect(url_for('dept'))
        else:
            flash('Login unsuccessful. Please check your email and password.', 'danger')
            return redirect(url_for('home'))

    else:
        flash('Invalid email domain. Please use a valid email.', 'danger')
        return redirect(url_for('home'))


@app.route('/user')
def user():
    user_id = session.get('id')  # Corrected the session key
    if not user_id:
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()
    # Fetch Alerts data
    cur.execute("SELECT * FROM alerts WHERE Status = 'Not yet resolved'")
    alerts = cur.fetchall()

    # Fetch information data
    cur.execute("SELECT * FROM information")
    information = cur.fetchall()

    cur.close()

    return render_template('user.html', alerts=alerts, information=information)

# //////////////////////////////
# ML MODEL
def train_model():
    # Load the dataset
    data = pd.read_csv(r"C:\Users\hp\OneDrive\Documents\project\static\water.csv")

    # Split data into features (X) and labels (y)
    X = data[['threshold_value']]
    y = data['result']
    # Initialize the model
    model = RandomForestClassifier()

    # Train the model
    model.fit(X, y)

    return model
    

# Train the model when the server starts
model = train_model()

def predict(ax, ay, az):
    # Load the earthquake detection data
    data = pd.read_csv(r'C:\Users\hp\OneDrive\Documents\project\static\earth2.csv')
    
    # Check for missing values
    if data.isnull().values.any():
        return jsonify({'error': 'Missing values detected in the dataset'})

    # Separate features and target variable
    X = data[['axisx', 'axisy', 'axisz']]
    y = data['output']
    
    # Train the SVM model
    svm_model = SVC(kernel='linear')
    svm_model.fit(X, y)
    
    # Predict whether an earthquake will occur
    prediction = svm_model.predict([[ax, ay, az]])
    
    # Prepare response
    response = {'prediction': bool(prediction[0])}
    
    return prediction[0]



# Modify your dept() route in app.py
@app.route('/dept', methods=['GET','POST'])
def dept():
    if request.method == 'POST':
        if request.headers['Content-Type'] == 'application/x-www-form-urlencoded':
            # If content type is application/x-www-form-urlencoded
            data = request.form.to_dict()
        elif request.headers['Content-Type'] == 'application/json':
            # If content type is application/json
            data = request.get_json()
        else:
            return jsonify({"error": "Unsupported Media Type"}), 415

        print("Received data:", data)
        print(type(data.get('DepartmentID')))
        if data.get('DepartmentID') == '5':
            latitude = float(data.get('latitude'))
            longitude = float(data.get('longitude'))
            # flame_value = int(data.get('flameValue'))
            department_id = int(data.get('DepartmentID'))
            axisX = int(data.get('axisX'));
            axisY  = int(data.get('axisY'));
            axisZ  = int(data.get('axisZ'));
            details = data.get('details')
            print(data)
            print(department_id)
            p = predict(axisX,axisY,axisZ)
            print(p)
            if p:
                cur = mysql.connection.cursor()
                cur.execute('''INSERT INTO alerts (Name, DepartmentID, Location, Details, DataReadings, Status)
                            VALUES (%s, %s, %s, %s, %s, %s)''', 
                        ('Earthquake department', int(data.get('DepartmentID')), f"{latitude}, {longitude}", 
                        data.get('details'), f"Magnitude of earthquake: {axisX},{axisY},{axisZ}", 'Not yet resolved'))

                mysql.connection.commit()
                cur.close()
        # Extract latitude and longitude from the received data
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        if data.get('DepartmentID') == '1':
            print('hello')
            # Extract water level from the received data
            water_level = int(data.get('waterLevel').split(': ')[1])
            print(water_level)
            prediction = model.predict([[water_level]])
            print(prediction)
            # Insert data into MySQL if prediction is True
            # if prediction[0] and data.get('DepartmentID') == '1':
            if prediction[0]:


                # Insert data into MySQL
                cur = mysql.connection.cursor()
                cur.execute('''INSERT INTO alerts (Name, DepartmentID, Location, Details, DataReadings, Status)
                        VALUES (%s, %s, %s, %s, %s, %s)''', 
                    ('Flood department', int(data.get('DepartmentID')), f"{latitude}, {longitude}", 
                    data.get('details'), f"WaterLevel: {water_level}", 'Not yet resolved'))

                mysql.connection.commit()
                cur.close()
            else:
                print('wrong in prediction')
        if data.get('DepartmentID') == '2':
            latitude = float(data.get('latitude'))
            longitude = float(data.get('longitude'))
            flame_value = int(data.get('flameValue'))
            department_id = int(data.get('DepartmentID'))
            details = data.get('details')
            print(data)
            print(department_id)
            cur = mysql.connection.cursor()
            cur.execute('''INSERT INTO alerts (Name, DepartmentID, Location, Details, DataReadings, Status)
                        VALUES (%s, %s, %s, %s, %s, %s)''', 
                    ('Fire department', int(data.get('DepartmentID')), f"{latitude}, {longitude}", 
                    data.get('details'), f"Flame value: {flame_value}", 'Not yet resolved'))

            mysql.connection.commit()
            cur.close()

        # return jsonify({"message": "Data inserted successfully"})

    # return 'hii'

    department_id = session.get('DepartmentID')
    
    print(department_id)
    if not department_id:
        flash('Department ID not found. Please log in.', 'danger')
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()

    # Retrieve alerts for the logged-in department
    cur.execute("SELECT * FROM alerts WHERE DepartmentID = %s AND Status = 'Not yet resolved' ORDER BY AlertID LIMIT 3", (department_id,))
    alerts = cur.fetchall()

    # Retrieve information for the logged-in department
    cur.execute("SELECT * FROM information WHERE DepartmentID = %s", (department_id,))
    information_data = cur.fetchall()
    print(information_data)

    # Retrieve Messages for the logged-in department
    cur.execute("SELECT * FROM messages WHERE department_id = %s",(department_id,))
    messages_data = cur.fetchall()

    cur.execute("SELECT temperature FROM  temperaturehumiditydata WHERE id = 1")
    temp_hum_data = cur.fetchone()

    cur.close()

    # print("alerts:", alerts)
    # print("information Data:", information_data)
    # print("dept id",department_id)
    # print("Messages Data:", messages_data)
    return render_template('dep.html', alerts=alerts, information_data=information_data, messages_data=messages_data)

@app.route('/resolve_alert/<int:alert_id>', methods=['POST'])
def resolve_alert(alert_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE alerts SET Status = 'Resolved' WHERE AlertID = %s", (alert_id,))
    mysql.connection.commit()
    cur.close()
    flash('Alert marked as resolved', 'success')
    return redirect(url_for('dept'))

@app.route('/register', methods=['POST'])
def register():
    name = request.form['fullname']
    email = request.form['email']
    phone = request.form['phone']
    password = request.form['confirmpassword']

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO users (name, email, phone, password) VALUES (%s, %s, %s, %s)",
                (name, email, phone, hashed_password))
    mysql.connection.commit()
    cur.close()

    flash('Registration successful', 'success')
    return redirect(url_for('home'))

@app.route('/submit_message', methods=['POST'])
def submit_message():
    # Retrieve user details from the session
    user_id = session.get('id')
    cur = mysql.connection.cursor()
    
    # Fetch user_name and user_phone from the 'users' table
    cur.execute("SELECT name, phone FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    
    # Check if user_data is not None before accessing its elements
    if user_data:
        user_name, user_phone = user_data
    else:
        user_name, user_phone = None, None

    print(user_id)
    print(user_name)
    print(user_phone)
    cur.close()
    # Retrieve form data
    details = request.form['details']
    location = request.form['location']
    selected_department = request.form['department']

    # Retrieve department_id based on the selected_department
    cur = mysql.connection.cursor()
    cur.execute("SELECT DepartmentID FROM departments WHERE DepartmentName = %s", (selected_department,))
    department_id = cur.fetchone()[0]
    print(department_id)  # Assuming DepartmentID is the first column
    cur.close()

    # Insert the message into the messages table
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO messages (name, phone, details, location, user_id, department_id) VALUES (%s, %s, %s, %s, %s, %s)", (user_name, user_phone, details, location, user_id, department_id))
    mysql.connection.commit()
    cur.close()

    flash('Message submitted successfully', 'success')
    return redirect(url_for('user'))

@app.route('/add_alert', methods=['POST'])
def add_alert():
    # Retrieve form data
    alert_name = request.form.get('alertName')
    location = request.form.get('location')  # Add other form fields as needed
    details = request.form.get('details')
    data_readings = request.form.get('dataReadings')

    # Retrieve department ID from the session
    department_id = session.get('DepartmentID')

    if not department_id:
        flash('Department ID not found. Please log in.', 'danger')
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()
    print(department_id)

    # Insert the new alert into the alerts table
    cur.execute("""
        INSERT INTO alerts (Name, DepartmentID, Location, Details, DataReadings, Status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (alert_name, department_id, location, details, data_readings, 'Not yet resolved'))

    mysql.connection.commit()
    cur.close()

    flash('Alert added successfully', 'success')
    return redirect(url_for('dept'))



if __name__ == '__main__':
    app.run(debug=True)
    # app.run(host='192.168.9.134',port=5000,debug=True)

# GET DIRECTIONS FOR THE DEPAERTMENT WORK LIKE IT SHOULD FET THE DIRECTIOS FROM THE LOCATION WHERE IT IS LOCATED TO THE DISASTER HAPPEND PLACE