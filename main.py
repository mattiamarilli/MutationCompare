import os
import csv
import shutil
from environment.config import *
from modules.pit_test_module import run_pit, analyze_pitest_report
from modules.defects4j_module import defects4j_checkout, defects4j_compile
from modules.major_test_module import run_defects4j_mutation, analyze_defects4j_report
from utils import copy_mutation_report

# File names
XML_PATH = "mutations.csv"
DEFECTS4J_RESULTS_PATH = "defects4j_mutation_results.xml"

# Environment setup
os.environ["PATH"] += os.pathsep + D4J_BIN_PATH
os.environ["JAVA_HOME"] = JAVA_HOME_11_PATH
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

os.makedirs(RESULTS_FOLDER, exist_ok=True)


def main():
    # CSV defining the projects to analyze
    projects_csv = "environment/projects.csv"

    with open(projects_csv, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            project_id = row['project_id']
            project_path = row['project_path']
            bug_id = row['bug_id']
            fixed_version = row['fixed_version']
            test_dir = row['test_dir']

            working_dir = f"/tmp/{project_id.lower()}_{bug_id}_{fixed_version}"
            log_file = os.path.join(working_dir, "kill.csv")
            major_log_file = os.path.join(working_dir, "mutants.log")

            # Clean previous working directory if present
            if os.path.exists(working_dir):
                shutil.rmtree(working_dir)

            os.makedirs(working_dir, exist_ok=True)
            print(f"\n=== Processing {project_id} bug {bug_id} ===")

            # Checkout project using Defects4J
            if not defects4j_checkout(project_id, bug_id, fixed_version, working_dir):
                print("Checkout failed. Skipping project.")
                continue

            # Compile project
            if not defects4j_compile(working_dir):
                print("Compilation failed. Skipping project.")
                continue

            print(f"\n=== PIT Mutation Testing ===")
            # Run PIT mutation testing
            if not run_pit(working_dir, project_path, test_dir):
                print("PIT execution failed. Skipping project.")
                continue

            # Copy PIT report
            project_pit_res_path = os.path.join(RESULTS_FOLDER, f"{project_id.lower()}_pit_{XML_PATH}")
            copy_mutation_report(working_dir, project_pit_res_path, True)

            # Analyze PIT report
            analyze_pitest_report(project_pit_res_path)

            print(f"\n=== MAJOR Mutation Testing ===")
            # Run MAJOR mutation testing
            if not run_defects4j_mutation(working_dir, project_path):
                print("MAJOR execution failed. Skipping project.")
                continue

            # Analyze MAJOR report
            analyze_defects4j_report(log_file, major_log_file)

            # Copy MAJOR report
            project_major_res_path = os.path.join(RESULTS_FOLDER, f"{project_id.lower()}_major_{XML_PATH}")
            copy_mutation_report(working_dir, project_major_res_path, False)

            print(f"Mutation testing completed for {project_id} bug {bug_id}")


if __name__ == "__main__":
    main()
