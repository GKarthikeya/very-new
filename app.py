from flask import Flask, render_template, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time, re

app = Flask(__name__)

COLLEGE_LOGIN_URL = "https://samvidha.iare.ac.in/"
ATTENDANCE_URL = "https://samvidha.iare.ac.in/home?action=course_content"

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver_path = ChromeDriverManager().install()
    return webdriver.Chrome(service=Service(driver_path), options=chrome_options)

def calculate_attendance_percentage(rows):
    result = {"subjects": {}, "overall": {"present": 0, "absent": 0, "percentage": 0.0, "success": False}}
    current_course = None
    total_present, total_absent = 0, 0

    for row in rows:
        text = row.text.strip().upper()
        if not text or text.startswith("S.NO") or "TOPICS COVERED" in text:
            continue

        course_match = re.match(r"^(A[A-Z]+\d+)\s*[-:\s]+\s*(.+)$", text)
        if course_match:
            current_course = course_match.group(1)
            result["subjects"][current_course] = {
                "name": course_match.group(2).strip(),
                "present": 0, "absent": 0, "percentage": 0.0
            }
            continue

        if current_course:
            present_count, absent_count = text.count("PRESENT"), text.count("ABSENT")
            result["subjects"][current_course]["present"] += present_count
            result["subjects"][current_course]["absent"] += absent_count
            total_present += present_count
            total_absent += absent_count

    for sub in result["subjects"].values():
        total = sub["present"] + sub["absent"]
        if total > 0:
            sub["percentage"] = round((sub["present"] / total) * 100, 2)

    overall_total = total_present + total_absent
    if overall_total > 0:
        result["overall"] = {
            "present": total_present,
            "absent": total_absent,
            "percentage": round((total_present / overall_total) * 100, 2),
            "success": True
        }

    return result

def get_attendance_data(username, password):
    driver = create_driver()
    try:
        driver.get(COLLEGE_LOGIN_URL)
        time.sleep(2)

        driver.find_element(By.ID, "txt_uname").send_keys(username)
        driver.find_element(By.ID, "txt_pwd").send_keys(password)
        driver.find_element(By.ID, "but_submit").click()
        time.sleep(3)

        driver.get(ATTENDANCE_URL)
        time.sleep(3)

        rows = driver.find_elements(By.TAG_NAME, "tr")
        return calculate_attendance_percentage(rows)

    finally:
        driver.quit()

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        data = get_attendance_data(username, password)
        return render_template("results.html", data=data)

    return render_template("login.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
