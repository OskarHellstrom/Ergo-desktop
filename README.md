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

### Creating a Linux AppImage "From Scratch"

This section explains how to package the Ergo application into a portable `AppImage` for Linux systems. This process involves first bundling the Python application using PyInstaller, then constructing an `AppDir` (Application Directory), and finally using `appimagetool` to convert the `AppDir` into an AppImage.

The `appimagetool-x86_64.AppImage` utility is included in the project root. Ensure it is executable:
```bash
chmod +x appimagetool-x86_64.AppImage
```

**Steps to build the AppImage:**

1.  **Ensure PyInstaller Build is Up-to-Date:**
    The AppImage relies on the output of PyInstaller. Build or update your PyInstaller bundle by running the following from the project root (ensure your virtual environment is active):
    ```bash
    .venv/bin/python -m PyInstaller main.spec --noconfirm
    ```
    This command uses the `main.spec` file and places the bundled application into the `dist/main/` directory.

2.  **Prepare the Application Directory (`AppDir`):**
    The `AppImage` is built from a specially structured directory, conventionally named `YourAppName.AppDir`.
    
    *   **Clean up previous build (optional but recommended):**
        ```bash
        rm -rf Ergo.AppDir Ergo-x86_64.AppImage
        ```
    *   **Create the `AppDir` structure:**
        ```bash
        mkdir -p Ergo.AppDir/usr/bin
        mkdir -p Ergo.AppDir/usr/lib
        mkdir -p Ergo.AppDir/usr/share/icons/hicolor/256x256/apps
        ```
    *   **Copy PyInstaller output:**
        Copy all contents from the PyInstaller build directory (`dist/main/`) into `Ergo.AppDir/usr/bin/`:
        ```bash
        cp -r dist/main/* Ergo.AppDir/usr/bin/
        ```
        *(Note: PyInstaller bundles Python itself, so we place the app contents directly where AppRun expects to find the executable).*

    *   **Add the `AppRun` script:**
        This script is the entry point for the AppImage. It sets up the environment and executes your application.
        Copy the existing `AppRun` script from the project root to `Ergo.AppDir/AppRun`.
    ```bash
        cp AppRun Ergo.AppDir/
        chmod +x Ergo.AppDir/AppRun
        ```
        Ensure your `AppRun` script (located in the project root) is configured correctly. It is **critical** for the AppImage to function. Key considerations for `AppRun`:
        *   **Working Directory:** PyInstaller-bundled applications often need to be executed from their own directory. Use `cd "$HERE/usr/bin"` (or equivalent based on your `AppDir` structure) before the `exec` line.
        *   **Executable Path:** The `exec` command should call the executable relative to the new working directory (e.g., `exec "./main" "$@"`).
        *   **`LD_LIBRARY_PATH`:** PyInstaller may bundle the Python shared library (e.g., `libpythonX.Y.so`) in a subdirectory like `_internal` relative to the main executable. This path must be explicitly added to `LD_LIBRARY_PATH`. For example: `export LD_LIBRARY_PATH="$HERE/usr/bin/_internal:$HERE/usr/lib:$HERE/usr/bin:$LD_LIBRARY_PATH"` (adjust `_internal` if PyInstaller places it elsewhere).
        *   Other environment variables like `QT_PLUGIN_PATH` should also be set relative to `$HERE`.

        A robust `AppRun` script, reflecting these points, might look like this (the one in the project root should be similar):
        ```sh
        #!/bin/sh
        HERE=$(dirname "$(readlink -f "$0")")

        # Set up library and plugin paths, including PyInstaller's internal lib directory
        export LD_LIBRARY_PATH="$HERE/usr/bin/_internal:$HERE/usr/lib:$HERE/usr/bin:$LD_LIBRARY_PATH"
        export QT_PLUGIN_PATH="$HERE/usr/bin/PyQt6/Qt6/plugins:$HERE/usr/bin/plugins:$QT_PLUGIN_PATH"
        export QT_QPA_PLATFORM_PLUGIN_PATH="$HERE/usr/bin/PyQt6/Qt6/plugins/platforms"
        export QML2_IMPORT_PATH="$HERE/usr/bin/PyQt6/Qt6/qml:$QML2_IMPORT_PATH"
        
        # Change to the directory where the executable is located.
        # This is crucial for PyInstaller bundles to find their dependencies.
        cd "$HERE/usr/bin" || exit 1
        
        # Execute the main application binary.
        exec "./main" "$@"
        ```

    *   **Add the `.desktop` file:**
        This file provides metadata for desktop integration (name, icon, categories).
        Copy the `ergo.desktop` file from the project root to `Ergo.AppDir/ergo.desktop`.
        ```bash
        cp ergo.desktop Ergo.AppDir/
        ```
        Ensure your `ergo.desktop` file is correctly configured. It should look something like:
        ```desktop
        [Desktop Entry]
        Version=1.1
        Name=Ergo
        Comment=Improve your posture with real-time feedback.
        Exec=main # This should match the executable name inside AppDir/usr/bin/
        Icon=ergo # This should match the icon filename (without extension)
        Terminal=false
        Type=Application
        Categories=Utility;
        ```

    *   **Add the application icon:**
        Place your application icon (e.g., `ergo.png`) in `Ergo.AppDir/` (root of AppDir) and also in `Ergo.AppDir/usr/share/icons/hicolor/256x256/apps/`. The `.desktop` file references the icon by its name (e.g., `ergo`).
        Assuming your icon is `resources/icons/ergo-logo.png`:
        ```bash
        cp resources/icons/ergo-logo.png Ergo.AppDir/ergo.png
        cp resources/icons/ergo-logo.png Ergo.AppDir/usr/share/icons/hicolor/256x256/apps/ergo.png
        ```

