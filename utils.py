import os
import subprocess
import shutil

def run_command(command, cwd=None):
    """
    Execute a shell command in an optional working directory.
    Returns stdout, stderr, and the exit code.
    """
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def copy_mutation_report(working_dir, dest_file, pit=True):
    """
    Copy the mutation testing report from the working directory
    into the destination file.

    - If pit=True, copies PIT's mutations.csv.
    - If pit=False, copies Major's mutants_major.csv.

    Returns True if the file was copied successfully, False otherwise.
    """
    if pit:
        source_file = os.path.join(working_dir, "target", "pit-reports", "mutations.csv")
    else:
        source_file = os.path.join(working_dir, "mutants_major.csv")

    if os.path.exists(source_file):
        shutil.copy(source_file, dest_file)
        print(f"File mutations.csv copied to {dest_file}")
        return True
    else:
        print(f"File {source_file} not found for destination {dest_file}")
        return False
