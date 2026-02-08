import os
import subprocess
import time
import sys

def get_py_files(directory):
    py_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return py_files

def get_file_mtimes(files):
    # Use a dictionary to store file paths and their modification times
    return {f: os.path.getmtime(f) for f in files}

def main():
    app_dir = 'app'
    main_file = os.path.join(app_dir, 'main.py')
    
    if not os.path.exists(main_file):
        print(f"Error: {main_file} not found.")
        sys.exit(1)

    py_files = get_py_files(app_dir)
    last_mtimes = get_file_mtimes(py_files)
    
    # Start the application using the python executable that is running the reloader
    process = subprocess.Popen([sys.executable, main_file])
    print("Application started. Watching for changes...")

    try:
        while True:
            time.sleep(1)
            
            # Check for new files
            current_py_files = get_py_files(app_dir)
            if set(current_py_files) != set(py_files):
                py_files = current_py_files
                print("New python files detected.")
            
            new_mtimes = get_file_mtimes(py_files)

            # Check for modified files
            if new_mtimes != last_mtimes:
                print("Changes detected. Reloading application...")
                process.terminate()
                process.wait()
                
                last_mtimes = get_file_mtimes(py_files)

                process = subprocess.Popen([sys.executable, main_file])
                print("Application reloaded.")
            
            # Check if process is still running
            if process.poll() is not None:
                # If the user closes the GUI window, the subprocess will terminate.
                # The reloader should exit as well.
                print("Application process has terminated. Exiting reloader.")
                break

    except KeyboardInterrupt:
        print("Stopping reloader...")
        process.terminate()
        process.wait()
        print("Application stopped.")

if __name__ == "__main__":
    main()
