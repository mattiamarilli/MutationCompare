import os
import csv
import shutil
from environment.config import *
from modules.defects4j_module import defects4j_checkout, defects4j_compile
from modules.llm_test_module import generate_mutants_for_project, apply_single_mutant, log_java_file, \
    run_test_for_class_with_d4j

# Environment setup
os.environ["PATH"] += os.pathsep + D4J_BIN_PATH
os.environ["JAVA_HOME"] = JAVA_HOME_11_PATH
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

RESULTS_FILE = "llm_mutation_results.csv"

os.makedirs(RESULTS_FOLDER, exist_ok=True)

def main():
    # CSV defining the projects to analyze
    projects_csv = "environment/projects.csv"
    llm_models = ['google/gemini-2.5-flash-lite']

    # Create global results file if missing
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "w") as f:
            f.write("project_id,bug_id,mutant_name,class,result\n")

    with open(projects_csv, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            project_id = row['project_id']
            bug_id = row['bug_id']
            fixed_version = row['fixed_version']

            working_dir = f"/tmp/{project_id.lower()}_{bug_id}_{fixed_version}"
            mutants_base_dir = os.path.join("mutants", f"{project_id}_{bug_id}")

            print(f"\n=== Processing {project_id} bug {bug_id} ===")

            # Clean previous working directory if present
            if os.path.exists(working_dir):
                shutil.rmtree(working_dir)

            # Checkout and compile Defects4J project
            if not defects4j_checkout(project_id, bug_id, fixed_version, working_dir):
                print("Checkout failed. Skipping project.")
                continue

            if not defects4j_compile(working_dir):
                print("Compilation failed. Skipping project.")
                continue

            # Iterate through LLM models
            for model in llm_models:

                # Clean mutants directory for the model
                if os.path.exists(mutants_base_dir):
                    shutil.rmtree(mutants_base_dir)

                # Generate mutants for this project using the LLM
                generate_mutants_for_project(
                    working_dir, project_id, bug_id,
                    model != GOOGLE_GEMINI, model
                )

                # Log all .java files in the project
                src_dir = os.path.join(working_dir, "src/main/java")
                for root, _, files in os.walk(src_dir):
                    for file in files:
                        if file.endswith(".java"):
                            full_path = os.path.join(root, file)
                            log_java_file(full_path, working_dir)

                # Apply each mutant and test it
                for root, _, files in os.walk(mutants_base_dir):
                    for mutant_file in files:

                        # Ensure clean working directory for each mutant
                        if os.path.exists(working_dir):
                            shutil.rmtree(working_dir)

                        if not defects4j_checkout(project_id, bug_id, fixed_version, working_dir):
                            print("Checkout failed during mutant iteration.")
                            continue

                        if not mutant_file.endswith(".java"):
                            continue

                        full_mutant_path = os.path.join(root, mutant_file)
                        mutated_class = mutant_file.split("_Mutant_")[0]

                        print(f"\n Testing mutant: {mutant_file}")

                        # Apply single mutant to project
                        if not apply_single_mutant(full_mutant_path, working_dir):
                            print("Failed to apply mutant.")
                            continue

                        # Directory for results based on model name
                        result_model_dir = os.path.join(RESULTS_FOLDER, model.split("/")[0])
                        print(result_model_dir)

                        # Run Defects4J tests for mutated class
                        result = run_test_for_class_with_d4j(working_dir, mutated_class)

                        result_file_path = os.path.join(result_model_dir, RESULTS_FILE)
                        os.makedirs(result_model_dir, exist_ok=True)

                        # Create model-specific results file if missing
                        if not os.path.exists(result_file_path):
                            with open(result_file_path, "w") as f:
                                f.write("project_id,bug_id,mutant_name,class,result\n")

                        # Append results
                        with open(result_file_path, "a") as f:
                            f.write(f"{project_id},{bug_id},{mutant_file},{mutated_class},{result}\n")


if __name__ == "__main__":
    main()
