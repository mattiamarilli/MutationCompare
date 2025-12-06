import os
import shutil
from modules.defects4j_module import defects4j_compile, defects4j_test_with_timeout
from llm.llm_mutation_engine_module import LLMMutationEngine

def run_test_for_class_with_d4j(working_dir, mutated_class):
    test_name = f"{mutated_class}Test"
    print(f"🧪 Eseguo test: {test_name}")

    defects4j_compile(working_dir)

    result = defects4j_test_with_timeout(working_dir)

    # Timeout ⇒ mutante ucciso
    if result == "timeout":
        print("⏳ Timeout (>30s) → Mutante ucciso")
        return "killed"

    failing_tests_file = os.path.join(working_dir, "failing_tests")
    print(failing_tests_file)

    if os.path.exists(failing_tests_file) and os.path.getsize(failing_tests_file) > 0:
        print("💀 Mutante ucciso (failing_tests non vuoto)")
        return "killed"
    else:
        print("Mutante sopravvissuto")
        return "Survived"


def log_java_file(java_file_path, working_dir):
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