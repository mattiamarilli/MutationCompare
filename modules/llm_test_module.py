import os
import shutil
from modules.defects4j_module import defects4j_compile, defects4j_test_with_timeout
from llm.llm_mutation_engine_module import LLMMutationEngine

def run_test_for_class_with_d4j(working_dir, mutated_class):
    """
    Run Defects4J tests for the given class and determine
    whether the mutant is killed or survived.
    """
    test_name = f"{mutated_class}Test"
    print(f"Running test: {test_name}")

    try:
        compiled = defects4j_compile(working_dir)
    except Exception as e:
        return "build_failed"
    
    if not compiled:
        return "build_failed"

    result = defects4j_test_with_timeout(working_dir)

    if result == "timeout":
        print("Timeout (>30s) - mutant killed")
        return "timeout"

    
    failing_tests_file = os.path.join(working_dir, "failing_tests")
    print(failing_tests_file)
    print(f"Checking: {failing_tests_file}")

    # If failing_tests is not empty, the mutant is killed
    if os.path.exists(failing_tests_file) and os.path.getsize(failing_tests_file) > 0:
        print("Mutant killed (failing_tests file is not empty)")
        return "killed"
    else:
        print("Mutant survived")
        return "survived"


def ensure_dir(path):
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)


def generate_mutants_for_project(working_dir, project_id, bug_id, model=""):
    """
    Generate mutants for the entire project using the LLM mutation engine.
    """

    src_dir = os.path.join(working_dir, "src", "main", "java")
    if not os.path.exists(src_dir):
        src_dir = os.path.join(working_dir, "src", "java")

    base_mutants_dir = os.path.join("mutants", f"{project_id}_{bug_id}")

    ensure_dir(base_mutants_dir)

    engine = LLMMutationEngine(model)

    print(f"Generating mutants for: {src_dir}")

    for root, _, files in os.walk(src_dir):
        for file in files:
            if not file.endswith(".java"):
                continue

            java_path = os.path.join(root, file)
            rel_path = os.path.relpath(java_path, src_dir)
            rel_folder = os.path.dirname(rel_path)

            target_dir = os.path.join(base_mutants_dir, rel_folder)
            ensure_dir(target_dir)

            print(f"Analyzing Java file: {rel_path}")

            # Generate mutations via LLM
            mutations = engine.mutate_java_file(java_path)

            if not mutations:
                print("No mutations generated")
                continue

            print(f"{len(mutations)} mutations generated - saving mutants to {target_dir}")

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

                print(f"Mutant created: {mutant_file}")

    print("Mutant generation completed")


def apply_single_mutant(mutant_file, working_dir):
    """
    Replace the original Java class with the mutated version.
    """
    if not os.path.exists(mutant_file):
        print(f"Mutant file not found: {mutant_file}")
        return False

    filename = os.path.basename(mutant_file)
    original_class = filename.split("_Mutant_")[0] + ".java"

    print(f"Applying mutant: {filename}")

    # Extract relative package path
    try:
        after_mutants = mutant_file.split("mutants" + os.sep, 1)[1]
    except IndexError:
        print("Invalid mutant path structure")
        return False

    parts = after_mutants.split(os.sep)

    if len(parts) < 3:
        print("Path too short, cannot determine package")
        return False

    rel_package_path = os.path.join(*parts[1:-1])
    print(f"Detected package: {rel_package_path}")

    src_dir = os.path.join(working_dir, "src", "main", "java")
    if not os.path.exists(src_dir):
        src_dir = os.path.join(working_dir, "src", "java")

    dest_dir = os.path.join(
        src_dir, rel_package_path
    )
    os.makedirs(dest_dir, exist_ok=True)

    dest_file = os.path.join(dest_dir, original_class)
    print(f"Writing mutant to: {dest_file}")

    shutil.copy(mutant_file, dest_file)

    print("Mutant successfully applied")
    return True
