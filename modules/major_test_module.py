import os
import csv
import xml.etree.ElementTree as ET
from collections import Counter
from utils import run_command
import pandas as pd

def run_defects4j_mutation(working_dir):
    stdout, stderr, returncode = run_command(f"defects4j mutation -w {working_dir}", cwd=working_dir)
    if returncode != 0:
        print(f"Errore nell'esecuzione di Defects4J Mutation: {stderr}")
        return False
    return True


def analyze_defects4j_report(csv_path, mutants_log_path):
    # --- Legge i risultati dal CSV ---
    mutants = []
    print("=== Defects4j mutation results ===")
    with open(csv_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row or not row[0].isdigit():
                continue
            row = [r.strip() for r in row if r.strip()]
            if len(row) < 2:
                continue

            mutant_id, status = row[:2]
            status_map = {
                "LIVE": "SURVIVED",
                "FAIL": "KILLED",
                "UNCOV": "NO_COVERAGE",
                "EXC": "ERROR",
                "TIMED_OUT": "TIMED_OUT"
            }
            mapped_status = status_map.get(status, status)
            mutants.append({
                "ID": mutant_id,
                "Status": mapped_status,
                "Class": None,
                "Mutator": None,
                "Method": None,
                "Line": None
            })

    # --- 2️⃣ Se esiste mutants.log, arricchisce con info extra ---
    if mutants_log_path and os.path.exists(mutants_log_path):
        mutant_info = {}
        with open(mutants_log_path) as f:
            for line in f:
                line = line.strip()
                if not line or not line[0].isdigit():
                    continue

                try:
                    parts = line.split(":")
                    mutant_id   = parts[0]
                    mutator_type = parts[1] if len(parts) > 1 else "?"
                    class_method = parts[4] if len(parts) > 4 else "?"
                    line_number  = parts[5] if len(parts) > 5 else "?"

                    if "@" in class_method:
                        class_name, method_name = class_method.split("@", 1)
                    else:
                        class_name, method_name = class_method, "unknown"

                    class_name = class_name.replace("/", ".")
                    method_name = method_name.replace("()", "")

                    mutant_info[mutant_id] = {
                        "Class": class_name,
                        "Method": method_name,
                        "Line": line_number,
                        "Mutator": mutator_type
                    }

                except Exception as e:
                    print(f"[WARN] Errore parsing linea: {line} → {e}")
                    continue

        for m in mutants:
            extra = mutant_info.get(m["ID"])
            if extra:
                m.update(extra)

    # --- 3️⃣ Crea il DataFrame ---
    df = pd.DataFrame(mutants)

    print("=== STATISTICHE GENERALI ===")
    total = len(df)
    print(f"Totale mutazioni: {total}")

    status_counts = df["Status"].value_counts()
    for status, count in status_counts.items():
        perc = (count / total) * 100
        print(f"{status}: {count} ({perc:.2f}%)")

    # --- 4️⃣ Statistiche per CLASSE ---
    if df["Class"].notna().any():
        print("\n=== STATISTICHE PER CLASSE ===")
        class_stats = df.groupby("Class")["Status"].value_counts().unstack(fill_value=0)
        class_stats["Total"] = class_stats.sum(axis=1)
        print(class_stats.sort_values("Total", ascending=False))

    # --- 5️⃣ Statistiche per MUTATORE ---
    if df["Mutator"].notna().any():
        print("\n=== STATISTICHE PER MUTATORE ===")
        mutator_stats = df.groupby("Mutator")["Status"].value_counts().unstack(fill_value=0)
        mutator_stats["Total"] = mutator_stats.sum(axis=1)
        print(mutator_stats.sort_values("Total", ascending=False))

    # --- 6️⃣ Statistiche per METODO ---
    if df["Method"].notna().any():
        print("\n=== STATISTICHE PER METODO ===")
        method_stats = df.groupby("Method")["Status"].value_counts().unstack(fill_value=0)
        method_stats["Total"] = method_stats.sum(axis=1)
        print(method_stats.sort_values("Total", ascending=False))

    # --- 7️⃣ Calcolo Mutation Score ---
    counts = Counter(df["Status"])
    killed = counts.get("KILLED", 0)
    survived = counts.get("SURVIVED", 0)
    error = counts.get("ERROR", 0)
    denominator = killed + survived + error
    mutation_score = ((killed + error) / denominator * 100) if denominator > 0 else 0.0

    print(f"\nMutation Score: {mutation_score:.2f}%\n")