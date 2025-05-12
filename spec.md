## Developer Specification: Ergo - Desktop Application

**Version:** 1.0 **Date:** May 7, 2025

**Table of Contents:**

1. Introduction & Overview
2. General Architecture & Technology Stack
3. Detailed Features & User Interface (UI) Flow
    - 3.1. Application Launch & Initial Screen
    - 3.2. User Login & Authentication
    - 3.3. Post-Login Dashboard
    - 3.4. Settings
    - 3.5. Session Management
    - 3.6. Background Operation & System Tray/Menu Bar Icon
4. Core Technical Implementation Details
    - 4.1. MediaPipe Pose Integration
    - 4.2. Posture Reference & Deviation Calculation
    - 4.3. Sensitivity Adjustment
5. Data Handling & Storage (Local)
    - 5.1. Session Reminder Graph Data
    - 5.2. Webcam Data & Landmarks
    - 5.3. User Settings & Calibration Data
6. Installation & Updates
    - 6.1. Installation
    - 6.2. In-App Updates
7. Error Handling & User Guidance
    - 7.1. Webcam Access Issues
    - 7.2. Poor Landmark Detection
    - 7.3. Network & Subscription Issues
8. Informational Sections (In-App)
    - 8.1. "About" Section
    - 8.2. Privacy Considerations
9. Testing Plan
    - 9.1. Unit Tests
    - 9.2. Integration Tests
    - 9.3. UI/UX Tests
    - 9.4. Functional Tests (End-to-End)
    - 9.5. Performance Tests
    - 9.6. Cross-Platform Tests
    - 9.7. Installation and Update Tests
    - 9.8. Error Handling and Edge Case Tests
    - 9.9. User Acceptance Testing (UAT)

---

### 1. Introduction & Overview

- **Application Name:** Ergo
- **Purpose:** A desktop application designed to help users improve their posture by providing real-time feedback using their webcam and MediaPipe pose detection technology.
- **Target Audience:** Desktop computer users who wish to monitor and correct their posture during work or general computer use.
- **Core Functionality Summary:**
    - User authentication and subscription validation (Supabase).
    - User-initiated calibration of "good posture" at the start of each session.
    - Real-time webcam-based posture analysis using local MediaPipe Pose detection.
    - Detection of deviations from the calibrated posture (specifically head forwardness and shoulder unevenness).
    - Configurable audio and visual alerts upon deviation.
    - Local storage of session statistics (reminder counts).
    - Background operation with system tray/menu bar icon.
    - In-app update mechanism.

### 2. General Architecture & Technology Stack (Desktop App Focus)

- **Platform:** Desktop application supporting:
    - Windows (Target: Windows 10 and newer)
    - macOS (Target: Specify recent versions, e.g., macOS 11 Big Sur and newer)
    - Linux (via AppImage, target common distributions like Ubuntu, Fedora)
- **Primary Language:** Python
- **GUI Framework:** To be selected by the developer, ensuring cross-platform compatibility, good performance with webcam feeds, and integration with Python (e.g., PyQt, Kivy, CustomTkinter with appropriate styling).
- **Pose Detection Engine:** MediaPipe Pose. Processing must occur entirely locally on the user's machine.
- **Interaction with Backend Services (Supabase):**
    - **Authentication & Subscription Validation:** The desktop app will communicate with Supabase (via its provided APIs) for user login and to validate the status of the user's subscription.
    - **Update Manifest & Installers:** The app will check for updates by fetching a manifest file (JSON) from Supabase Storage and download new installers (also hosted on Supabase Storage) via HTTPS.

### 3. Detailed Features & User Interface (UI) Flow

#### 3.1. Application Launch & Initial Screen

- Upon launch, a professional and simple initial screen is displayed.
- Elements:
    - Application Name: Ergo
    - Application Logo
    - Brief one-sentence explanation of the application's purpose.
    - User Login Interface (email/password fields, login button, link to sign-up/forgot password on the web application).

#### 3.2. User Login & Authentication

- User enters credentials (email/password).
- On "Login" click, the application attempts to authenticate against Supabase.
    - Requires an active internet connection.
    - Supabase validates credentials and checks for an active subscription associated with the user account.
- **Successful Login:** Proceed to Post-Login Dashboard (Section 3.3).
- **Failed Login (Invalid Credentials):** Display an appropriate error message.
- **Failed Login (No Internet):** Display "Internet connection required to log in."
- **Failed Login (Subscription Expired/Inactive):** Display a clear message, e.g., "Your subscription has expired. Please visit [WebAppURL/SubscriptionPage] to renew." Prevent access to the dashboard/session features.

