# importing libraries and flask
from flask import Flask, render_template,flash,redirect,url_for,session,request,logging
from functools import wraps
from wtforms import Form, StringField, PasswordField, IntegerField, TextAreaField, validators
from passlib.hash import sha256_crypt
from flask_mysqldb import MySQL
from flask_script import Manager
from datetime import datetime

#creating instance for flask
app = Flask(__name__)

#config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'timecards'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# initialize MySQL
mysql = MySQL(app)

# index
@app.route('/')
def index():
    return redirect(url_for('login'))

# LoginHome
@app.route('/loginHome')
def loginHome():
    return render_template('loginHome.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']
        if username =='' or password=='':
            flash("please fill all fields",'warning')
            return render_template('login.html')

        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE email = %s", [username])
        if result > 0:
            data = cur.fetchone()
            password_candidate = data['password']
            user_type = data['usertype']
            if password_candidate==password:
                #**********************************************************
                if session.get('logged_in') is None:
                    session['checked_in'] = False
                    session['checked_out'] = True
                    #session['intime'] =
                #************************************************************
                session['logged_in'] = True
                session['username'] = username
                session['user_type'] = user_type
                session['password'] = password
                if user_type ==1:
                    flash('You are now logged in', 'success')
                    return redirect(url_for('employerHome'))
                else:
                    flash('You are now logged in', 'success')
                    return redirect(url_for('employeeHome'))
            else:
                error = 'Invalid password'
                return render_template('login.html', error=error)
            cur.close()
        else:
            error='username not found'
            return render_template('login.html', error=error)
    else:
        return render_template('login.html')

# Home Page
@app.route('/home')
def home():
    return render_template('home.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('loginHome'))
    return wrap

#check if admin is logged in or not
def is_logged_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session and session['user_type'] == 1:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap



# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))



# Employee Logout *********
@app.route('/employeeLogout')
@is_logged_in
def employeeLogout():
    session['logged_in'] = False
    flash('You are now logged out employee', 'success')
    return redirect(url_for('login'))


# Employer Home
@app.route('/employerHome')
@is_logged_admin
def employerHome():
    return render_template('employerHome.html')


# Employee Home
@app.route('/employeeHome', methods = ['GET', 'POST'])
@is_logged_in
def employeeHome():
    if request.method=='GET':
        return render_template('employeeHome.html')
    else:
        tick1=0
        tick2=0
        eswar = dict(request.form)
        if eswar['action']==['id1']:
            tick1 =1
        else:
            tick2 =1
        app.logger.info('Post request recieved')
        email = session['username']
        entered_date = request.form['leave_date']
        year,month,dte = entered_date.split('-')
        app.logger.info(year)
        cur = mysql.connection.cursor()
        sameresult = cur.execute("SELECT * FROM leaves WHERE email = %s and date = %s",(email,entered_date))
        app.logger.info(sameresult)
        if sameresult>0:
            flash('You have already taken leave on requested date','warning')
            app.logger.info(sameresult)
            cur.close()
            return redirect(url_for('employeeHome'))
        result = cur.execute("SELECT * FROM workingdata WHERE email = %s and year = %s and month = %s",(email,year,month))
        if result>0:
            data = cur.fetchone()
            result2 = cur.execute("SELECT * FROM user_details WHERE email = %s",[email])
            data2 = cur.fetchone()
            eswar = dict(request.form)
            app.logger.info(eswar['action'])
            if eswar['action']==['id1']:
                app.logger.info('in if')
                app.logger.info(data2['email'])
                if data2['max_casual_leaves'] >data['casualleaves']:
                    result3 = cur.execute("SELECT * FROM leaves WHERE email = %s and date =%s",(email,entered_date))
                    if result3>0:
                        flash('casual leave is already granted on that date','warning')
                        cur.close()
                        return redirect(url_for('employeeHome'))
                    else:
                        flash('casual leave granted','success')
                        val =1 + data['casualleaves']
                        session['leave'] = True
                        session['leavedate'] = datetime.now()
                        app.logger.info(val)
                        cur.execute("insert into leaves(email, date, type) values(%s, %s, %s)", (email, entered_date, 1))
                        cur.execute("update workingdata set casualleaves = %s where email = %s and year = %s and month = %s",(val,email,year,month))
                else:
                    flash('you have reached your maximum casual leaves','warning')
                    cur.close()
                    return redirect(url_for('employeeHome'))
            else:
                app.logger.info('in else')
                if data2['max_sick_leaves'] >data['sickleaves']:
                    result3 = cur.execute("SELECT * FROM leaves WHERE email = %s and date =%s",(email,entered_date))
                    if result3>0:
                        flash('sick leave is already granted on that date','warning')
                        cur.close()
                        return redirect(url_for('employeeHome'))
                    else:
                        flash('sick leave granted','success')
                        val =1+data['sickleaves']
                        cur.execute("update workingdata set sickleaves = %s where email = %s and year = %s and month = %s",(val,email,year,month))
                        cur.execute("insert into leaves(email, date, type) values(%s, %s, %s)", (email, entered_date, 2))
                else:
                    flash('you have reached your maximum sick leaves','warning')
                    cur.close()
                    return redirect(url_for('employeeHome'))
        else:
            if tick1 ==1:
                flash('Casual leave granted','success')
            else:
                flash('Sick leave granted','success')
            cur.execute("insert into workingdata(email, year, month,sickleaves,casualleaves,workinghours) values(%s, %s, %s,%s,%s,%s)", (email,year,month,tick2,tick1,0))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('employeeHome'))

