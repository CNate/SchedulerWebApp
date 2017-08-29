from flask import *
import flask_login
from flask_cors import CORS
import sqlite3
from flask_security import login_required

db = 'scheduler.sqlite'

conn = sqlite3.connect(db)

login_manager = flask_login.LoginManager()

app = Flask(__name__)
app.secret_key = 'aabbccdd'
CORS(app)
login_manager.init_app(app)

cur = conn.execute('select email, password, access_level, f_name, emp_id from employee')

users = [dict(email = row[0], pw = row[1], acc_lvl = row[2], name=row[3], id=row[4]) for row in cur.fetchall()]


#User class the inherits from flask_login's default UserMixin class
class User(flask_login.UserMixin):
    pass

#Loads active users after they login and stores their name, employee id, and email
@login_manager.user_loader
def user_loader(email):
    for acct_dict in users:
        if email in acct_dict['email']:
            user = User()
            user.name = acct_dict['name']
            user.empid = acct_dict['id']
            user.id = email
            return user    
    return

#Sets all the appropriate values in the User class. Important for authenticating users.
@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    if email not in users:
        return

    user = User()
    user.name = users['name']
    user.id = email

    user.is_authenticated = request.form['pw'] == users[email]['pw']
    
    return user

#Function for the login screen. For the GET method, it render's the page. 
#Makes sure anyone attempting to login matches the credentials stored in the database.
#Also redirects the user depending on their access level. 
# ***0 is for employees and redirects to /home_page 
# ***1 is for manager/admins and redirects to /make_schedule
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("loginPage.html")

    email = request.form['email']
    for acct_dict in users:
        if request.form['pw'] == acct_dict['pw'] and request.form['email'] == acct_dict['email'] and acct_dict['acc_lvl'] == 0:
            user = User()
            user.name = acct_dict['name']
            user.id = email
            flask_login.login_user(user)
            return redirect(url_for('home_page'))

        elif request.form['pw'] == acct_dict['pw'] and request.form['email'] == acct_dict['email'] and acct_dict['acc_lvl'] == 1:
            user = User()
            user.name = acct_dict['name']
            user.id = email
            flask_login.login_user(user)
            return redirect(url_for('make_schedule'))  

    return redirect(url_for('login'))

#Route that navigates from root to the login screen
@app.route('/')
def root():
    return redirect(url_for('login'))

#Logs the user out of the session and redirects them to the login page
@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect(url_for('login'))

#Route for an employee, taking them to the page to make their availability
@app.route('/home_page')
@login_required
def home_page():
    return render_template("availability.html")

#Route to the manager page that allows them to make the schedule
@app.route('/make_schedule')
@login_required
def make_schedule():
    return render_template("makeSchedule.html")

#Route to the about page
@app.route('/about')
def about():
    if flask_login.current_user.is_authenticated == True:
        return render_template("about.html")
    else:
        return render_template("aboutAnon.html")

#Route to the schedule template
@app.route('/schedule')
@login_required
def schedule():
    return render_template("schedule.html")

#The function that redirects any user who is attempting to access a page that 
#has the login_required decorator but is not autheticated back to the login page.
@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for('login'))

#This function posts the schedule to the database.
@app.route('/postschedule', methods=['POST'])
def api_postsched():
    conn = sqlite3.connect(db)
    conn.execute("update schedule set Sunday='none', Monday='none', Tuesday='none', Wednesday='none', Thursday='none', Friday='none', Saturday='none'")
    content = request.form
    con = dict(content)
    for key in con:
        if len(con[key]) == 1:
            time = checkTime(con[key][0])
            day = checkDay(str(con[key][0]))
            cur = conn.execute("select " + day + " from schedule where emp_id ='" + key + "'")
            current = cur.fetchone()
            if current[0] == 'pm' or current[0] == 'am':
                conn.execute("update schedule set " + day + " = 'both' where emp_id ='" + key + "'")
                conn.commit()
            else:
                conn.execute("update schedule set " + day + " = '" + time + "' where emp_id ='" + key + "'")
                conn.commit()
        else:
            for item in con[key]:
                time = checkTime(item)
                day = checkDay(item)
                cur = conn.execute("select " + day + " from schedule where emp_id ='" + key + "'")
                current = cur.fetchone()
                if current[0] == 'pm' or current[0] == 'am':
                    conn.execute("update schedule set " + day + " = 'both' where emp_id ='" + key + "'")
                    conn.commit()
                else:
                    conn.execute("update schedule set " + day + " = '" + time + "' where emp_id ='" + key + "'")
                    conn.commit()
    conn.commit()
    conn.close()
    return render_template("schedule.html")


#Get day of week.
def checkDay(data):
    day = ''
    if data == 'sun' or data == 'sn':
        day = 'Sunday'
    if data == 'mon' or data == 'mn':
        day = 'Monday'
    if data == 'tues' or data == 'ts':
        day = 'Tuesday'
    if data == 'wed' or data == 'wd':
        day = 'Wednesday'
    if data == 'thur' or data == 'th':
        day = 'Thursday'
    if data == 'fri' or data == 'fr':
        day = 'Friday'
    if data == 'sat' or data == 'st':
        day = 'Saturday'
    return day

#Get time of day.
def checkTime(data):
    time = ''
    if data == 'sun' or data == 'mon' or data == 'tues' or data == 'wed' or data == 'thur' or data == 'fri' or data == 'sat':
        time = 'am'
    if data == 'sn' or data == 'mn' or data == 'ts' or data == 'wd' or data == 'th' or data == 'fr' or data == 'st':
        time = 'pm'
    return time

#Post availability to database.
@app.route('/post/<sun>/<mon>/<tue>/<wed>/<thu>/<fri>/<sat>', methods=['POST'])
def api_post2(sun, mon, tue, wed, thu, fri, sat):
    conn = sqlite3.connect(db)
    user = flask_login.current_user.empid
    conn.execute("update employee_availability_dow set Sunday='" + sun + "', Monday='" + mon + "', Tuesday='" + tue + "', Wednesday='" + wed + "', Thursday='" + thu + "', Friday='" + fri + "', Saturday='" + sat + "' where emp_id = '" + str(user) + "'")
    conn.commit()
    conn.close()
    return 'OK'

#Get employee availability for specified day and time.
@app.route('/get/<day>/<tod>', methods=['GET'])
def api_get_emp_by_day(day, tod):
    conn = sqlite3.connect(db)
    cur = conn.execute("select f_name,l_name,employee.emp_id from employee inner join employee_availability_dow on employee.emp_id=employee_availability_dow.emp_id where employee_availability_dow." + day + " = '" + tod + "' or employee_availability_dow." + day + " = 'both'")
    resp = cur.fetchall()
    return jsonify({'name': resp})

#Get schedule from database.
@app.route('/getSched/<day>/<tod>', methods=['GET'])
def api_get_sched(day, tod):
    conn = sqlite3.connect(db)
    cur = conn.execute("select f_name,l_name from employee inner join schedule on employee.emp_id=schedule.emp_id where schedule." + day + " = '" + tod + "' or schedule." + day + " = 'both'")
    resp = cur.fetchall()
    return jsonify({'name': resp})

#Check if current logged in user is admin or not.
@app.route('/checkAdmin', methods=['GET'])
def checkAdmin():
    conn = sqlite3.connect(db)
    user = flask_login.current_user.empid
    cur = conn.execute("select access_level from employee where emp_Id = '" +str(user)+ "'")
    resp = cur.fetchall()
    return jsonify({'admin': resp})

if __name__ == '__main__':
    app.run()