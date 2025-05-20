import base64
import pickle
import requests
from django.shortcuts import render ,redirect
from .forms import LoginForm
from .models import Contact

session = requests.Session()
# cookie_file = 'cookies.pkl'

# def save_cookies():
#     with open(cookie_file, 'wb') as f:
#         pickle.dump(session.cookies, f)

# def clear_cookies():
#     try:
#         open(cookie_file, 'wb').close()  # Clear the cookie file
#     except FileNotFoundError:
#         pass
#     session.cookies.clear()

# def load_cookies():
#     try:
#         with open(cookie_file, 'rb') as f:
#             session.cookies.update(pickle.load(f))
#     except FileNotFoundError:
#         pass

import base64
import requests

def login_and_fetch_attendance(username, password):
    session = requests.Session()

    # Step 1: Login
    login_url = "https://tech.kiet.edu/api/hrms/student_login/"
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers_login = {
        "Authorization": f"Basic {encoded_credentials}",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://tech.kiet.edu",
        "Referer": "https://tech.kiet.edu/StudentPortal/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    login_response = session.post(login_url, headers=headers_login)

    # Check login success
    if login_response.status_code != 200:
        return None, 0, 0, 0, True  # Login failed

    # Step 2: Get Attendance
    attendance_url = "https://tech.kiet.edu/api/hrms/StudentPortal/getComponents/?request_type=mobikiet_att_new_dev"
    headers_attendance = {
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://tech.kiet.edu/StudentPortal/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    attendance_response = session.get(attendance_url, headers=headers_attendance)

    if attendance_response.status_code != 200:
        return None, 0, 0, 0, True  # Attendance fetch failed

    data = attendance_response.json()

    # Extract attendance summary
    total_present = data.get("total_present")
    total_classes = data.get("total_total")
    total_absent = total_classes - total_present if total_present is not None and total_classes is not None else 0

    # Extract detailed attendance list if exists
    attendance_list = data.get("attendance_type") or []

    processed_data = []
    for att in attendance_list:
        processed_data.append({
            "Subject": att.get("type", "Unknown"),
            "Attendance": att.get("P/T", "0/0"),
            "Percentage": att.get("percentage", "0"),
        })

    return processed_data, total_present or 0, total_absent, total_classes or 0, False



def logout(request):
    logout_url = "https://tech.kiet.edu/api/hrms/logout/"
    try:
        session.get(logout_url) 
    except requests.RequestException:
        pass
    # clear_cookies()  # Clear the session and cookies
    request.session.flush()  # Clear Django session data
    return redirect('home')

def calculate_classes_to_attend(goal_attendance, total_present, total_classes):
    additional_classes = 0
    while True:
        required_present = (goal_attendance * (total_classes + additional_classes)) / 100
        if required_present <= total_present + additional_classes:
            break
        additional_classes += 1
    
    return additional_classes
def calculate_classes_to_bunk(goal_attendance, total_present, total_classes):
    max_classes_to_bunk = (total_present / (goal_attendance / 100)) - total_classes
    return max(0, round(max_classes_to_bunk))

# def user_data(username,password):
#     try:
#         # Check if the user already exists in the Contact model
#         # contact = Contact.objects.get(lib_id=username)
#         contact.name=password
#         contact.frequency =int(contact.frequency)+ 1  # Increment the frequency
#         # contact.save()  # Save the updated instance
#     except Contact.DoesNotExist:
#         # If the user does not exist, create a new entry
#         contact = Contact(lib_id=username,name=password)
#         # contact.save()

def home(request):
    # Initialize variables
    form = LoginForm() 
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
                username1=username.replace("("," ").replace(")"," ")
                # user_data(username1,password)
                # Successfully logged in, store necessary data
                request.session['logged_in'] = True
                request.session['attendance_data'] = attendance_data
                request.session['total_present'] = total_present
                request.session['total_absent'] = total_absent
                request.session['total_classes'] = total_classes
                return redirect('home')  # Reload page to show updated data
        
        # Handling goal attendance form submission
        elif 'goal_attendance' in request.POST:
            goal_attendance = request.POST.get('goal_attendance')
            if goal_attendance=="":
                error_message = "Pls enter Some Goal :)"
                return render(request, 'home.html', {
                        'error_message': error_message,
                        'logged_in': logged_in
                    })
            elif goal_attendance=="100":
                error_message="100% Krega attendance? Toda time khud pr bhi dede!"
                return render(request, 'home.html', {
                        'error_message': error_message,
                        'logged_in': logged_in
                    })
            elif goal_attendance == "0":
                error_message = "Bhai Chod de degree!"
                return render(request, 'home.html', {
                    'error_message': error_message,
                    'logged_in': logged_in
                })
            goal_attendance=int(goal_attendance)
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
        elif "class_to_leave" in request.POST:
            extra_class=request.POST.get("class_to_leave")
            if extra_class:
                extra_class = int(extra_class)
                request.session['extra_class'] = extra_class
                attendance_drop=total_present / (total_classes + extra_class)*100
                attendance_boost=(total_present + extra_class) / (total_classes + extra_class)*100
                request.session['attendance_drop'] = attendance_drop
                request.session['attendance_boost'] = attendance_boost
            return redirect('home')
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
         'attendance_drop': request.session.get('attendance_drop'),  # Use .get()
    'attendance_boost': request.session.get('attendance_boost'),
        'extra_class': request.session.get('extra_class'),
    })
