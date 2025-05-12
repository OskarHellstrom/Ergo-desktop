# [PostureApp] Desktop Application - Development Todo List

## 1. Project Setup & Core Dependencies
- [x] Initialize Python project structure.
- [x] Select and integrate a Python GUI framework (e.g., PyQt, Kivy, CustomTkinter, etc.).
    - [x] Ensure basic window creation and event handling.
- [x] Integrate MediaPipe Pose Python library.
- [x] Set up Supabase Python client library for authentication and API calls.
- [x] Choose and set up local database solution for graph data/settings (e.g., SQLite).
- [ ] Set up project for cross-platform development (consider virtual environments, build tools).

## 2. Architecture & Cross-Platform Base
- [ ] Establish basic application structure for Windows.
- [ ] Establish basic application structure for macOS.
- [ ] Establish basic application structure for Linux (AppImage).
- [x] Implement core abstractions for platform-specific features if necessary (e.g., tray icon, notifications). (PyQt handles some of this)

## 3. User Authentication & Subscription (Desktop - Supabase Integration)
- [x] Implement user login UI (email, password, login button, links to web app for sign-up/forgot password).
- [x] Implement logic to authenticate against Supabase using provided credentials.
- [x] Implement logic to fetch and validate subscription status from Supabase post-login.
- [x] Implement UI feedback for successful login.
- [x] Implement UI feedback for failed login (invalid credentials, no internet).
- [x] Implement UI feedback and access restriction for expired/inactive subscriptions (with link to web app).

## 4. Main Application UI Shell & Navigation
### 4.1. Initial Screen / Login UI
- [x] Implement application launch screen (App Name, Logo, brief explanation, Login UI).
### 4.2. Post-Login Dashboard UI
- [x] Design and implement the main dashboard layout.
- [x] Implement "Start Session" button.
- [x] Implement "Settings" button.
- [x] Implement display area for basic subscription information (status, expiry). (Handled internally, not explicitly displayed)
- [x] Implement "Manage Subscription" button/link (opens web app). (Moved to Settings)
- [x] Design and implement the reminders graph display area.
    - [x] Implement logic to render graph from local data (see Section 10).
### 4.3. Settings UI
- [x] Design and implement the Settings view/dialog.
- [x] Implement UI controls for Sensitivity adjustment (slider/dropdown).
- [x] Implement UI controls for Notification Mode selection (radio buttons/dropdown).
- [x] Implement UI control for Custom Pop-up Message text input.
- [x] Implement UI control for Webcam Selection dropdown (populated dynamically).
- [x] Ensure settings UI is accessible from Dashboard and Tray Icon.
- [x] Ensure settings can be adjusted during an active session (if specified as non-modal). (Dialog is modal, but settings apply)
### 4.4. "About" Section UI
- [x] Design and implement the "About" view/dialog.
- [x] Populate with App Name, Version Number, Copyright.
- [x] Add brief description.
- [x] Add link to Privacy Policy (opens web app URL).
- [x] Add link to Help/Documentation (opens web app URL).
- [x] Add link to Contact Us/Support (opens web app URL).

## 5. Webcam & MediaPipe Integration
- [x] Implement logic to request and manage webcam access permissions.
- [x] Implement live webcam feed display within the application (for calibration/preview).
- [x] Integrate MediaPipe Pose to process the live webcam feed locally.
- [x] Extract required landmarks (Shoulders, Head - Nose, Ears) in real-time.
- [x] Bundle MediaPipe model files or ensure they are correctly downloaded/located.

## 6. Calibration Logic & UI
- [x] Implement UI for the guided posture setup step:
    - [x] Display example image of good posture.
    - [x] Display text instructions ("Sit upright," etc.).
- [x] Implement "Capture Good Posture" button functionality.
- [x] On capture, calculate and store baseline reference angles for:
    - [x] Head position (angular relationship with shoulders).
    - [x] Shoulder alignment (angle relative to horizontal).
- [x] Implement UI feedback for successful/failed calibration.
- [x] Transition UI to active monitoring state after successful calibration.

## 7. Posture Monitoring & Deviation Logic
- [x] Implement continuous processing of MediaPipe landmarks during an active session.
- [x] Continuously calculate current head position angle.
- [x] Continuously calculate current shoulder line angle.
- [x] Compare current angles to the calibrated baseline angles.
- [x] Implement logic to determine deviation based on the sensitivity threshold (degrees).
- [x] Differentiate between head forwardness deviation and shoulder unevenness deviation.

## 8. Alerts & Notifications System
- [x] Implement alert trigger logic based on deviation detection.
- [x] Implement audio alert:
    - [x] Integrate recorded voice: "Fix the posture." (Uses edge-tts)
    - [x] Ensure audio playback functionality.
- [x] Implement visual alert:
    - [x] Non-modal pop-up message. (Custom Toast)
    - [x] Display default ("Fix your posture!") or user-customized message.
    - [x] Ensure text is large, clear, and noticeable.
    - [x] Determine and implement pop-up position. (Centered on parent/screen)