#### 3.3. Post-Login Dashboard

- Main application window after successful login.
- Elements:
    - **"Start Session" Button:** Initiates the calibration process and starts posture monitoring.
    - **"Settings" Button:** Opens the application settings view/dialog.
    - **User Account Information:**
        - Display basic subscription info (e.g., "Subscription: Active until YYYY-MM-DD"). (Note: Currently checked but not explicitly displayed on dashboard).
        - Link/Button: "Manage Subscription" - opens the user's subscription management page on the web application in their default browser (Located in Settings Dialog).
    - **Reminders Graph:**
        - A clean, simple graph displaying the number of posture reminders sent per session over time.
        - X-axis: Date of session.
        - Y-axis: Total count of reminders for that session.
        - Data for this graph is stored locally (see Section 5.1).

#### 3.4. Settings

- Accessible via the "Settings" button on the dashboard and from the system tray/menu bar icon. Settings should also be accessible _during_ an active monitoring session without stopping it (Settings dialog is modal, but applying settings can affect the running session).
- Settings Options:
    - **Sensitivity for Deviation Detection:**
        - User-adjustable setting (e.g., a slider or dropdown).
        - Defines the angular threshold (in degrees) for triggering an alert.
        - Example: "Low," "Medium (Default - e.g., 20 degrees)," "High." Higher sensitivity means a smaller angular change triggers alerts.
    - **Notification Mode:**
        - User can select:
            - Audio Alert Only
            - Visual Alert Only
            - Both Audio and Visual Alerts (Default)
    - **Custom Pop-up Message Text:**
        - A text input field allowing the user to customize the message displayed in the visual pop-up alert.
        - Default text: "Fix your posture!"
    - **Webcam Selection (if multiple webcams are detected):**
        - A dropdown to select the active webcam. This option should be prominent if a webcam issue is detected (see Section 7.1) or available in general settings.

#### 3.5. Session Management

##### 3.5.1. Starting a Session & Calibration

1. User clicks the **"Start Session"** button from the dashboard.
2. **Webcam Access:**
    - The application requests access to the user's webcam if not already granted.
    - Handle cases where access is denied (see Section 7.1).
    - Display the live webcam feed in a designated area of the UI.
3. **Guided Posture Setup:**
    - Display an example image illustrating good posture.
    - Display clear, concise text instructions:
        - "Sit upright."
        - "Shoulders relaxed and back."
        - "Head aligned over shoulders."
        - "Eyes looking straight ahead."
4. **"Capture Posture" Action:**
    - User positions themselves according to the guidance.
    - User clicks a **"Capture Good Posture"** button.
5. **Baseline Establishment:**
    - Upon click, the application uses the current frame from the webcam and MediaPipe Pose landmarks to calculate and store the reference angles/relationships for:
        - **Head Position:** The angular relationship of head landmarks (e.g., ears, nose) relative to shoulder landmarks (e.g., midpoint of shoulders) to establish a baseline for forward head movement.
        - **Shoulder Alignment:** The angle of the line connecting the left and right shoulder landmarks relative to the horizontal, to establish a baseline for shoulder evenness.
    - This captured baseline represents the user's "good posture" for the current session.
    - Provide feedback that calibration is complete (e.g., "Calibration successful! Monitoring started."). The UI then transitions to active monitoring.

##### 3.5.2. Active Monitoring

- The application continuously processes the webcam feed using MediaPipe Pose (locally).
- It extracts relevant landmarks (shoulders, head).
- It calculates the current head position angle and shoulder line angle.
- It compares these current angles to the calibrated baseline angles.
- Deviation is determined if the change in these angles exceeds the user-defined sensitivity threshold.
    - **Head Deviation:** Detects if the head moves significantly forward from its calibrated angular relationship with the shoulders.
    - **Shoulder Deviation:** Detects if the shoulder line angle changes significantly, indicating one shoulder dropping or hunching.

##### 3.5.3. Alerts & Notifications

