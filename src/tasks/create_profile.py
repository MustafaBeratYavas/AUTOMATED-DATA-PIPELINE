# -- Chrome Profile Creator Utility --
# CLI tool that bootstraps a persistent Chrome user data directory.
# This isolated profile ensures session cookies and local storage
# persist across scraping runs, reducing CAPTCHA trigger frequency.

import os
import argparse
import sys

def create_chrome_profile(user_data_dir: str, profile_name: str):
    # Resolve absolute paths relative to the project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    
    full_user_data_path = os.path.join(root_dir, user_data_dir)
    full_profile_path = os.path.join(full_user_data_path, profile_name)

    print(f"User Data Path: {full_user_data_path}")
    print(f"Profile Name:   {profile_name}")

    # Create the profile directory structure if it does not already exist
    if not os.path.exists(full_profile_path):
        try:
            os.makedirs(full_profile_path, exist_ok=True)
            print(f"Successfully created profile directory: {full_profile_path}")
        except OSError as e:
            print(f"Error creating profile directory: {e}")
            sys.exit(1)
    else:
        print("Profile directory already exists.")

def main():
    # Parse CLI arguments for custom user data and profile paths
    parser = argparse.ArgumentParser(description="Automated Data Pipeline — Chrome Profile Creator")

    parser.add_argument("--user-data-dir", default=".browser_profile")
    parser.add_argument("--profile-name", default="Profile 1")

    args = parser.parse_args()
    create_chrome_profile(args.user_data_dir, args.profile_name)

if __name__ == "__main__":
    main()
