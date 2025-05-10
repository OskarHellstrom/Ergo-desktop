# PostureApp

A basic PyQt6 application with a stacked widget for managing multiple views, webcam-based posture detection, and Supabase authentication/subscription management.

## Setup

1. **Install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   # Or, if you are missing dependencies:
   pip install PyQt6 opencv-python mediapipe matplotlib python-dotenv requests
   ```

2. **Download the pose model:**
   (Already included in the repo, but if needed, run:)
   ```bash
   wget -O PostureApp/models/pose_landmarker_heavy.task \
     https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task
   ```

3. **Set up your .env file:**
   Create a `.env` file in the `PostureApp/` directory with:
   ```env
   NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
   ```

4. **Run the application:**
   ```bash
   PostureApp/.venv/bin/python PostureApp/main.py
   ```

## Usage

- **Sign Up:**
  - On the login screen, click the **Sign Up** button.
  - Enter your email and password, confirm your password, and submit.
  - Check your email for a verification link and verify your account.
  - Return to the app and log in with your new credentials.

- **Login:**
  - Enter your email and password and click **Login**.
  - If your subscription is active, you will be taken to the dashboard.

- **Subscription:**
  - Subscriptions are managed by an admin in Supabase.
  - After signing up, an admin must add a record for your user in the `user_subscriptions` table with:
    - `user_id`: The user's Supabase Auth ID (find in the Supabase Auth > Users table for your email)
    - `status`: `active`
    - `expires_at`: A future date (e.g., `2025-12-31T23:59:59Z`)
  - Without an active subscription, you cannot access the dashboard.

### Example: Making a User a Subscriber (Admin Only)

1. **Find the user's ID:**
   - Go to Supabase web console > Auth > Users.
   - Find the user by email (e.g., `oskar.hellstrom@outlook.com`).
   - Copy the user's `id` (UUID).

2. **Insert a subscription record:**
   - Go to the `user_subscriptions` table in Supabase.
   - Insert a new row:
     - `user_id`: (paste the user's UUID)
     - `status`: `active`
     - `expires_at`: (e.g., `2025-12-31T23:59:59Z`)

3. **User can now log in and access the dashboard.**

---

For more details, see the Supabase documentation or contact your system administrator.

## Structure
- `main.py`: Main application entry point, defines the main window and placeholder views.
- `requirements.txt`: Python dependencies. 