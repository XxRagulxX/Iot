import os
import subprocess
import json

# Configuration
remote_repo_url = "https://github.com/LineageOS/android_kernel_oneplus_sm8250.git"
local_repo_path = "/media/king/Linux/Kernelupdate/android_kernel_oneplus_sm7250/"  # Update this with your local repository path
last_local_commit = "245c7e59073add7c4bec107a7abb5f473fbb6762"  # Last commit in local repo
latest_remote_commit = "72c5422"  # Latest commit in the remote repo
json_file_path = "commits.json"

def run_command(command, cwd=None):
    try:
        result = subprocess.run(command, cwd=cwd, text=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return e.stderr.strip()

def fetch_remote_commits():
    if not os.path.exists(local_repo_path):
        print(f"Cloning repository {remote_repo_url}...")
        run_command(["git", "clone", remote_repo_url, local_repo_path])
    else:
        print("Fetching updates from remote repository...")
        run_command(["git", "fetch", "--all"], cwd=local_repo_path)

def get_commit_details():
    print(f"Fetching commits from {last_local_commit} to {latest_remote_commit}...")
    log_output = run_command(["git", "log", f"{last_local_commit}..{latest_remote_commit}", "--reverse", "--pretty=format:%H|%s|%ci"], cwd=local_repo_path)
    if not log_output:
        print("No new commits found.")
        return []
    
    commits = []
    for line in log_output.split("\n"):
        commit_id, message, date = line.split("|", 2)
        commits.append({"id": commit_id, "message": message, "date": date})
    return commits

def save_commits_to_json(commits):
    print(f"Saving commits to {json_file_path}...")
    with open(json_file_path, "w") as json_file:
        json.dump(commits, json_file, indent=4)
    print(f"Saved {len(commits)} commits.")

def prompt_user_for_commits():
    if os.path.exists(json_file_path):
        while True:
            choice = input(f"The file '{json_file_path}' already exists. Do you want to use the existing file? (yes/no): ").strip().lower()
            if choice in ["yes", "y"]:
                print("Using the existing commits file.")
                with open(json_file_path, "r") as json_file:
                    return json.load(json_file)
            elif choice in ["no", "n"]:
                print("Fetching new commits from the repository...")
                fetch_remote_commits()
                commits = get_commit_details()
                save_commits_to_json(commits)
                return commits
            else:
                print("Please answer 'yes' or 'no'.")
    else:
        print(f"No existing '{json_file_path}' file found. Fetching new commits...")
        fetch_remote_commits()
        commits = get_commit_details()
        save_commits_to_json(commits)
        return commits

def prompt_user_to_proceed():
    while True:
        proceed = input("The commits have been saved to 'commits.json'. Do you want to proceed with cherry-picking? (yes/no): ").strip().lower()
        if proceed in ["yes", "y"]:
            return True
        elif proceed in ["no", "n"]:
            print("Exiting without cherry-picking.")
            return False
        else:
            print("Please answer 'yes' or 'no'.")

def cherry_pick_commits(commits):
    print(f"Cherry-picking {len(commits)} commits...")
    for commit in commits:
        print(f"Cherry-picking commit {commit['id']} - {commit['message']}")
        result = run_command(["git", "cherry-pick", "--allow-empty", "--keep-redundant-commits", commit["id"]], cwd=local_repo_path)
        
        if "is a merge but no -m option was given" in result:
            print(f"Merge commit detected. Retrying with -m1 for commit {commit['id']}")
            result = run_command(["git", "cherry-pick", "--allow-empty", "--keep-redundant-commits", "-m1", commit["id"]], cwd=local_repo_path)
        
        if "The previous cherry-pick is now empty" in result or "empty commit" in result.lower():
            print(f"Skipping empty commit: {commit['id']}")
            run_command(["git", "cherry-pick", "--abort"], cwd=local_repo_path)
            continue
        
        if result is None or "error" in result.lower() or "fatal" in result.lower():
            print(f"Failed to cherry-pick {commit['id']}. Resolve conflicts manually and then run: git cherry-pick --continue")
            return
    
    print("Cherry-picking complete.")

if __name__ == "__main__":
    commits = prompt_user_for_commits()
    if commits:
        if prompt_user_to_proceed():
            cherry_pick_commits(commits)
