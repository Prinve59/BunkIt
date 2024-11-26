import base64
import pickle
import requests
from django.shortcuts import render
from .forms import LoginForm

session = requests.Session()
cookie_file = 'cookies.pkl'

def save_cookies():
    with open(cookie_file, 'wb') as f:
        pickle.dump(session.cookies, f)

def load_cookies():
    try:
        with open(cookie_file, 'rb') as f:
            session.cookies.update(pickle.load(f))
    except FileNotFoundError:
        pass


def login_and_fetch_attendance(username, password):
    login_url = "https://mserp.kiet.edu/"
    attendance_url = "https://mserp.kiet.edu/StudeHome.aspx/ShowAttendance"

    # Encode username and password to base64
    encoded_username = base64.b64encode(username.encode('utf-8')).decode('utf-8')
    encoded_password = base64.b64encode(password.encode('utf-8')).decode('utf-8')

    # Prepare the login payload
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
            return processed_data, total_present, total_classes - total_present,total_classes
        else:
            return None, 0, 0
    return None, 0, 0


def home(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            attendance_data, total_present, total_absent ,total_classes= login_and_fetch_attendance(username, password)
            return render(request, 'home.html', {
                'form': form,
                'attendance_data': attendance_data,
                'total_present': total_present,
                'total_absent': total_absent,
                'total_classes': total_classes,
            })
    else:
        form = LoginForm()
    return render(request, 'home.html', {'form': form})