- [x] Implement logic to respect user's Notification Mode setting (audio only, visual only, both).
- [x] Implement a cooldown period for alerts to prevent spamming.
- [x] Implement a minimum duration for bad posture before alerting (e.g., 2 seconds).

## 9. Settings Functionality (Backend Logic)
- [x] Implement logic to save selected sensitivity to local settings.
- [x] Implement logic to save selected notification mode to local settings.
- [x] Implement logic to save custom pop-up message text to local settings.
- [x] Implement logic to save selected webcam to local settings.
- [x] Ensure core monitoring logic uses these saved settings.

## 10. Local Data Storage (Graph Data, User Settings)
### 10.1. Session Reminder Graph Data
- [x] Implement schema/structure for storing session data (Date, Reminder Count). (SQLite)
- [x] Implement logic to record session data (increment reminder count during session, save on session end).
- [x] Implement logic to retrieve session data for graph display.
- [x] Ensure data is stored in the application's user-specific data directory. (Uses QSettings path, relative to executable)
- [x] Ensure data persists until application uninstallation.
### 10.2. User Settings Persistence
- [x] Implement logic to save all user-configurable settings (from Section 9) locally. (Uses QSettings)
- [x] Implement logic to load user settings on application startup.
### 10.3. Calibration Data (Session Specific)
- [x] Confirm if calibration data needs to persist between app restarts (current spec: per-session-start). Implement persistence if changed. (Implemented as per-session-start)

## 11. Background Operation & System Tray/Menu Bar Icon
- [x] Implement logic for posture monitoring to continue if the main window is closed.
- [x] Implement system tray icon (Windows, Linux) / menu bar icon (macOS). (PyQt handles abstraction)
- [x] Ensure icon is always present when the app is running.
- [x] Implement icon menu with options:
    - [x] "Open Ergo Window"
    - [x] "Start Session" / "Stop Session" (dynamic label)
    - [x] "Settings"
    - [x] "Quit Ergo"
- [x] Ensure menu options correctly trigger respective actions.
- [x] Implement logic for "Stop Session" button (main window and tray icon).
- [x] Implement "Quit Application" logic (stops session, closes background processes, exits).

## 12. Installation & Packaging
- [ ] Set up build process using PyInstaller, Briefcase, or similar for:
    - [ ] Windows: `.exe` installer (e.g., with Inno Setup).
    - [ ] macOS: `.dmg` containing signed `.app` bundle.
    - [ ] Linux: `AppImage`.
- [ ] Ensure all necessary dependencies (Python runtime, libraries, MediaPipe models) are bundled correctly.
- [ ] Test installers on clean target OS environments.

## 13. In-App Update Mechanism
- [x] Implement logic to check a manifest URL (Supabase Storage) on application startup.
    - [x] Parse manifest JSON (latest version, download URLs, release notes).
- [x] Implement version comparison logic.
- [x] If update available:
    - [x] Display small, non-intrusive notification.
    - [x] Implement automatic background download of the correct platform-specific installer from Supabase Storage.
    - [x] (Optional) Implement download progress indication. (Basic QProgressDialog implemented)
- [x] Once downloaded, prompt user to install and restart.
    - [x] On confirmation, guide user to run the downloaded installer (or attempt to launch it). (Opens download folder)
- [x] Develop the update manifest file (`update-info.json`) structure. (Assumed structure)

## 14. Error Handling & User Guidance
### 14.1. Webcam Issues
- [x] Implement detection and user messages for "No webcam," "Permission denied," "Webcam in use."
- [x] Ensure webcam selection works correctly if multiple webcams are present.
### 14.2. Poor Landmark Detection
- [x] Implement non-intrusive messages/tips for improving detection (lighting, visibility, distance).
- [x] Prevent calibration completion if detection is insufficient.
### 14.3. Network & Subscription Issues
- [x] Implement error messages for no internet (login, update check).
- [x] Implement error display for "Subscription Expired" (at login or session start attempt), guiding to web app.

## 15. Testing (Track completion of testing activities)
- [ ] Plan and execute Unit Tests (as per spec).
- [ ] Plan and execute Integration Tests (as per spec).
- [ ] Plan and execute UI/UX Tests (as per spec).
- [ ] Plan and execute Functional Tests (End-to-End) (as per spec).
- [ ] Plan and execute Performance Tests (as per spec).
- [ ] Plan and execute Cross-Platform Tests (Windows, macOS, Linux) (as per spec).
- [ ] Plan and execute Installation and Update Tests (as per spec).
- [ ] Plan and execute Error Handling and Edge Case Tests (as per spec).
- [ ] Coordinate and gather feedback from User Acceptance Testing (UAT).

## 16. Documentation
- [x] Write clear code comments and internal documentation for maintainability.
- [ ] Prepare information for the "Help/Documentation" section on the web app (relevant to desktop app usage).
- [x] Finalize text for Privacy Policy (relevant to desktop app data handling). (Added to About dialog)

## 17. Final Review & Polish
- [x] Review all UI text for clarity and consistency.
- [x] Perform a final walkthrough of all application features.
- [x] Check for any remaining bugs or usability issues.
- [x] Confirm application icon and branding elements are correctly implemented.
- [ ] Prepare final release builds for each platform.
