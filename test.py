import subprocess
import os
import shutil
import xml.etree.ElementTree as ET
from collections import Counter
from config import *
import csv
 
# ===== Aggiungi Defects4J al PATH =====
d4j_bin_path = D4J_BIN_PATH
os.environ["PATH"] += os.pathsep + d4j_bin_path

# Imposta JAVA_HOME per JDK 11
os.environ["JAVA_HOME"] = JAVA_HOME_11_PATH
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

XML_PATH = "mutations.xml"
DEFECTS4J_RESULTS_PATH = "defects4j_mutation_results.xml"  # Percorso per i risultati di Defects4J

print(os.environ.get("JAVA_HOME"))

os.makedirs(RESULTS_FOLDER, exist_ok=True)

def analyze_pitest_report(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Tutti i nodi <mutation>
    mutations = root.findall(".//mutation")

    total = len(mutations)
    statuses = Counter(m.get("status") for m in mutations)

    survived = statuses.get("SURVIVED", 0)
    killed = statuses.get("KILLED", 0)
    no_coverage = statuses.get("NO_COVERAGE", 0)
    total_detected = survived + killed + no_coverage

    mutation_score = (killed / total_detected * 100) if total_detected else 0

    print("=== PIT Mutation Testing Summary ===")
    print(f"Total mutations: {total}")
    print(f" - KILLED:       {killed}")
    print(f" - SURVIVED:     {survived}")
    print(f" - NO_COVERAGE:  {no_coverage}")
    print(f"Mutation Score:  {mutation_score:.2f}%")
    print()


def convert_kill_csv_to_xml(csv_path, xml_path):
    root = ET.Element("mutations")

    with open(csv_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row or row[0].startswith("#"):
                continue

            # Alcuni CSV possono avere spazi o tab
            row = [r.strip() for r in row if r.strip()]
            if len(row) < 2:
                continue

            mutant_id, status = row[:2]

            # Mappa gli stati dal CSV a quelli XML standard
            status_map = {
                "LIVE": "SURVIVED",
                "FAIL": "KILLED",
                "UNCOV": "NO_COVERAGE",
                "EXC": "ERROR",
            }
            xml_status = status_map.get(status, "UNKNOWN")

            mutation_elem = ET.SubElement(root, "mutation")
            mutation_elem.set("id", mutant_id)
            mutation_elem.set("status", xml_status)

    tree = ET.ElementTree(root)
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    print(f"File XML creato in {xml_path} dal CSV {csv_path}")


def analyze_defects4j_report(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    mutations = root.findall(".//mutation")

    total = len(mutations)
    statuses = Counter(m.get("status") for m in mutations)

    killed = statuses.get("KILLED", 0)
    survived = statuses.get("SURVIVED", 0)
    no_coverage = statuses.get("NO_COVERAGE", 0)
    error = statuses.get("ERROR", 0)
    unknown = statuses.get("UNKNOWN", 0)

    # Formula standard Defects4J
    denominator = killed + survived + error
    mutation_score = ((killed + error)/ denominator * 100) if denominator > 0 else 0.0

    print("=== Defects4J Mutation Testing Summary ===")
    print(f"Total mutations: {total}")
    print(f" - KILLED:       {killed}")
    print(f" - SURVIVED:     {survived}")
    print(f" - NO_COVERAGE:  {no_coverage}")
    print(f" - ERROR:        {error}")
    print(f" - UNKNOWN:      {unknown}")
    print(f"Mutation Score:  {mutation_score:.2f}%")
    print()


def copy_mutation_report(working_dir, dest_file):
    source_file = os.path.join(working_dir, "target", "pit-reports", "mutations.xml")

    if os.path.exists(source_file):
        shutil.copy(source_file, dest_file)
        print(f"File mutations.xml copiato in {dest_file}")
        return True
    else:
        print(f"File mutations.xml non trovato in {source_file}")
        return False


# Funzione per eseguire comandi shell
def run_command(command, cwd=None):
    result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


# Funzione per eseguire il checkout di un progetto
def defects4j_checkout(project_id, bug_id, fixed_version, working_dir):
    checkout_command = f"defects4j checkout -p {project_id} -v {bug_id}{fixed_version} -w {working_dir}"
    stdout, stderr, returncode = run_command(checkout_command)
    if returncode != 0:
        print(f"Errore nel checkout del progetto: {stderr}")
        return False
    return True


# Funzione per compilare il progetto
def defects4j_compile(working_dir):
    compile_command = "defects4j compile"
    stdout, stderr, returncode = run_command(compile_command, cwd=working_dir)
    if returncode != 0:
        print(f"Errore nella compilazione del progetto: {stderr}")
        return False
    return True

# Funzione per eseguire PIT
def run_pit(working_dir, project_id, test_dir=None):
    
    pit_command = (
        f'JAVA_HOME=$({JAVA_HOME_11_PATH}) '
        f'mvn org.pitest:pitest-maven:mutationCoverage '
        f'-DtargetClasses="org.apache.commons.{project_id}.*" '
        f'-DtargetTests="org.apache.commons.{project_id}.*Test" '
        f'-DoutputFormats=XML '  # 👈 aggiunge anche CSV
        f'-DexportLineCoverage=true'

        #if the test binaries ar not in target/test-classes you must add this
        f'{f" -DtestClassesDirectory={test_dir} " if test_dir else ""}'
        f'{f" -DadditionalClasspathElements={test_dir} " if test_dir else ""}'
    )
    stdout, stderr, returncode = run_command(pit_command, cwd=working_dir)
    if returncode != 0:
        print(f"Errore nell'esecuzione di PIT: {stderr}")
        return False
    return True


# Funzione per eseguire Defects4J Mutation Testing
def run_defects4j_mutation(working_dir):
    mutation_command = f"defects4j mutation -w {working_dir}"
    stdout, stderr, returncode = run_command(mutation_command, cwd=working_dir)
    if returncode != 0:
        print(f"Errore nell'esecuzione di Defects4J Mutation: {stderr}")
        return False
    return True


# Funzione principale
def main():
    projects_csv = "projects.csv"

    with open(projects_csv, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            project_id    = row['project_id']
            bug_id        = row['bug_id']
            fixed_version = row['fixed_version']
            id_dir        = row['id_dir']
            test_dir      = row['test_dir']

            working_dir = f"/tmp/{project_id.lower()}_{bug_id}_{fixed_version}"
            log_file = os.path.join(working_dir, "kill.csv")

            os.makedirs(working_dir, exist_ok=True)

            print(f"\n=== Elaborazione {project_id} bug {bug_id} ===")

            if not defects4j_checkout(project_id, bug_id, fixed_version, working_dir):
                print(f"Checkout fallito per {project_id} bug {bug_id}")
                continue

            if not defects4j_compile(working_dir):
                print(f"Compilazione fallita per {project_id} bug {bug_id}")
                continue

            if not run_pit(working_dir, id_dir, test_dir):
                print(f"PIT fallito per {project_id} bug {bug_id}")
                continue

            project_pit_res_path = os.path.join(RESULTS_FOLDER,f"{project_id.lower()}_{XML_PATH}")
            copy_mutation_report(working_dir, project_pit_res_path)
            analyze_pitest_report(project_pit_res_path)

            if not run_defects4j_mutation(working_dir):
                print(f"Defects4J mutation fallito per {project_id} bug {bug_id}")
                continue

            project_df4j_res_path = os.path.join(RESULTS_FOLDER,f"{project_id.lower()}_{DEFECTS4J_RESULTS_PATH}")
            convert_kill_csv_to_xml(log_file, project_df4j_res_path)
            analyze_defects4j_report(project_df4j_res_path)

            print(f"Mutation testing completato per {project_id} bug {bug_id}")


if __name__ == "__main__":
    main()
