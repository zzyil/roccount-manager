# Roblox Account Manager (Roccount Manager)

A simple Python-based GUI application to manage and switch between multiple Roblox accounts on macOS and Windows without needing to re-enter passwords.

> [!WARNING]
> **Use at Your Own Risk**: This tool works by directly manipulating Roblox authentication files (macOS) or registry keys (Windows). While the method (swapping valid session cookies) is generally safe and similar to what other account managers do, **there is always a non-zero risk** when using third-party tools to interact with game authentication.
>
> **Safety Speculation**: This tool does *not* inject code into the game client runtime. It simply swaps the `.ROBLOSECURITY` cookie before the game launches. This should be undetectable by anti-cheat as standard behavior, but **we cannot guarantee safety** against future ban waves or policy changes.

## ⚠️ Windows Status
**The Windows version is currently UNTESTED.**
The code includes logic for Windows Registry manipulation (`HKCU\Software\Roblox\RobloxPlayer\roblox.com`), but it has not been verified on a live Windows machine as of Feb 2026. Use with caution.

## Prerequisites & Installation

You need Python 3 installed on your system.

1.  **Clone or download** this repository.
2.  **Install dependencies**:
    ```bash
    pip install customtkinter cryptography psutil
    ```

## Usage

### macOS
1.  Open a terminal in the project folder.
2.  Run the application:
    ```bash
    python3 main.py
    ```
3.  **To Add Accounts**:
    *   **Log in manually** to Roblox in your browser or the Roblox app.
    *   Open Roccount Manager and click **"Load Existing"**.
    *   Give it a nickname. This safely captures your current session file.
4.  **To Switch**:
    *   Select an account and click **"Switch and Launch"** to open Roblox as that user.
    *   Or click **"Load into Roblox"** to inject the session without launching the game immediately.

### Safe Guards
The app includes safeguards to preventing "cookie corruption":
-   If you try to switch accounts while Roblox is running, the app will warn you and offer to close Roblox safely for you.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
