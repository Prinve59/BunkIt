import base64
import pickle
import requests
from django.shortcuts import render ,redirect
from .forms import LoginForm

session = requests.Session()
cookie_file = 'cookies.pkl'

def save_cookies():
    with open(cookie_file, 'wb') as f:
        pickle.dump(session.cookies, f)

def clear_cookies():
    try:
        open(cookie_file, 'wb').close()  # Clear the cookie file
    except FileNotFoundError:
        pass
    session.cookies.clear()

def load_cookies():
    try:
        with open(cookie_file, 'rb') as f:
            session.cookies.update(pickle.load(f))
    except FileNotFoundError:
        pass

def login_and_fetch_attendance(username, password):
    login_url = "https://mserp.kiet.edu/"
    attendance_url = "https://mserp.kiet.edu/StudeHome.aspx/ShowAttendance"
    logout_url = "https://mserp.kiet.edu/default.aspx"

    # Encode username and password to base64
    encoded_username = base64.b64encode(username.encode('utf-8')).decode('utf-8')
    encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')

    login_payload = {
        'Script_water_HiddenField': ';;AjaxControlToolkit, Version=3.0.20229.20843, Culture=neutral, PublicKeyToken=28f01b0e84b6d53e:en-US:3b7d1b28-161f-426a-ab77-b345f2c428f5:e2e86ef9:1df13a87:8ccd9c1b',
        '__EVENTTARGET': 'btnLogin',
        '__EVENTARGUMENT': '',
        '__VIEWSTATE': 'ACKqIxa4EejFgfnYDemEW2p5kDIRBfKn+gUSX5m1xoT7RATyPcCMy81r7bMmW7+TZwoC8O/fWpvIcRM8JAoQ39G7q1VSwkfW2sjP5sOzI8w7iEHs2rUvMWdDig/T+mvq8QyUUOh7Oh/6LSn81HPdAcuI5qrTv95dWkgWJdFmUkIm6bwv',
        '__VIEWSTATEGENERATOR': 'CA0B0334',
        '__VIEWSTATEENCRYPTED': '',
        'txt_username': username,
        'txt_password': password,
        'hdncaptcha': '2212',
        'txtcaptcha': '2212', 
        'hdnusername': encoded_username,
        'hdnpassword': encoded_password,
        'hdfVisitorId': '4523f067d4298d62b824f1c3832acded',
    }

    # Login request
    login_response = session.post(login_url, data=login_payload)

    if login_response.status_code == 200:
        save_cookies()
        # Fetch Attendance
        headers = {
            'Content-Type': 'application/json',
        }
        response = session.post(attendance_url, json={}, headers=headers)
        if response.status_code == 200:
            data = response.json()
            attendance_list = data['d']['AttendList']
            if not attendance_list:  # If attendance list is None or empty
                return None, 0, 0, 0,True # Return a flag indicating no data
            processed_data = [
                {
                    'Subject': item['CourseName'],
                    'Attendance': item['Attendance'],
                    'Percentage': item['AttendancePerc']
                } for item in attendance_list
            ]
            # Calculate totals
            total_present = sum(int(a['Attendance'].split('/')[0]) for a in processed_data)
            total_classes = sum(int(a['Attendance'].split('/')[1]) for a in processed_data)
            total_absent = total_classes - total_present
            return processed_data, total_present, total_absent, total_classes, False  # No error flag
        else:
            return None, 0, 0, 0, True  
    return None, 0, 0, 0, True 

def logout(request):
    logout_url = "https://mserp.kiet.edu/Logout.aspx"
    try:
        session.get(logout_url)  # Call the logout endpoint
    except requests.RequestException:
        pass
    clear_cookies()  # Clear the session and cookies
    request.session.flush()  # Clear Django session data
    return redirect('home')

def calculate_classes_to_attend(goal_attendance, total_present, total_classes):
    # Initial guess for additional classes needed
    additional_classes = 0
    
    # Iteratively calculate additional classes required to reach the goal percentage
    while True:
        required_present = (goal_attendance * (total_classes + additional_classes)) / 100
        if required_present <= total_present + additional_classes:
            break
        additional_classes += 1
    return additional_classes

def calculate_classes_to_bunk(goal_attendance, total_present, total_classes):
    # Calculate the maximum number of classes that can be bunked
    max_classes_to_bunk = (total_present / (goal_attendance / 100)) - total_classes
    return max(0, round(max_classes_to_bunk))
def home(request):
    # Initialize variables
    form = LoginForm()  # Form initialization
    logged_in = request.session.get('logged_in', False)
    attendance_data = request.session.get('attendance_data', None)
    total_present = request.session.get('total_present', 0)
    total_absent = request.session.get('total_absent', 0)
    total_classes = request.session.get('total_classes', 0)
    goal_attendance = request.session.get('goal_attendance', None)
    classes_to_attend = request.session.get('classes_to_attend', None)
    classes_to_bunk = request.session.get('classes_to_bunk', None)
    error_message = None

    if request.method == 'POST':
        # Handling login form submission
        if 'username' in request.POST and 'password' in request.POST:
            form = LoginForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                attendance_data, total_present, total_absent, total_classes, no_data = login_and_fetch_attendance(username, password)
                if no_data:
                    error_message = "Invaild Credentials"
                    return render(request, 'home.html', {
                        'form': form,
                        'error_message': error_message,
                        'logged_in': logged_in
                    })
                # Successfully logged in, store necessary data
                request.session['logged_in'] = True
                request.session['attendance_data'] = attendance_data
                request.session['total_present'] = total_present
                request.session['total_absent'] = total_absent
                request.session['total_classes'] = total_classes
                return redirect('home')  # Reload page to show updated data
        
        # Handling goal attendance form submission
        elif 'goal_attendance' in request.POST:
            goal_attendance = int(request.POST.get('goal_attendance'))
            request.session['goal_attendance'] = goal_attendance

            if total_classes > 0:  # Ensure total_classes is greater than 0 to avoid division by zero
                current_percentage = round((total_present / total_classes) * 100, 2)
                if goal_attendance > current_percentage:

                    additional_classes_needed = calculate_classes_to_attend(goal_attendance, total_present,total_classes)


                    request.session['classes_to_attend'] = additional_classes_needed
                elif goal_attendance < current_percentage:
                    # Calculate classes to bunk
                    bunkable_classes = calculate_classes_to_bunk(goal_attendance, total_present, total_classes)
                    request.session['classes_to_bunk'] = max(0, round(bunkable_classes))

            return redirect('home')  # Reload page to show goal calculations

    # Render the page (after login or goal update)
    return render(request, 'home.html', {
        'form': form,
        'attendance_data': attendance_data,
        'total_present': total_present,
        'total_absent': total_absent,
        'total_classes': total_classes,
        'attendance_per': round((total_present / total_classes) * 100, 2) if total_classes > 0 else 0,
        'goal_attendance': goal_attendance,
        'classes_to_attend': classes_to_attend,
        'classes_to_bunk': classes_to_bunk,
        'error_message': error_message,
        'logged_in': logged_in,
    })
