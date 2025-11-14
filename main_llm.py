import os
import csv
import subprocess
import shutil
from environment.config import *
from modules.defects4j_module import defects4j_checkout, defects4j_compile, defects4j_test

# === CONFIG ===
os.environ["PATH"] += os.pathsep + D4J_BIN_PATH
os.environ["JAVA_HOME"] = JAVA_HOME_11_PATH
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

RESULTS_FILE = os.path.join(RESULTS_FOLDER, "llm_mutation_results.csv")
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# === HELPER ===

def run_test_for_class_with_d4j(working_dir, mutated_class):
    test_name = f"{mutated_class}Test"
    print(f"🧪 Eseguo test: {test_name}")

    defects4j_compile(working_dir)
    defects4j_test(working_dir)

    failing_tests_file = os.path.join(working_dir, "failing_tests")

    if os.path.exists(failing_tests_file) and os.path.getsize(failing_tests_file) > 0:
        print("💀 Mutante ucciso (failing_tests non vuoto)")
        return "killed"
    else:
        print("Mutante sopravvissuto")
        return "Survived"



def apply_single_mutant(mutant_file, working_dir):
    if not os.path.exists(mutant_file):
        print(f"❌ Mutant file non trovato: {mutant_file}")
        return False

    filename = os.path.basename(mutant_file)
    original_class = filename.split("_Mutant_")[0] + ".java"
    print()

    src_dir = os.path.join(working_dir, "src", "main", "java", "org", "apache", "commons", "csv")
    dest_file = os.path.join(src_dir, original_class)
    print(src_dir)

    if not os.path.exists(dest_file):
        print(f"Classe originale non trovata: {dest_file}")
        return False

    # Sovrascrive la classe originale
    shutil.copy(mutant_file, dest_file)
    print(f"📄 Applicato mutante {filename} → {original_class}")
    return True


# === MAIN ===

def main():
    projects_csv = "environment/projects.csv"

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
            print(f"\n=== Elaborazione {project_id} bug {bug_id} ===")

            if os.path.exists(working_dir):
                print(f"⚠️  Cartella esistente trovata, la elimino: {working_dir}")
                shutil.rmtree(working_dir)

            if not defects4j_checkout(project_id, bug_id, fixed_version, working_dir):
                continue
            if not defects4j_compile(working_dir):
                continue

            for root, _, files in os.walk(mutants_base_dir):
                for mutant_file in files:
                    if not mutant_file.endswith(".java"):
                        continue

                    full_mutant_path = os.path.join(root, mutant_file)
                    mutated_class = mutant_file.split("_Mutant_")[0]

                    print(f"\n Test mutante: {mutant_file}")

                    if not apply_single_mutant(full_mutant_path, working_dir):
                        continue

                    result = run_test_for_class_with_d4j(working_dir, mutated_class)

                    with open(RESULTS_FILE, "a") as f:
                        f.write(f"{project_id},{bug_id},{mutant_file},{mutated_class},{result}\n")

if __name__ == "__main__":
    main()
