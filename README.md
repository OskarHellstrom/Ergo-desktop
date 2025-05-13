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

1.  **Clone the repository:**
    ```bash
    git clone https://your-repository-url.git
    cd PostureApp
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up Supabase (if not already done):**
    *   Ensure your Supabase URL and Anon Key are correctly configured (e.g., in `.env` or `auth_service.py`).
5.  **Run the application:**
    ```bash
    python main.py
    ```

## Packaging with PyInstaller

This project uses PyInstaller to create distributable executables.

### Prerequisites

1.  Ensure you have Python and your project's virtual environment set up.
2.  Activate your virtual environment:
    ```bash
    source .venv/bin/activate
    ```
3.  Install PyInstaller if you haven't already (it should also be in `requirements.txt`):
    ```bash
    .venv/bin/python -m pip install pyinstaller
    ```
    If `pyinstaller` is listed in your `requirements.txt`, the regular `pip install -r requirements.txt` would have installed it.

### Building the Application

The project includes a `main.spec` file which is configured to bundle all necessary scripts, resources (like images and stylesheets), and MediaPipe models.

To build the application, run the following command from the project root directory:

```bash
.venv/bin/python -m PyInstaller main.spec --noconfirm
```

### Output

The bundled application will be located in the `dist/main` directory. This directory contains the executable and all its dependencies.

### Notes

*   The `main.spec` file is critical for a successful build. It includes specific paths to data files.
*   The current build process creates a "one-folder" bundle. The entire `dist/main` directory is needed to run the application.
*   If you modify resource paths or add new dependencies, you might need to update `main.py` (to use the `resource_path()` utility function for any new resources) and potentially `main.spec` if new data files need to be explicitly included.

### Creating a Linux AppImage

To package the application as a portable AppImage for Linux:

1.  **Build with PyInstaller:** First, ensure you have a working PyInstaller build in `dist/main` by running:
    ```bash
    .venv/bin/python -m PyInstaller main.spec --noconfirm
    ```

2.  **Get `appimagetool`:** Download the `appimagetool` utility (e.g., `appimagetool-x86_64.AppImage`) from [AppImageKit releases](https://github.com/AppImage/AppImageKit/releases) and place it in your project root. Make it executable:
    ```bash
    # Example:
    # wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    # chmod +x appimagetool-x86_64.AppImage
    ```
    *(Ensure you have `appimagetool-x86_64.AppImage` in your project root for the next commands, or adjust paths accordingly).*

3.  **Prepare `.desktop` and `AppRun` files:**
    *   Ensure you have an `ergo.desktop` file in your project root with content similar to this:
        ```desktop
        [Desktop Entry]
        Version=1.1
        Name=Ergo
        Comment=Improve your posture with real-time feedback.
        Exec=main
        Icon=ergo
        Terminal=false
        Type=Application
        Categories=Utility
        ```
    *   Ensure you have an `AppRun` script in your project root. This script is the entry point for the AppImage. A suitable version:
        ```sh
        #!/bin/sh
        HERE=$(dirname "$(readlink -f "$0")")
        export LD_LIBRARY_PATH="$HERE/lib:$LD_LIBRARY_PATH"
        export QT_PLUGIN_PATH="$HERE/plugins:$HERE/PyQt6/Qt6/plugins:$QT_PLUGIN_PATH"
        export QML2_IMPORT_PATH="$HERE/PyQt6/Qt6/qml:$QML2_IMPORT_PATH"
        # Optional: Add any other environment variable setups needed by your app
        exec "$HERE/main" "$@"
        ```
        Make sure `AppRun` is executable (`chmod +x AppRun`).

4.  **Create the AppImage:** Run the following commands from your project root. This will create an `Ergo.AppDir` directory, populate it, and then use `appimagetool` to generate `Ergo-x86_64.AppImage`.
    ```bash
    # Clean up previous attempts (optional, but good practice)
    rm -rf Ergo.AppDir Ergo-x86_64.AppImage 

    # Create and populate AppDir
    mkdir -p Ergo.AppDir
    cp -r dist/main/* Ergo.AppDir/
    cp ergo.desktop Ergo.AppDir/
    cp resources/icons/ergo-logo.png Ergo.AppDir/ergo.png # Icon referred by .desktop
    cp AppRun Ergo.AppDir/
    chmod +x Ergo.AppDir/AppRun

    # Build the AppImage (ensure appimagetool is in the current path or use ./appimagetool-x86_64.AppImage)
    ./appimagetool-x86_64.AppImage Ergo.AppDir
    ```

5.  **Run:**
    ```bash
    chmod +x Ergo-x86_64.AppImage
    ./Ergo-x86_64.AppImage
    ```

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

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on how to contribute to this project. 