- Triggered when a deviation exceeding the sensitivity threshold is detected.
- The type of alert depends on the user's selection in Settings (Section 3.4):
    - **Audio Alert:**
        - A recorded voice saying: **"Fix the posture."** (Using edge-tts for voice generation).
        - Ensure the sound is clear and at an appropriate volume (consider OS volume).
    - **Visual Alert:**
        - A non-modal pop-up message appears on the screen.
        - Message text: Default "Fix your posture!", customizable by the user.
        - Appearance: Large, clear, easily noticeable text. The position of the pop-up should be considered (e.g., corner of the screen, or near the application's tray icon if windowless).
- Alerts should not be overly spammy; consider a cooldown period after an alert before another one for the same deviation type can be triggered if the posture is not corrected.

##### 3.5.4. Ending a Session

- User can end an active monitoring session by clicking a clearly labeled **"Stop Session"** button.
- This button should be available in the main application window (if open) and via the system tray/menu bar icon.
- Upon stopping, the application ceases webcam processing and monitoring. The UI might return to the Post-Login Dashboard.

#### 3.6. Background Operation & System Tray/Menu Bar Icon

- If the main application window is closed while a session is active, the posture monitoring should continue to run in the background.
- A system tray icon (Windows, Linux) or menu bar icon (macOS) must be present when the application is running (especially when monitoring in the background).
    - The icon should visually indicate whether a session is active (if possible, e.g., subtle color change).
- **Icon Menu Options (Right-click on Windows/Linux, Click on macOS):**
    - **"Open Ergo Window":** Opens/focuses the main application dashboard.
    - **"Start Session" / "Stop Session":** Label dynamically changes based on current state. Starts calibration and monitoring, or stops the active session.
    - **"Settings":** Opens the application settings view/dialog.
    - **"Quit Ergo":** Stops any active session, closes background processes, and exits the application.

### 4. Core Technical Implementation Details

#### 4.1. MediaPipe Pose Integration

- Utilize the MediaPipe Pose Landmarker API with the Python bindings.
- Ensure the chosen model (e.g., "pose_landmarker_lite.task" or "pose_landmarker_full.task" – developer to choose based on performance/accuracy trade-off) is bundled with the application or downloaded on first run (with user consent if large).
- All MediaPipe processing must be performed locally on the user's machine. No image/video data should be streamed to external servers.
- Key landmarks to be used for calculation:
    - `LEFT_SHOULDER` (MP Landmark 11)
    - `RIGHT_SHOULDER` (MP Landmark 12)
    - `NOSE` (MP Landmark 0)
    - `LEFT_EAR` (MP Landmark 7)
    - `RIGHT_EAR` (MP Landmark 8)
    - (Consider `LEFT_HIP` (23) and `RIGHT_HIP` (24) if needed for more robust torso lean detection in future, but current spec focuses on head/shoulders).

#### 4.2. Posture Reference & Deviation Calculation

- **Calibration Baseline:**
    - **Head Forwardness Reference:** Calculate a vector or angle (e.g., from midpoint of shoulders to midpoint of ears, or ears to nose projected onto sagittal plane if possible) representing the initial head orientation relative to shoulders. Store this reference angle.
    - **Shoulder Line Reference:** Calculate the angle of the line segment between `LEFT_SHOULDER` and `RIGHT_SHOULDER` with respect to the horizontal axis. Store this reference angle.
- **Deviation Metrics:**
    - Continuously recalculate these angles during monitoring.
    - **Head Deviation:** The absolute difference between the current head forwardness angle and the reference head forwardness angle.
    - **Shoulder Line Deviation:** The absolute difference between the current shoulder line angle and the reference shoulder line angle.

#### 4.3. Sensitivity Adjustment

- The user-adjustable sensitivity setting directly maps to an angular threshold (in degrees).
- If `current_deviation_angle > sensitivity_threshold_degrees`, an alert is triggered.
- Implement a default threshold (e.g., 20 degrees).

### 5. Data Handling & Storage (Local)

#### 5.1. Session Reminder Graph Data

- **Data to Store per Session:**
    - Date of the session (YYYY-MM-DD).
    - Total count of reminders triggered during that session.
- **Storage Mechanism:** Local file storage (e.g., a simple SQLite database file or a structured JSON file). Developer to choose a lightweight, robust solution appropriate for Python desktop apps. File should be stored in the application's user-specific data directory.
- **Retention:** Data is retained until the application is uninstalled by the user.
- **Privacy:** This data is strictly local and not transmitted.

#### 5.2. Webcam Data & Landmarks

- The live webcam video stream and derived MediaPipe landmarks are processed exclusively in the application's memory on the user's local machine.
- This data is used for real-time analysis only.
- **No images, video frames, or detailed landmark coordinates are stored permanently or transmitted off the user's device by the application.**

#### 5.3. User Settings & Calibration Data

- User-configured settings (sensitivity, notification preferences, custom alert message, selected webcam) must be persisted locally.
- The "good posture" calibration data (reference angles) is specific to each session and may not need to be persisted between application restarts, but rather re-captured at the start of each new session. (If persistence of calibration across app restarts for a _day_ is desired, this needs to be specified. Current assumption: calibration is per-session-start).

### 6. Installation & Updates

#### 6.1. Installation

- **Distribution Formats:**
    - Windows: `.exe` installer (e.g., created with PyInstaller + Inno Setup).
    - macOS: `.dmg` disk image containing the `.app` bundle (e.g., created with PyInstaller or Briefcase). Application must be signed for macOS.
    - Linux: `AppImage` (e.g., created with tools compatible with Python app bundling).
- **Download Source:** Users download these installers from the companion web application after subscribing.

#### 6.2. In-App Updates

- **Mechanism:** The Python desktop application will implement a mechanism to check for updates.
- **Update Manifest:**
    - The application will periodically check a URL pointing to an update manifest file (e.g., `update-info.json`) hosted on Supabase Storage.
    - This manifest will contain information like the latest version number, download URLs for each platform-specific installer, and release notes.
- **Update Process:**
    1. **Automatic Check:** On application startup, check the manifest file for a newer version.
    2. **Notification:** If an update is available, display a small, non-intrusive notification within the application (e.g., a banner or an indicator on a "Help" or "About" menu).
    3. **Automatic Download:** The update installer (new `.exe`, `.dmg`, or `AppImage` corresponding to the user's platform) downloads automatically in the background. Progress indication is a plus.
    4. **Installation Prompt:** Once downloaded, the application prompts the user to install the update, stating that a restart will be required (e.g., "A new version of [PostureApp] has been downloaded. Restart now to install?").
    5. **Manual Restart & Apply:** Upon user confirmation, the application should attempt to quit and guide the user to run the downloaded installer. (Automating the replacement of a running Python application can be complex; the simplest approach is to have the user run the new installer, which then overwrites the previous version). The installer should handle the replacement smoothly.

### 7. Error Handling & User Guidance

#### 7.1. Webcam Access Issues

- If no webcam is detected: Display "No webcam detected. Please connect a webcam to use [PostureApp]."
- If webcam permission is denied by OS: Display "Webcam access denied. Please grant permission in your system settings to use [PostureApp]." Provide a button/link that attempts to open OS permission settings if possible, or clear instructions.
- If another app is using the webcam: Display "Webcam is currently in use by another application."
- If multiple webcams are available and one fails or is not desired: Provide an option in settings (and possibly prompted on error) to select a different webcam (see Section 3.4).

#### 7.2. Poor Landmark Detection (MediaPipe)

- If MediaPipe consistently fails to detect landmarks reliably (e.g., user too far, poor lighting, obstruction), either during calibration or active monitoring:
    - Display a non-intrusive message/overlay on the webcam feed or a status indicator.
    - Provide brief, actionable tips:
        - "Ensure your face and shoulders are clearly visible."
        - "Improve room lighting."
        - "Try moving closer to the camera."
        - "Remove any obstructions."
    - During calibration, if detection is insufficient, prevent completion of "Capture Good Posture" until a reasonable pose is detected.

#### 7.3. Network & Subscription Issues

- **No Internet Connection (at Login/Startup):**
    - For login: "Internet connection required to log in and validate subscription." Prevent login.
    - For update check: Silently fail the update check or inform "Could not check for updates. No internet connection."
- **Subscription Expired/Inactive (handled at Login - Section 3.2, or on attempted Session Start if app was already running):**
    - If user attempts to start a new session and a check reveals the subscription (cached status or fresh check if implemented) is now expired: Display "Your subscription has expired. Please renew to start a new session." Guide to web app. Prevent session start.

### 8. Informational Sections (In-App)

#### 8.1. "About" Section

- Accessible from the main UI (e.g., Help menu or Settings).
- Contents:
    - Application Name: [PostureApp]
    - Version Number (e.g., 1.0.0)
    - Brief copyright notice.
    - A brief description of the application.
    - Link to the **Privacy Policy** (opens the policy page on the web application in the default browser).
    - Link to **Help/Documentation** (opens the help page on the web application).
    - Link to **Contact Us/Support** (opens the contact page on the web application).

#### 8.2. Privacy Considerations (To be emphasized in UI and documentation)

- Clearly communicate to users that webcam processing is done **locally**.
- Reinforce that no images or personal video data are transmitted or stored by the application.
- Refer to the full Privacy Policy for details.

### 9. Testing Plan

A comprehensive testing strategy should be employed, covering the following areas:

#### 9.1. Unit Tests

- **Scope:** Individual Python functions, methods, and classes.
- **Focus:**
    - Logic for calculating angles from MediaPipe landmarks.
    - Sensitivity threshold application.
    - Settings persistence (load/save).
    - Local data storage for reminder graph (read/write operations).
    - Parsing of update manifest.
- **Tools:** Python's `unittest` module, `pytest`.

#### 9.2. Integration Tests

- **Scope:** Interactions between different components of the desktop application and with external services.
- **Focus:**
    - Correct initialization and data flow from MediaPipe Pose to the posture analysis logic.
    - Authentication flow with Supabase (mocking Supabase API responses or using a test environment).
    - Subscription status validation logic.
    - Fetching and parsing the update manifest from a mock endpoint or Supabase Storage (test environment).
    - Interaction between the GUI and the core application logic.

#### 9.3. UI/UX Tests

- **Scope:** Visual elements, user interaction, and overall user experience.
- **Focus:**
    - All buttons, sliders, dropdowns, text fields function correctly.
    - Clarity and accuracy of instructions (especially for calibration).
    - Effectiveness and non-intrusiveness of alerts (visual and audio).
    - Navigation flow between different screens/states.
    - Responsiveness of the UI, especially during active monitoring.
    - Visual consistency across platforms.

#### 9.4. Functional Tests (End-to-End)

- **Scope:** Testing complete user scenarios from start to finish.
- **Focus:**
    - User launch -> login -> dashboard interaction -> start session -> calibration -> active monitoring -> receive alerts -> adjust settings during session -> stop session -> check graph -> background mode -> tray icon interaction -> quit.
    - Handling of expired subscription scenarios.
    - Correct behavior of all settings options.

#### 9.5. Performance Tests

- **Scope:** Application's resource usage and responsiveness under load.
- **Focus:**
    - CPU and memory consumption during active posture monitoring (MediaPipe). Aim for acceptable levels that don't severely impact system performance.
    - Application startup time.
    - UI responsiveness when webcam feed and MediaPipe are active.
    - Test on systems with varying hardware specifications (especially min-spec targets).

#### 9.6. Cross-Platform Tests

- **Scope:** Ensuring consistent functionality and appearance on all supported operating systems.
- **Focus:**
    - Execute a core suite of functional and UI tests on:
        - Windows (e.g., Windows 10, Windows 11).
        - macOS (e.g., latest and one previous major version).
        - Linux (select 2-3 popular distributions for AppImage testing, e.g., Ubuntu LTS, Fedora).
    - Verify platform-specific integrations:
        - System tray icon (Windows, Linux KBE/Gnome).
        - Menu bar icon (macOS).
        - Native notifications/pop-ups if any OS-specific APIs are used for alerts.
        - Webcam access and permissions handling.

#### 9.7. Installation and Update Tests

- **Scope:** The application's installation and update processes.
- **Focus:**
    - Successful installation from `.exe` (Windows), `.dmg` (macOS), and `AppImage` (Linux) on clean systems and over previous versions.
    - Correct uninstallation (ensure no unnecessary files are left behind, except user-generated data like graph history if explicitly desired).
    - In-app update mechanism:
        - Detection of new version from manifest.
        - Successful background download of the new installer.
        - Correct prompting for restart and installation.
        - Successful application of the update.

#### 9.8. Error Handling and Edge Case Tests

- **Scope:** Application's robustness and behavior in unexpected situations.
- **Focus:**
    - No webcam connected / multiple webcams.
    - Webcam permission denied / webcam in use by another app.
    - Poor lighting / user out of frame / obstructions for MediaPipe.
    - Intermittent or no internet connection during login, subscription check, or update check.
    - Invalid or corrupted settings files or local graph data.
    - Extremely high or low sensitivity settings.
    - Rapidly starting/stopping sessions.

#### 9.9. User Acceptance Testing (UAT)

- **Scope:** Validation by representative end-users that the application is fit for purpose.
- **Focus:**
    - Ease of use and intuitiveness of the UI and calibration process.
    - Effectiveness of posture feedback.
    - Appropriateness of alert frequency and type.
    - Overall satisfaction with the application.
    - Gather feedback for future improvements.

---

This specification should provide a clear and detailed guide for the development of the [PostureApp] desktop application.