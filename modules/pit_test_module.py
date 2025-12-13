from utils import run_command
from environment.config import JAVA_HOME_11_PATH
import pandas as pd

def run_pit(working_dir, project_path, test_dir=None):
    """
    Run PIT mutation testing on a given project using Maven.

    Args:
        working_dir (str): Project root directory.
        project_path (str): Fully-qualified package name to target.
        test_dir (str, optional): Optional directory for test classes.

    Returns:
        bool: True if PIT ran successfully, False otherwise.
    """
    # Construct the PIT Maven command
    pit_command = (
        f'JAVA_HOME=$({JAVA_HOME_11_PATH}) '
        f'mvn org.pitest:pitest-maven:mutationCoverage '
        f'-DtargetClasses="{project_path}.*" '
        f'-DtargetTests="{project_path}.*Test" '
        f'-DoutputFormats=CSV '  # Export results as CSV
        f'-DexportLineCoverage=true '  # Include line coverage info
        f'{f"-DtestClassesDirectory={test_dir} " if test_dir else ""}'  # Optional test dir
        f'{f"-DadditionalClasspathElements={test_dir} " if test_dir else ""}'  # Optional classpath
    )

    # Execute the command in the working directory
    stdout, stderr, returncode = run_command(pit_command, cwd=working_dir)

    if returncode != 0:
        # Log error if PIT execution fails
        print(f"Error running PIT: {stderr}")
        return False

    print("PIT executed successfully")
    return True


def analyze_pitest_report(csv_path):
    """
    Analyze a PIT mutation testing CSV report and print statistics.

    Args:
        csv_path (str): Path to the PIT CSV report.
    """
    # Read CSV without header and assign column names
    columns = ["File", "Class", "Mutator", "Method", "Line", "Status", "Test"]
    df = pd.read_csv(csv_path, names=columns)

    # --- 1. General statistics ---
    print("=== GENERAL STATISTICS ===")
    total = len(df)
    print(f"Total mutants: {total}")

    # Count each status type
    status_counts = df["Status"].value_counts()
    for status, count in status_counts.items():
        perc = (count / total) * 100
        print(f"{status}: {count} ({perc:.2f}%)")

    # # --- 2. Statistics per class ---
    # print("\n=== STATISTICS PER CLASS ===")
    # class_stats = df.groupby("Class")["Status"].value_counts().unstack(fill_value=0)
    # class_stats["Total"] = class_stats.sum(axis=1)  # Total mutants per class
    # print(class_stats.sort_values("Total", ascending=False))

    # # --- 3. Statistics per mutator ---
    # print("\n=== STATISTICS PER MUTATOR ===")
    # mutator_stats = df.groupby("Mutator")["Status"].value_counts().unstack(fill_value=0)
    # mutator_stats["Total"] = mutator_stats.sum(axis=1)  # Total mutants per mutator
    # print(mutator_stats.sort_values("Total", ascending=False))

    # # --- 4. Statistics per method ---
    # print("\n=== STATISTICS PER METHOD ===")
    # method_stats = df.groupby("Method")["Status"].value_counts().unstack(fill_value=0)
    # method_stats["Total"] = method_stats.sum(axis=1)  # Total mutants per method
    # print(method_stats.sort_values("Total", ascending=False))
