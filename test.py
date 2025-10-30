import subprocess
import os
import shutil
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from config import D4J_BIN_PATH, JAVA_HOME_11_PATH
import csv
 
# ===== Aggiungi Defects4J al PATH =====
d4j_bin_path = D4J_BIN_PATH
os.environ["PATH"] += os.pathsep + d4j_bin_path

# Imposta JAVA_HOME per JDK 11
os.environ["JAVA_HOME"] = JAVA_HOME_11_PATH
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

XML_PATH = "mutations.xml"
MAJOR_RESULTS_PATH = "major_mutation_results.xml"  # Percorso per i risultati di Major
DEFECTS4J_RESULTS_PATH = "defects4j_mutation_results.xml"  # Percorso per i risultati di Defects4J

print(os.environ.get("JAVA_HOME"))
import xml.etree.ElementTree as ET

def convert_mutants_log_to_xml(log_path, xml_path):
    root = ET.Element("mutations")

    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Splitta la riga secondo il formato Major
            # Esempio: 1:LVR:0:POS:org.apache.commons.csv.ExtendedBufferedReader:46:1543:0 |==> 1
            parts = line.split(":")
            if len(parts) < 6:
                continue

            mutant_id = parts[0]
            mutator = parts[1]
            class_name = parts[4]
            line_number = parts[5]

            mutation_elem = ET.SubElement(root, "mutation")
            mutation_elem.set("id", mutant_id)
            mutation_elem.set("class", class_name)
            mutation_elem.set("line", line_number)
            mutation_elem.set("mutator", mutator)
            mutation_elem.set("status", "NO_COVERAGE")  # default se non hai i risultati dei test

    tree = ET.ElementTree(root)
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    print(f"File XML creato in {xml_path}")


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
            if len(row) != 2:
                continue
            mutant_id, status = row
            # Mappa gli stati dal CSV a quelli standard XML
            if status == "LIVE":
                xml_status = "SURVIVED"
            elif status == "FAIL":
                xml_status = "KILLED"
            elif status == "UNCOV":
                xml_status = "NO_COVERAGE"
            elif status == "EXC":
                xml_status = "ERROR"
            else:
                xml_status = "UNKNOWN"

            mutation_elem = ET.SubElement(root, "mutation")
            mutation_elem.set("id", mutant_id)
            mutation_elem.set("status", xml_status)

    tree = ET.ElementTree(root)
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    print(f"File XML creato in {xml_path} dal CSV {csv_path}")

def analyze_defects4j_report(xml_path):
    # Analizza il file XML di Defects4J per visualizzare i risultati
    tree = ET.parse(xml_path)
    root = tree.getroot()

    mutations = root.findall(".//mutation")

    total = len(mutations)
    statuses = Counter(m.get("status") for m in mutations)

    survived = statuses.get("SURVIVED", 0)
    killed = statuses.get("KILLED", 0)
    no_coverage = statuses.get("NO_COVERAGE", 0)
    total_detected = survived + killed + no_coverage

    mutation_score = (killed / total_detected * 100) if total_detected else 0

    print("=== Defects4J Mutation Testing Summary ===")
    print(f"Total mutations: {total}")
    print(f" - KILLED:       {killed}")
    print(f" - SURVIVED:     {survived}")
    print(f" - NO_COVERAGE:  {no_coverage}")
    print(f"Mutation Score:  {mutation_score:.2f}%")
    print()


def copy_mutation_report(working_dir):
    source_file = os.path.join(working_dir, "target", "pit-reports", "mutations.xml")
    dest_file = os.path.join(XML_PATH)

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
def run_pit(working_dir):
    pit_command = (
        f'JAVA_HOME=$(/usr/libexec/java_home -v 11) '
        f'mvn org.pitest:pitest-maven:mutationCoverage '
        f'-DtargetClasses="org.apache.commons.csv.*" '
        f'-DtargetTests="org.apache.commons.csv.*Test" '
        f'-DoutputFormats=XML '  # 👈 aggiunge anche CSV
        f'-DexportLineCoverage=true'

        #if the test binaries ar not in target/test-classes you must add this
        #f'-DtestClassesDirectory={test_dir}'
        #f'-DadditionalClasspathElements={test_dir}'
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

    # Funzione per eseguire Major (Mutation Testing)
def run_major(working_dir):
    major_command = f"major --project {working_dir} --output {MAJOR_RESULTS_PATH}"
    stdout, stderr, returncode = run_command(major_command, cwd=working_dir)
    if returncode != 0:
        print(f"Errore nell'esecuzione di Major: {stderr}")
        return False
    return True



# Funzione principale
def main():
    project_id = "Csv"  # Esempio di progetto
    bug_id = "1"         # Esempio di bug ID
    fixed_version = "f"  # Versione post-fix
    working_dir = "/tmp/csv_1_fixed"  # Directory di lavoro
    log_file = os.path.join(working_dir, "kill.csv")

    # Creazione della directory di lavoro se non esiste
    os.makedirs(working_dir, exist_ok=True)

    # Esecuzione del checkout
    if not defects4j_checkout(project_id, bug_id, fixed_version, working_dir):
        return

    # Compilazione del progetto
    if not defects4j_compile(working_dir):
        return

    # Esecuzione di PIT
    if not run_pit(working_dir):
        return

    # Copia del report nella working directory
    copy_mutation_report(working_dir)
    analyze_pitest_report(XML_PATH)

    # Esecuzione di Defects4J Mutation
    if not run_defects4j_mutation(working_dir):
        return

    # Analisi del report di Defects4J Mutation
    convert_kill_csv_to_xml(log_file, DEFECTS4J_RESULTS_PATH)
    analyze_defects4j_report(DEFECTS4J_RESULTS_PATH)

    print("Mutation testing completato con successo!")

if __name__ == "__main__":
    main()
