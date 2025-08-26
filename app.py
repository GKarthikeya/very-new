from flask import Flask, render_template_string
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from tabulate import tabulate
import time
import re
import os

app = Flask(__name__)

# Login details
COLLEGE_LOGIN_URL = "https://samvidha.iare.ac.in/"
ATTENDANCE_URL = "https://samvidha.iare.ac.in/home?action=course_content"
USERNAME = "23951a0475"   # ⚠ Replace with dynamic input later
PASSWORD = "Karthikeya.0"

# HTML template for rendering
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Attendance Report</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f9f9f9; padding: 20px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; background: white; }
        th, td { padding: 10px; border: 1px solid #ccc; text-align: center; }
        th { background-color: #4CAF50; color: white; }
        h2 { color: #333; }
        .summary { font-weight: bold; font-size: 16px; }
    </style>
</head>
<body>
    <h2>📊 Attendance Report</h2>
    {{ table_html | safe }}
    <div class="summary">
        <p>✅ Overall Attendance: Present = {{ overall.present }}, Absent = {{ overall.absent }}, Percentage = {{ overall.percentage }}%</p>
    </div>
</body>
</html>
"""

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # run without UI
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver_path = ChromeDriverManager().install()

    # Fix case where webdriver-manager returns THIRD_PARTY_NOTICES.chromedriver
    if driver_path.endswith(".chromedriver"):
        driver_path = os.path.join(os.path.dirname(driver_path), "chromedriver.exe")

    return webdriver.Chrome(service=Service(driver_path), options=chrome_options)

def calculate_attendance_percentage(rows):
    result = {
        "subjects": {},
        "overall": {"present": 0, "absent": 0, "percentage": 0.0, "success": False, "message": ""}
    }

    current_course = None
    total_present, total_absent = 0, 0

    for row in rows:
        text = row.text.strip().upper()
        if not text or text.startswith("S.NO") or "TOPICS COVERED" in text:
            continue

        # Detect course line
        course_match = re.match(r"^(A[A-Z]+\d+)\s*[-:\s]+\s*(.+)$", text)
        if course_match:
            current_course = course_match.group(1)
            course_name = course_match.group(2).strip()
            result["subjects"][current_course] = {
                "name": course_name,
                "present": 0,
                "absent": 0,
                "percentage": 0.0
            }
            continue

        if current_course:
            present_count = text.count("PRESENT")
            absent_count = text.count("ABSENT")
            result["subjects"][current_course]["present"] += present_count
            result["subjects"][current_course]["absent"] += absent_count
            total_present += present_count
            total_absent += absent_count

    # calculate subject-wise % 
    for sub in result["subjects"].values():
        total = sub["present"] + sub["absent"]
        if total > 0:
            sub["percentage"] = round((sub["present"] / total) * 100, 2)

    # calculate overall %
    overall_total = total_present + total_absent
    if overall_total > 0:
        overall_percentage = round((total_present / overall_total) * 100, 2)
        result["overall"] = {
            "present": total_present,
            "absent": total_absent,
            "percentage": overall_percentage,
            "success": True,
            "message": f"Overall Attendance: Present={total_present}, Absent={total_absent}, Percentage={overall_percentage}%"
        }

    return result

def get_attendance_data():
    driver = create_driver()
    try:
        driver.get(COLLEGE_LOGIN_URL)
        time.sleep(2)

        driver.find_element(By.ID, "txt_uname").send_keys(USERNAME)
        driver.find_element(By.ID, "txt_pwd").send_keys(PASSWORD)
        driver.find_element(By.ID, "but_submit").click()
        time.sleep(3)

        driver.get(ATTENDANCE_URL)
        time.sleep(3)

        rows = driver.find_elements(By.TAG_NAME, "tr")
        return calculate_attendance_percentage(rows)
    finally:
        driver.quit()

@app.route("/")
def show_attendance():
    data = get_attendance_data()
    subjects = data["subjects"]

    table_data = []
    for i, (code, sub) in enumerate(subjects.items(), start=1):
        table_data.append([i, code, sub["name"], sub["present"], sub["absent"], f"{sub['percentage']}%"])

    table_html = tabulate(
        table_data,
        headers=["S.No", "Course Code", "Course Name", "Present", "Absent", "Percentage"],
        tablefmt="html"
    )

    return render_template_string(HTML_TEMPLATE, table_html=table_html, overall=data["overall"])

if __name__ == "__main__":
    app.run(debug=True)
