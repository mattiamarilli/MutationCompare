import os
import subprocess
import shutil

def run_command(command, cwd=None):
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def copy_mutation_report(working_dir, dest_file, pit=True):
    if pit:
        source_file = os.path.join(working_dir, "target", "pit-reports", "mutations.csv")
    else:
        source_file = os.path.join(working_dir, "mutants_major.csv")

    if os.path.exists(source_file):
        shutil.copy(source_file, dest_file)
        print(f"File mutations.csv copiato in {dest_file}")
        return True
    else:
        print(f"File {source_file} non trovato in {dest_file}")
        return False
