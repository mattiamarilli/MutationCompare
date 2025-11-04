import os
import csv
import subprocess
import shutil
from environment.config import *
from modules.defects4j_module import defects4j_checkout, defects4j_compile

# === CONFIG ===
os.environ["PATH"] += os.pathsep + D4J_BIN_PATH
os.environ["JAVA_HOME"] = JAVA_HOME_11_PATH
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

RESULTS_FILE = os.path.join(RESULTS_FOLDER, "llm_mutation_results.csv")
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# === HELPER ===

def run_test_for_class(working_dir, mutated_class):
    """Esegue il test corrispondente alla classe mutata (es. CSVFormatTest)."""
    test_name = f"{mutated_class}Test"
    print(f"🧪 Eseguo test: {test_name}")

    result = subprocess.run(
        ["defects4j", "test", "-t", test_name],
        cwd=working_dir,
        capture_output=True,
        text=True
    )

    if "Failing tests:" in result.stdout:
        return "killed"
    elif "No tests executed" in result.stdout:
        return "unknown"
    else:
        return "survived"


def apply_single_mutant(mutant_file, working_dir, base_package_path):
    """Applica un singolo file mutante rinominandolo come la classe originale."""
    if not os.path.exists(mutant_file):
        print(f"❌ Mutant file non trovato: {mutant_file}")
        return False

    filename = os.path.basename(mutant_file)
    # Esempio: CSVFormat_Mutant_1.java -> CSVFormat.java
    original_class = filename.split("_Mutant_")[0] + ".java"

    src_dir = os.path.join(working_dir, "src", "main", "java", "org", "apache", "commons", "csv")
    dest_file = os.path.join(src_dir, original_class)

    if not os.path.exists(dest_file):
        print(f"⚠️ Classe originale non trovata: {dest_file}")
        return False

    # Sovrascrive la classe originale
    shutil.copy(mutant_file, dest_file)
    print(f"📄 Applicato mutante {filename} → {original_class}")
    return True


def restore_original_code(working_dir, project_id, bug_id, fixed_version):
    subprocess.run(
        ["defects4j", "checkout", "-p", project_id, "-v", f"{bug_id}{fixed_version}", "-w", working_dir],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


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

            if not defects4j_checkout(project_id, bug_id, fixed_version, working_dir):
                continue
            if not defects4j_compile(working_dir):
                continue

            for root, _, files in os.walk(mutants_base_dir):
                for mutant_file in files:
                    if not mutant_file.endswith(".java"):
                        continue

                    full_mutant_path = os.path.join(root, mutant_file)
                    base_package_path = os.path.relpath(root, mutants_base_dir)

                    mutated_class = mutant_file.split("_Mutant_")[0]

                    print(f"\n🧬 Test mutante: {mutant_file}")

                    if not apply_single_mutant(full_mutant_path, working_dir, base_package_path):
                        continue

                    if not defects4j_compile(working_dir):
                        print(" Compilazione fallita per mutante, skip.")
                        restore_original_code(working_dir, project_id, bug_id, fixed_version)
                        continue

                    result = run_test_for_class(working_dir, mutated_class)

                    with open(RESULTS_FILE, "a") as f:
                        f.write(f"{project_id},{bug_id},{mutant_file},{mutated_class},{result}\n")

                    # Ripristina il codice originale per il prossimo mutante
                    restore_original_code(working_dir, project_id, bug_id, fixed_version)
                    defects4j_compile(working_dir)


if __name__ == "__main__":
    main()
