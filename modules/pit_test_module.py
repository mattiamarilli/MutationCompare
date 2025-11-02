from utils import run_command
from environment.config import JAVA_HOME_11_PATH
import pandas as pd

def run_pit(working_dir, project_path, test_dir=None):
    pit_command = (
        f'JAVA_HOME=$({JAVA_HOME_11_PATH}) '
        f'mvn org.pitest:pitest-maven:mutationCoverage '
        f'-DtargetClasses="{project_path}.*" '
        f'-DtargetTests="{project_path}.*Test" '
        f'-DoutputFormats=CSV '
        f'-DexportLineCoverage=true '
        f'{f"-DtestClassesDirectory={test_dir} " if test_dir else ""}'
        f'{f"-DadditionalClasspathElements={test_dir} " if test_dir else ""}'
    )
    stdout, stderr, returncode = run_command(pit_command, cwd=working_dir)
    if returncode != 0:
        print(f"Errore nell'esecuzione di PIT: {stderr}")
        return False
    return True

def analyze_pitest_report(csv_path):
    # Legge il CSV senza intestazione e assegna nomi alle colonne
    columns = ["File", "Class", "Mutator", "Method", "Line", "Status", "Test"]
    df = pd.read_csv(csv_path, names=columns)

    print("=== STATISTICHE GENERALI ===")
    total = len(df)
    print(f"Totale mutazioni: {total}")

    # Conta gli stati
    status_counts = df["Status"].value_counts()
    for status, count in status_counts.items():
        perc = (count / total) * 100
        print(f"{status}: {count} ({perc:.2f}%)")

    print("\n=== STATISTICHE PER CLASSE ===")
    class_stats = df.groupby("Class")["Status"].value_counts().unstack(fill_value=0)
    class_stats["Total"] = class_stats.sum(axis=1)
    print(class_stats.sort_values("Total", ascending=False))

    print("\n=== STATISTICHE PER MUTATORE ===")
    mutator_stats = df.groupby("Mutator")["Status"].value_counts().unstack(fill_value=0)
    mutator_stats["Total"] = mutator_stats.sum(axis=1)
    print(mutator_stats.sort_values("Total", ascending=False))

    print("\n=== STATISTICHE PER METODO ===")
    method_stats = df.groupby("Method")["Status"].value_counts().unstack(fill_value=0)
    method_stats["Total"] = method_stats.sum(axis=1)
    print(method_stats.sort_values("Total", ascending=False))