3.  **Generate the AppImage:**
    Now, use `appimagetool` to convert the `Ergo.AppDir` directory into a single AppImage file. Run this command from the project root:
    ```bash
    ./appimagetool-x86_64.AppImage Ergo.AppDir
    ```
    This will create `Ergo-x86_64.AppImage` (or a similar name based on your desktop file and architecture) in your project root directory.

4.  **Make it Executable and Run:**
    ```bash
    chmod +x Ergo-x86_64.AppImage
    ./Ergo-x86_64.AppImage
    ```

This process gives you a self-contained AppImage that can be distributed and run on various Linux distributions. Remember to test it on a clean environment if possible.

### Creating a Windows Executable

To package the application as an executable for Windows:

1.  **Environment Setup:**
    *   You must run these steps on a Windows machine (or a Windows virtual machine).
    *   Ensure you have Python installed on Windows and added to your system's PATH.
    *   Clone the project repository to your Windows environment.
    *   Create and activate a virtual environment:
        ```bash
        python -m venv .venv
        .venv\Scripts\activate
        ```
    *   Install dependencies:
        ```bash
        pip install -r requirements.txt
        ```
    *   Install PyInstaller (if not already in `requirements.txt` specifically for Windows builds):
        ```bash
        pip install pyinstaller
        ```

2.  **Modify `main.spec` (Icon Handling):
    *   PyInstaller can bundle an `.ico` file for the application icon on Windows.
    *   Ensure your `main.spec` file's `exe` section has the `icon` parameter pointing to a valid `.ico` file (e.g., `icon='resources/icons/ergo-logo.ico'`). You might need to convert your `ergo-logo.png` to an `ergo-logo.ico` file using an online converter or a tool like GIMP or ImageMagick.
    *   The `console=False` setting in `main.spec` will ensure no command window appears when the GUI app runs.

3.  **Build with PyInstaller:**
    *   Run PyInstaller using the `.spec` file:
        ```bash
        python -m PyInstaller main.spec --noconfirm
        ```
    *   This will create a `dist\main` directory containing your executable (`main.exe`) and all its dependencies.

4.  **Testing:**
    *   Navigate to `dist\main` and run `main.exe`.

5.  **Distribution (Optional - Creating a Single Installer File):
    *   The `dist\main` folder contains everything needed. You can zip this folder and distribute it.
    *   For a more professional single-file installer (`.exe` or `.msi`), you would typically use a third-party installer creation tool like Inno Setup (free) or NSIS (free). These tools can take the output from PyInstaller's `dist/main` folder and package it into a guided installer, create shortcuts, allow uninstallation, etc.
        *   **Example (Inno Setup):** You would write an Inno Setup script (`.iss`) that specifies the files from `dist/main`, where to install them, shortcuts to create, etc., and then compile that script with Inno Setup to produce a single `setup.exe`.

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
- `.env`: Environment variables (Supabase URL/Key). This file is bundled with the AppImage. To use your own Supabase project, edit the `.env` file in the same directory as the AppImage before running it, or repackage the AppImage with your own `.env`.
- `README.md`: This file.
- `spec.md`: Application specification details.
- `todo.md`: Development task tracking.

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on how to contribute to this project.

### Environment Variables and AppImage

The `.env` file is bundled inside the AppImage. If you need to use your own Supabase credentials:

1.  Edit the `.env` file in your project root before building the AppImage, then rebuild.
2.  Or, after extracting the AppImage (using `--appimage-extract`), replace the `.env` file in the extracted directory and repackage if needed.
3.  The application will always load the `.env` file from the same directory as the executable, so you can update it as needed for different deployments. 