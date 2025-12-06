import os
import csv
import shutil
from environment.config import *
from modules.defects4j_module import defects4j_checkout, defects4j_compile, defects4j_test
from modules.llm_mutation_engine_module import LLMMutationEngine

os.environ["PATH"] += os.pathsep + D4J_BIN_PATH
os.environ["JAVA_HOME"] = JAVA_HOME_11_PATH
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

RESULTS_FILE = os.path.join(RESULTS_FOLDER, "llm_mutation_results.csv")

os.makedirs(RESULTS_FOLDER, exist_ok=True)

def run_test_for_class_with_d4j(working_dir, mutated_class):
    test_name = f"{mutated_class}Test"
    print(f"🧪 Eseguo test: {test_name}")

    defects4j_compile(working_dir)
    defects4j_test(working_dir)

    failing_tests_file = os.path.join(working_dir, "failing_tests")

    print(failing_tests_file)

    if os.path.exists(failing_tests_file) and os.path.getsize(failing_tests_file) > 0:
        print("💀 Mutante ucciso (failing_tests non vuoto)")
        return "killed"
    else:
        print("Mutante sopravvissuto")
        return "Survived"

def log_java_file(java_file_path, working_dir):
    # Percorso relativo a working_dir/src
    src_root = os.path.join(working_dir, "src")
    relative_path = os.path.relpath(java_file_path, src_root)

    print(f"📄 File Java trovato: {relative_path}")

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def generate_mutants_for_project(working_dir, project_id, bug_id, is_open_router=False, model=""):
    src_dir = os.path.join(working_dir, "src", "main", "java")
    base_mutants_dir = os.path.join("mutants", f"{project_id}_{bug_id}")

    ensure_dir(base_mutants_dir)

    engine = LLMMutationEngine(is_open_router, model)

    print(f"🔍 Generazione mutanti per: {src_dir}")

    for root, _, files in os.walk(src_dir):
        for file in files:
            if not file.endswith(".java"):
                continue

            java_path = os.path.join(root, file)

            rel_path = os.path.relpath(java_path, src_dir)
            rel_folder = os.path.dirname(rel_path)

            target_dir = os.path.join(base_mutants_dir, rel_folder)
            ensure_dir(target_dir)

            print(f"📄 Analisi file Java: {rel_path}")

            # Genera mutazioni via LLM
            mutations = engine.mutate_java_file(java_path)

            if not mutations:
                print("⚠️  Nessuna mutazione generata")
                continue

            print(f"⚡ {len(mutations)} mutazioni generate → salvo mutanti in {target_dir}")

            class_name = file.replace(".java", "")

            for idx, mutation in enumerate(mutations, start=1):
                mutant_file = os.path.join(
                    target_dir,
                    f"{class_name}_Mutant_{idx}.java"
                )

                with open(java_path, "r") as original_file:
                    content_lines = original_file.readlines()

                original_line = mutation["original_code"].strip()
                mutated_line = mutation["mutated_code"]

                new_content = []
                for line in content_lines:
                    if line.strip() == original_line:
                        new_content.append(mutated_line + "\n")
                    else:
                        new_content.append(line)

                with open(mutant_file, "w") as mf:
                    mf.write("// MUTATION:\n")
                    mf.write(f"// ORIGINAL: {original_line}\n")
                    mf.write(f"// MUTATED:  {mutated_line}\n\n")
                    mf.write("".join(new_content))

                print(f"   ➕ Mutante creato: {mutant_file}")

    print("🎉 Generazione mutanti completata!")

def apply_single_mutant(mutant_file, working_dir):
    if not os.path.exists(mutant_file):
        print(f"❌ Mutant file non trovato: {mutant_file}")
        return False

    filename = os.path.basename(mutant_file)
    original_class = filename.split("_Mutant_")[0] + ".java"

    print(f"\n🧬 Applico mutante: {filename}")

    try:
        after_mutants = mutant_file.split("mutants" + os.sep, 1)[1]
    except IndexError:
        print("❌ Struttura dei mutanti non valida.")
        return False

    parts = after_mutants.split(os.sep)

    if len(parts) < 3:
        print("❌ Struttura troppo corta: impossibile determinare il package.")
        return False

    rel_package_path = os.path.join(*parts[1:-1])

    print(f"📁 Package rilevato: {rel_package_path}")

    dest_dir = os.path.join( working_dir, "src", "main", "java", rel_package_path)
    os.makedirs(dest_dir, exist_ok=True)

    dest_file = os.path.join(dest_dir, original_class)

    print(f"📄 Scrivo mutante in: {dest_file}")

    shutil.copy(mutant_file, dest_file)

    print(f"✅ Mutante applicato con successo!")
    return True


# === MAIN ===

def main():
    projects_csv = "environment/projects.csv"
    llm_models = [OPENROUTER_OPEN_GPT_OSS20B_MODEL_NAME, GOOGLE_GEMINI]

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
                shutil.rmtree(working_dir)

            if not defects4j_checkout(project_id, bug_id, fixed_version, working_dir):
                continue
            if not defects4j_compile(working_dir):
                continue

            for model in llm_models:
                if os.path.exists(mutants_base_dir):
                    shutil.rmtree(mutants_base_dir)
                    
                generate_mutants_for_project(working_dir, project_id, bug_id, model!=GOOGLE_GEMINI, model)

                src_dir = os.path.join(working_dir, "src/main/java")

                for root, _, files in os.walk(src_dir):
                    for file in files:
                        if file.endswith(".java"):
                            full_path = os.path.join(root, file)
                            log_java_file(full_path, working_dir)

                for root, _, files in os.walk(mutants_base_dir):
                    for mutant_file in files:
                        if os.path.exists(working_dir):
                            shutil.rmtree(working_dir)

                        if not defects4j_checkout(project_id, bug_id, fixed_version, working_dir):
                            continue

                        if not mutant_file.endswith(".java"):
                            continue

                        full_mutant_path = os.path.join(root, mutant_file)
                        mutated_class = mutant_file.split("_Mutant_")[0]

                        print(f"\n Test mutante: {mutant_file}")

                        if not apply_single_mutant(full_mutant_path, working_dir):
                            continue

                        result_base_dir = model.split("/")[0]

                        result = run_test_for_class_with_d4j(working_dir, mutated_class)

                        if not os.path.exists(f"{result_base_dir}/{RESULTS_FILE}"):
                            with open(f"{result_base_dir}/{RESULTS_FILE}", "w") as f:
                                f.write("project_id,bug_id,mutant_name,class,result\n")

                        with open(f"{result_base_dir}/{RESULTS_FILE}", "a") as f:
                            f.write(f"{project_id},{bug_id},{mutant_file},{mutated_class},{result}\n")

if __name__ == "__main__":
    main()