#admin req needes***********
#Check in********************

# Check if it is a leave for an user:<username> on the day he is checking in
def checkLeave(username, date):
    cur = mysql.connection.cursor()
    result = cur.execute("select * from leaves where email=%s and date=%s", (username, date))
    if result == 0:
        cur.close()
        return False
    else:
        cur.close()
        return True

@app.route('/checkin')
@is_logged_in
def checkin():
    date = datetime.now().date()
    if session['checked_in'] == True:
        flash('already checked in', 'warning')
        return redirect(url_for('employeeHome'))
    else:
        if checkLeave(session['username'], date):
            flash('Today is a leave for you', 'warning')
            return redirect(url_for('employeeHome'))
        else:
            flash('You are checked in', 'success')
            session['checked_in'] = True
            session['checked_out'] = False
            session['checkin'] = datetime.now()
            #time and date = session[checkout]
            # add time and date to session[checkin]

            #
            return redirect(url_for('employeeHome'))
#*******
#*********************************************



@app.route('/checkout')
@is_logged_in
def checkout():
    if session['checked_out'] == True:
        flash('already checked out', 'warning')
        return redirect(url_for('employeeHome'))
    else:
        flash('you are checked out', 'success')
        session['checked_in'] = False
        session['checked_out'] = True
        session['checkout'] = datetime.now()
        workingdur = session['checkout'] - session['checkin']
        email = session['username']
        year = session['checkin'].year
        month = session['checkin'].month
        #*******SQL QUERY
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM workingdata WHERE email = %s and year = %s and month = %s",(email,year,month))
        if result > 0:
            app.logger.info('check1')
            data = cur.fetchone()
            totalworking = data['workinghours']
        else:
            app.logger.info('check2')
            cur.execute("insert into workingdata(email, year, month,sickleaves,casualleaves,workinghours,overtime) values(%s, %s, %s,%s,%s,%s,%s)", (email,year,month,0,0,0,0))
            mysql.connection.commit()
            totalworking = 0

        totalworking = totalworking +(workingdur.seconds/3600.0)
        cur.execute("update workingdata set workinghours = %s where email = %s and year = %s and month = %s",(totalworking,email,year,month))
        mysql.connection.commit()
        cur.close()
        #******
        #calculate time and date based on
        return redirect(url_for('employeeHome'))
#*********************************************



@app.route('/employeeInfo/<string:username>', methods=['GET', 'POST'])
@is_logged_in
def employeeInfo(username):
    if request.method != 'POST':
        cur = mysql.connection.cursor()
        bun = datetime.now()
        year = bun.year
        month = bun.month
        app.logger.info(month)
        result = cur.execute("select * from user_details where email=%s",[username])
        row = cur.fetchone()
        pesult = cur.execute("select * from workingdata where email=%s and year = %s and month = %s",(username,year,month))
        prow = cur.fetchone()
        app.logger.info(prow)
        if result>0:
            cur.close()
            return render_template('employeeInfo.html', row=row,prow=prow)
            '''
            rows = cur.fetchall()
            for row in rows:
                if row['email']==username:
                    app.logger.info(row)
                    return render_template('employeeInfo.html', row=row)
                    cur.close()
                    break
            '''
    else:
        eswar = dict(request.form)
        app.logger.info('Post request recieved')
        name = request.form['username']
        email = session['username']
        salaryPerHour = request.form['salaryPerHour']
        jobTitle = request.form['jobTitle']
        payInOvertime = request.form['payInOvertime']
        maxCasualLeaves = request.form['maxCasualLeaves']
        maxSickLeaves = request.form['maxSickLeaves']
        cur = mysql.connection.cursor()
        app.logger.info(eswar)
        if eswar['action']==['update']:
            cur.execute("update user_details set name=%s, salary_per_hr=%s, jobTitle=%s, pay_in_overtime=%s, max_casual_leaves=%s, max_sick_leaves=%s where email=%s", (name, salaryPerHour, jobTitle, payInOvertime, maxCasualLeaves, maxSickLeaves, username))
            flash("Details updated Succesfully", 'success')
        else:
            cur.execute('delete from user_details where email=%s', [username])
            cur.execute('delete from users where email=%s', [username])
            cur.execute('delete from leaves where email=%s', [username])
            cur.execute('delete from workingdata where email=%s', [username])
            flash('employee deleted succesfully','success')
        mysql.connection.commit()
        cur.close()
        return render_template('employerHome.html')




