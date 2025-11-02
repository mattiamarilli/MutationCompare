import os
import csv
from environment.config import *
from modules.pit_test_module import run_pit, analyze_pitest_report
from modules.defects4j_module import  defects4j_checkout, defects4j_compile
from modules.major_test_module import run_defects4j_mutation, analyze_defects4j_report
from utils import copy_mutation_report

XML_PATH = "mutations.csv"
DEFECTS4J_RESULTS_PATH = "defects4j_mutation_results.xml"

os.environ["PATH"] += os.pathsep + D4J_BIN_PATH
os.environ["JAVA_HOME"] = JAVA_HOME_11_PATH
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

os.makedirs(RESULTS_FOLDER, exist_ok=True)

def main():
    projects_csv = "environment/projects.csv"

    with open(projects_csv, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            project_id = row['project_id']
            project_path = row['project_path']
            bug_id = row['bug_id']
            fixed_version = row['fixed_version']
            id_dir = row['id_dir']
            test_dir = row['test_dir']

            working_dir = f"/tmp/{project_id.lower()}_{bug_id}_{fixed_version}"
            log_file = os.path.join(working_dir, "kill.csv")

            os.makedirs(working_dir, exist_ok=True)
            print(f"\n=== Elaborazione {project_id} bug {bug_id} ===")

            if not defects4j_checkout(project_id, bug_id, fixed_version, working_dir):
                continue
            if not defects4j_compile(working_dir):
                continue
            if not run_pit(working_dir, project_path, test_dir):
                continue

            project_pit_res_path = os.path.join(RESULTS_FOLDER, f"{project_id.lower()}_{XML_PATH}")
            copy_mutation_report(working_dir, project_pit_res_path)
            analyze_pitest_report(project_pit_res_path)

            if not run_defects4j_mutation(working_dir):
                continue

            os.path.join(RESULTS_FOLDER, f"{project_id.lower()}_{DEFECTS4J_RESULTS_PATH}")
            analyze_defects4j_report(log_file)

            print(f"Mutation testing completato per {project_id} bug {bug_id}")


if __name__ == "__main__":
    main()
