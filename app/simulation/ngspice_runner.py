"""
simulation/ngspice_runner.py

Handles execution of ngspice simulations
"""

import os
import shutil
import subprocess
import platform
from datetime import datetime


class NgspiceRunner:
    """Runs ngspice simulations and manages output files"""
    
    def __init__(self, output_dir="simulation_output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.ngspice_cmd = None
    
    def find_ngspice(self):
        """Find ngspice executable on the system"""
        # Try PATH lookup first (works cross-platform)
        which_result = shutil.which('ngspice')
        if which_result:
            self.ngspice_cmd = which_result
            return which_result

        system = platform.system()

        # Fallback: check common installation paths
        if system == "Windows":
            possible_paths = [
                r'C:\Program Files (x86)\ngspice\bin\ngspice.exe',
                r'C:\ngspice\bin\ngspice.exe',
                r'C:\ngspice-42\Spice64\bin\ngspice.exe',
                r"C:\Program Files\Spice64\bin\ngspice.exe",
                r"C:\Program Files\ngspice\bin\ngspice.exe",
            ]
        elif system == "Linux":
            possible_paths = [
                '/usr/bin/ngspice',
                '/usr/local/bin/ngspice',
            ]
        elif system == "Darwin":  # macOS
            possible_paths = [
                '/usr/local/bin/ngspice',
                '/opt/homebrew/bin/ngspice',
            ]
        else:
            possible_paths = []

        for cmd in possible_paths:
            if os.path.exists(cmd):
                self.ngspice_cmd = cmd
                return cmd

        return None
    
    def run_simulation(self, netlist_content):
        """
        Run ngspice simulation with the given netlist
        
        Returns:
            tuple: (success: bool, output_file: str, stdout: str, stderr: str)
        """
        # Find ngspice if not already found
        if self.ngspice_cmd is None:
            ngspice_path = self.find_ngspice()
            if ngspice_path is None:
                return False, None, "", "ngspice executable not found"
        
        # Create timestamped filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        netlist_filename = os.path.join(self.output_dir, f"netlist_{timestamp}.cir")
        output_filename = os.path.join(self.output_dir, f"output_{timestamp}.txt")
        
        # Write netlist to file
        try:
            with open(netlist_filename, 'w') as f:
                f.write(netlist_content)
        except Exception as e:
            return False, None, "", f"Failed to write netlist: {str(e)}"
        
        # Run ngspice
        try:
            result = subprocess.run(
                [self.ngspice_cmd, '-b', netlist_filename, '-o', output_filename],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Check if output file was created
            if os.path.exists(output_filename):
                return True, output_filename, result.stdout, result.stderr
            else:
                return False, None, result.stdout, result.stderr or "Output file not created"
                
        except subprocess.TimeoutExpired:
            return False, None, "", "Simulation timed out (>60 seconds)"
        except Exception as e:
            return False, None, "", f"Simulation error: {str(e)}"
    
    def read_output(self, output_filename):
        """Read simulation output file"""
        try:
            with open(output_filename, 'r') as f:
                return f.read()
        except Exception as e:
            return f"Error reading output: {str(e)}"