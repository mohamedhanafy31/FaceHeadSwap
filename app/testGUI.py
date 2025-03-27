from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtCore import QUrl
import sys
import subprocess
import time
import os
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

class WebApp(QMainWindow):
    def __init__(self, email=None):
        super().__init__()
        self.setWindowTitle("Face & Head Swap GUI")
        self.setGeometry(100, 100, 1200, 900)

        # Default email (replace with actual logic to get email if needed)
        self.email = email or "mohamedhanafy3172003@gmail.com"  # Updated to match your example

        # Initialize Firebase (adjust the path to your service account key)
        if not firebase_admin._apps:
            cred = credentials.Certificate("app/remmabooth-ai-firebase-adminsdk-fbsvc-b8bae9300c.json")  # Update this path
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

        self.browser = QWebEngineView()
        self.browser.page().featurePermissionRequested.connect(self.handle_permission)
        self.browser.loadFinished.connect(self.on_load_finished)

        # Determine the initial URL based on last login time
        url = self.get_initial_url()
        print(f"Initial URL set to: {url}")
        self.browser.setUrl(QUrl(url))
        self.setCentralWidget(self.browser)

        self.start_server()

    def get_login_duration(self):
        """Fetch login_duration (in months) from Firestore for the user."""
        try:
            user_ref = self.db.collection("users").document(self.email)
            user_doc = user_ref.get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                login_duration_months = user_data.get("login_duration", 0)  # Default to 0 if not set
                # Convert months to seconds (30 days/month)
                login_duration_seconds = login_duration_months * 30 * 24 * 60 * 60
                print(f"Fetched login_duration: {login_duration_months} months ({login_duration_seconds} seconds)")
                return login_duration_seconds
            else:
                print(f"No user found for email: {self.email}")
                return 0  # Default to 0 seconds if user not found
        except Exception as e:
            print(f"Error fetching login_duration from Firestore: {e}")
            return 0  # Default to 0 seconds on error

    def get_initial_url(self):
        """Determine the initial URL based on the last login timestamp from the JSON file."""
        LOGIN_FILES_DIR = "login_logs"
        filename = f"login.json"
        file_path = os.path.join(LOGIN_FILES_DIR, filename)

        # Fetch login duration from Firestore
        login_duration_seconds = self.get_login_duration()

        # If the file or directory doesn't exist, go to login page
        if not os.path.exists(file_path):
            print(f"No login file found at {file_path}")
            return f"http://localhost:8000/static/login.html?t={int(time.time())}"

        try:
            with open(file_path, 'r') as f:
                login_data = json.load(f)

            # Validate that login_data is a list and not empty
            if not login_data or not isinstance(login_data, list):
                print("Login data is empty or not a list")
                return f"http://localhost:8000/static/login.html?t={int(time.time())}"

            # Get the most recent login entry based on loginTimestamp
            latest_login = max(login_data, key=lambda x: x.get("loginTimestamp", ""))
            last_login_str = latest_login.get("loginTimestamp")
            if not last_login_str:
                print("No valid loginTimestamp found in latest login entry")
                return f"http://localhost:8000/static/login.html?t={int(time.time())}"

            # Parse the last login timestamp
            last_login = datetime.fromisoformat(last_login_str)
            current_time = datetime.utcnow()
            time_diff = (current_time - last_login).total_seconds()

            print(f"Last login: {last_login}, Current time: {current_time}, Diff: {time_diff}s, Threshold: {login_duration_seconds}s")

            # Check if the time difference exceeds the login duration from Firebase
            if time_diff > login_duration_seconds:
                return f"http://localhost:8000/static/login.html?t={int(time.time())}"
            else:
                return "http://localhost:8000/static/index.html"
        except (json.JSONDecodeError, FileNotFoundError, ValueError) as e:
            print(f"Error reading login file: {e}")
            return f"http://localhost:8000/static/login.html?t={int(time.time())}"

    def start_server(self):
        """Start the FastAPI server as a subprocess."""
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, "-m", "app.main"],
                cwd="app",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(2)  # Give the server a moment to start
            print("FastAPI server started successfully")
        except Exception as e:
            print(f"Failed to start server: {e}")

    def handle_permission(self, securityOrigin, feature):
        """Handle feature permission requests (e.g., camera access)."""
        if feature == QWebEnginePage.MediaVideoCapture:
            self.browser.page().setFeaturePermission(
                securityOrigin,
                feature,
                QWebEnginePage.PermissionGrantedByUser
            )

    def on_load_finished(self, ok):
        """Handle page load completion."""
        if ok:
            print("Page loaded successfully")
        else:
            print("Failed to load page")

    def closeEvent(self, event):
        """Clean up server process when closing the window."""
        if hasattr(self, 'server_process'):
            print("Terminating server process...")
            self.server_process.terminate()
            self.server_process.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebApp(email="mohamedhanafy3172003@gmail.com")  # Matches your example
    window.show()
    sys.exit(app.exec_())