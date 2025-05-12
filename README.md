# Ergo

A PyQt6 desktop application for real-time posture monitoring and correction using webcam and MediaPipe.

## Features

- **Real-time Posture Monitoring:** Uses your webcam and MediaPipe Pose to analyze posture locally.
- **Calibration:** Set your personal "good posture" baseline at the start of each session.
- **Deviation Alerts:** Receive visual and/or audio notifications when your posture deviates (head forward, shoulders uneven).
- **Configurable Settings:**
    - Sensitivity (Low, Medium, High)
    - Notification Mode (Audio, Visual, Both)
    - Custom Alert Message
    - Webcam Selection
    - Show/Hide Landmarks on Feed
- **Session Tracking:** View a graph of posture reminders over time.
- **System Tray Integration:** Runs in the background with controls accessible from the system tray.
- **Authentication:** Secure login via Supabase (requires an active subscription, see below).
- **Auto-Update Check:** Notifies if a newer version is available.

## Setup

1.  **Prerequisites:**
    *   Python 3.10+
    *   `pip` (Python package installer)

2.  **Install Dependencies:**
    ```bash
    # Create and activate a virtual environment (recommended)
    python3 -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    # .venv\Scripts\activate  # On Windows

    # Install packages
    pip install -r requirements.txt
    ```

3.  **MediaPipe Model:**
    *   The required model (`PostureApp/models/pose_landmarker_heavy.task`) is included in the repository.
    *   If missing, download it:
        ```bash
        mkdir -p PostureApp/models
        wget -O PostureApp/models/pose_landmarker_heavy.task \
          https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task
        ```

4.  **Environment Variables:**
    *   Create a file named `.env` in the project's root directory (`PostureApp/`).
    *   Add your Supabase credentials:
        ```env
        SUPABASE_URL=your-supabase-url
        SUPABASE_ANON_KEY=your-supabase-anon-key
        ```
    *   *Note:* The `.env` variables in `main.py` previously used `NEXT_PUBLIC_` prefixes. Ensure your `.env` file uses `SUPABASE_URL` and `SUPABASE_ANON_KEY` directly, as expected by the `supabase-py` library now used in `auth_service.py`.

## Usage

1.  **Run the application:**
    ```bash
    # Ensure your virtual environment is active
    python PostureApp/main.py
    ```

2.  **Login:**
    *   Enter the email and password associated with your Supabase account.
    *   If you don't have an account, click "Create Account".
    *   A valid, active subscription is required to proceed past login (managed via Supabase).

3.  **Dashboard:**
    *   **Start Session:** Click to begin the calibration process.
        *   Follow the on-screen instructions and example images.
        *   Sit correctly and click "Capture Good Posture".
        *   Monitoring begins after successful calibration.
    *   **Stop Session:** Click to end monitoring and save session reminder data.
    *   **Settings:** Access application settings (sensitivity, notifications, etc.).
    *   **Logout:** Sign out of the application.
    *   **Graph:** Shows historical posture reminder counts per session.

4.  **Settings:**
    *   Adjust sensitivity, notification type, custom message, webcam, and landmark visibility.
    *   Settings are saved automatically.
    *   Manage Subscription button links to the online portal.

5.  **System Tray:**
    *   The app runs in the system tray even if the main window is closed.
    *   Right-click the tray icon for options: Open Window, Start/Stop Session, Settings, Quit.

## Subscription Requirement

- Access to the dashboard and monitoring features requires an active subscription managed in the Supabase backend.
- After signing up, an administrator needs to add a record to the `user_subscriptions` table linked to the user's Supabase Auth ID (`user_id`), setting `status` to `active` and providing a valid `expires_at` date.

## Structure

- `main.py`: Main application logic, UI (MainWindow, LoginView, DashboardView, SettingsDialog, etc.).
- `auth_service.py`: Handles Supabase authentication.
- `data_manager.py`: Manages local SQLite database for session data.
- `styles.qss`: PyQt stylesheet for application appearance.
- `resources/`: Contains icons and images.
- `models/`: Contains the MediaPipe pose landmarker model.
- `requirements.txt`: Python dependencies.
- `.env`: Environment variables (Supabase URL/Key - **DO NOT COMMIT**).
- `README.md`: This file.
- `spec.md`: Application specification details.
- `todo.md`: Development task tracking. 