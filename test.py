import subprocess
import os

# ===== Aggiungi Defects4J al PATH =====
d4j_bin_path = "/Users/mattiamarilli/Universita/defects4j/framework/bin"
os.environ["PATH"] += os.pathsep + d4j_bin_path

# Imposta JAVA_HOME per JDK 11
os.environ["JAVA_HOME"] = "/usr/libexec/java_home -v 11"
os.environ["PATH"] = os.environ["JAVA_HOME"] + "/bin:" + os.environ["PATH"]

print(os.environ.get("JAVA_HOME"))

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
        f'-DtargetClasses="org.apache.commons.lang3.*" '
        f'-DtargetTests="org.apache.commons.lang3.AnnotationUtilsTest.class" '
        f'-DexportLineCoverage=true'
    )
    stdout, stderr, returncode = run_command(pit_command, cwd=working_dir)
    if returncode != 0:
        print(f"Errore nell'esecuzione di PIT: {stderr}")
        return False
    return True

# Funzione principale
def main():
    project_id = "Lang"  # Esempio di progetto
    bug_id = "1"         # Esempio di bug ID
    fixed_version = "f"  # Versione post-fix
    working_dir = "/tmp/lang_1_fixed"  # Directory di lavoro

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

    print("Mutation testing completato con successo!")

if __name__ == "__main__":
    main()
