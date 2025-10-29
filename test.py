import subprocess
import os
import shutil
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

# ===== Aggiungi Defects4J al PATH =====
d4j_bin_path = "/Users/mattiamarilli/Universita/defects4j/framework/bin"
os.environ["PATH"] += os.pathsep + d4j_bin_path

# Imposta JAVA_HOME per JDK 11
os.environ["JAVA_HOME"] = "/usr/libexec/java_home -v 11"
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

XML_PATH = "mutations.xml"

print(os.environ.get("JAVA_HOME"))

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

def copy_mutation_report(working_dir):
    source_file = os.path.join(working_dir, "target", "pit-reports", "mutations.xml")
    dest_file = os.path.join(working_dir, "mutation.xml")

    if os.path.exists(source_file):
        shutil.copy(source_file, dest_file)
        print(f"File mutation.xml copiato in {dest_file}")
        return True
    else:
        print(f"File mutation.xml non trovato in {source_file}")
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

# Funzione principale
def main():
    project_id = "Csv"  # Esempio di progetto
    bug_id = "1"         # Esempio di bug ID
    fixed_version = "f"  # Versione post-fix
    working_dir = "/tmp/csv_1_fixed"  # Directory di lavoro

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


    print("Mutation testing completato con successo!")

if __name__ == "__main__":
    main()
