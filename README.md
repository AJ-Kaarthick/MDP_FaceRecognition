# SecureVision - Smart Security System

A Python-based security system using Face Recognition and Hand Gesture control.

## Features
- **Face Recognition**: Identifies registered users.
- **Gesture Control**: Requires a specific hand gesture (e.g., Fist) along with face verification for access.
- **Liveness Detection**: Simple blink detection to prevent photo spoofing.
- **User Management**: Register new users and add gestures via the UI.

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: `dlib` and `face_recognition` may require CMake and Visual Studio C++ compilers on Windows)*.

## Usage

Run the main application:
```bash
python main.py
```

### Controls
- **[R]**: Register a new user (Follow on-screen prompts).
- **[G]**: Add a new gesture to an existing user.
- **[ESC]**: Quit the application.

## Configuration
- User data encoded faces are stored locally in `users.json`. **Note**: This file is excluded from git for privacy.