#View Employees
@app.route('/viewEmployees', methods=['GET', 'POST'])
@is_logged_admin
def viewEmployees():
    if request.method=='GET':
        cur = mysql.connection.cursor()
        result = cur.execute("select * from user_details where email in (select email from users where usertype=2)")
        if result>0:
            rows = cur.fetchall()
            app.logger.info('Hello')
            for row in rows:
                app.logger.info(row['email'])
            return render_template('viewEmployees.html', rows = rows)
            cur.close()
        else:
            flash('No employees found', 'info')
            return render_template('employerHome.html')
    else:
        app.logger.info('IN POAST')
        #date = request.form['salary_date']
        date = datetime.now()
        app.logger.info(date)
        month_year = request.form['salary_month_year']
        year,month = month_year.split('-')
        app.logger.info(year,' ',month)
        app.logger.info(year)
        cur = mysql.connection.cursor()
        result = cur.execute("select * from (workingdata join user_details  on workingdata.email = user_details.email) where workingdata.email in (select email from workingdata where year = %s and month = %s) and workingdata.month=%s",(year,month,month))
        if result>0:
            rows = cur.fetchall()
            app.logger.info(rows)
            for row in rows:
                row.update( {"salary":0})
            for row in rows:
                row['salary'] = (row['workinghours']+row['sickleaves']*6+row['casualleaves']*6)*row['salary_per_hr']
                app.logger.info(row['salary'])
                #salary['value'] = row['workinghours']*
                #app.logger.info(dict[i]['email'] + ' and ' + dict[i]['salary'])
            return render_template('salary_generate.html', rows = rows, date = date)
            cur.close()
        else:
            flash('No employees worked in that month','info')
            return render_template('viewEmployees.html')


class NewEmployeeForm(Form):
    email = StringField('email', [validators.Length(min=6, max=50)])
    name = StringField('name', [validators.Length(min=1, max=50)])
    salaryPerHour = IntegerField('salaryPerHour', [validators.NumberRange(min=1, max=100000)])
    jobTitle = StringField('jobTitle', [validators.Length(min=1, max=50)])
    payInOvertime = IntegerField('payInOvertime', [validators.NumberRange(min=1, max=100000)])
    maxCasualLeaves = IntegerField('maxCasualLeaves', [validators.NumberRange(min=0, max=10)])
    maxSickLeaves = IntegerField('maxSickLeaves', [validators.NumberRange(min=0, max=10)])

#Add Employee
@app.route('/newEmployee', methods=['GET', 'POST'])
@is_logged_admin
def newEmployee():
    form = NewEmployeeForm(request.form)
    if request.method == 'POST' and form.validate():
        app.logger.info('got a request as POST')
        name = form.name.data
        email = form.email.data
        salaryPerHour = form.salaryPerHour.data
        jobTitle = form.jobTitle.data
        payInOvertime = form.payInOvertime.data
        maxCasualLeaves = form.maxCasualLeaves.data
        maxSickLeaves = form.maxSickLeaves.data

        cur = mysql.connection.cursor()
        result = cur.execute("select * from users where email=%s",[email])
        if result>0:
            flash('username already taken','warning')
            return render_template('newEmployee.html')
        cur.execute("insert into users(email, password, usertype) values(%s, %s, %s)", (email, '0000', 2))
        mysql.connection.commit()

        cur.execute("insert into user_details(email, name, salary_per_hr, jobtitle, pay_in_overtime, max_casual_leaves, max_sick_leaves) values(%s, %s, %s, %s, %s, %s, %s)", (email, name, salaryPerHour, jobTitle, payInOvertime, maxCasualLeaves, maxSickLeaves))
        mysql.connection.commit()

        cur.close()

        flash('New User has been added to the database', 'success')

        return redirect(url_for('employerHome'))
    else:
        if request.method =='POST':
            flash('Please fill all blanks','warning')
    return render_template('newEmployee.html', form=form)


#Employee Data
@app.route('/employeeData')
@is_logged_in
def employeeData():
    return render_template('employeeData')

# Update Password
@app.route('/updatePassword', methods=['GET', 'POST'])
@is_logged_in
def updatePassword():
    if request.method=='POST':
        app.logger.info('postdone')
        cur = mysql.connection.cursor()
        currentPassword = request.form['currentPassword']
        newPassword = request.form['newPassword']
        if newPassword=='' or currentPassword =='':
            flash('Please fill all feilds','warning')
            return render_template('updatePassword.html')
        if currentPassword == session['password']:
            cur.execute("update users set password=%s where email=%s",(newPassword,session['username']))
            flash('Your password has been updated, Use this password from next login','success')
            mysql.connection.commit()
            cur.close()
            if session['user_type'] ==1:
                return redirect(url_for('logout'))
            return redirect(url_for('employeeLogout'))
        else:
            flash('Please fill correct password','warning')
            return render_template('updatePassword.html')
    else:
        app.logger.info('getdone')
        return render_template('updatePassword.html')


if __name__ == '__main__':
    app.secret_key = 'hel#33'
    app.debug = True
    manager = Manager(app)
    manager.run()
