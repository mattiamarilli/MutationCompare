import os
import csv
import xml.etree.ElementTree as ET
from collections import Counter
from utils import run_command
import pandas as pd
from pathlib import Path
from collections import defaultdict

"""
Estrae i nomi completamente qualificati delle classi compilate (.class)
dalla cartella target/classes/<project_path>
e li salva nel file 'instrument_classes'.
"""
def set_instrument_classes(target_dir, project_path, instrument_classes_path):
    target_path = Path(target_dir)
    if not target_path.exists():
        print(f"Directory target non trovata: {target_dir}")
        return []

    class_names = []
    for root, _, files in os.walk(target_path):
        for f in files:
            if f.endswith(".class") and "$" not in f and "package-info" not in f:
                full_path = Path(root) / f
                rel_path = full_path.relative_to(target_path)
                fqcn = project_path + "." + str(rel_path).replace(os.sep, ".").replace(".class", "")
                class_names.append(fqcn)

    if not class_names:
        return []
    
    # Scrivi il file instrument_classes
    with open(instrument_classes_path, "w") as f:
        for cls in sorted(class_names):
            f.write(cls + "\n")

    return True


def run_defects4j_mutation(working_dir, project_path):
    target_dir = os.path.join(working_dir, "target", "classes", *project_path.split('.'))
    instrument_file = os.path.join(working_dir, "instrument_classes")
    
    if not set_instrument_classes(target_dir, project_path, instrument_file):
        print(f"Nessuna classe trovata in {target_dir}")
        return False
    
    # Esegui defects4j mutation
    command = f"defects4j mutation -w {working_dir} -i {instrument_file}"
    stdout, stderr, returncode = run_command(command, cwd=working_dir)
    if returncode != 0:
        print(f"Errore nell'esecuzione di Defects4J Mutation:\n{stderr}")
        return False
    
    return True


def analyze_defects4j_report(csv_path, mutants_log_path):
    # --- 1 Legge i risultati dal CSV ---
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
                "TIME": "TIMED_OUT"
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

    # --- 2️ Se esiste mutants.log, arricchisce con info extra ---
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

    # --- 3️ Crea il DataFrame ---
    df = pd.DataFrame(mutants)

    print("=== STATISTICHE GENERALI ===")
    total_mutants = len(df)
    print(f"Totale mutazioni: {total_mutants}")

    status_counts = df["Status"].value_counts()
    for status, count in status_counts.items():
        perc = (count / total_mutants) * 100
        print(f"{status}: {count} ({perc:.2f}%)")

    # --- 4️ Statistiche per CLASSE ---
    if df["Class"].notna().any():
        print("\n=== STATISTICHE PER CLASSE ===")
        class_stats = df.groupby("Class")["Status"].value_counts().unstack(fill_value=0)
        class_stats["Total"] = class_stats.sum(axis=1)
        print(class_stats.sort_values("Total", ascending=False))

    # --- 5️ Statistiche per MUTATORE ---
    if df["Mutator"].notna().any():
        print("\n=== STATISTICHE PER MUTATORE ===")
        mutator_stats = df.groupby("Mutator")["Status"].value_counts().unstack(fill_value=0)
        mutator_stats["Total"] = mutator_stats.sum(axis=1)
        print(mutator_stats.sort_values("Total", ascending=False))

    # --- 6️ Statistiche per METODO ---
    if df["Method"].notna().any():
        print("\n=== STATISTICHE PER METODO ===")
        method_stats = df.groupby("Method")["Status"].value_counts().unstack(fill_value=0)
        method_stats["Total"] = method_stats.sum(axis=1)
        print(method_stats.sort_values("Total", ascending=False))

    # --- 7️ Calcolo Mutation Score corretto ---
    counts = Counter(df["Status"])
    killed = counts.get("KILLED", 0) + counts.get("ERROR", 0) + counts.get("TIMED_OUT", 0)
    time_out = counts.get("TIME_OUT", 0)
    no_coverage = counts.get("NO_COVERAGE", 0)

    mutants_covered = total_mutants - no_coverage
    killed += time_out
    mutation_score_covered = (killed / mutants_covered * 100) if mutants_covered > 0 else 0.0
    mutation_score_total = (killed / total_mutants * 100) if total_mutants > 0 else 0.0

    export_pit_like(df, csv_path)
    print(f"Mutation score: {mutation_score_covered:.1f}% ({mutation_score_total:.1f}%)\n")


def export_pit_like(df, csv_path):
    """Esporta un file CSV nello stile PIT mutation testing,
    caricando automaticamente testMap.csv e covMap.csv dalla stessa cartella di csv_path."""

    base_dir = os.path.dirname(csv_path)
    test_map_path = os.path.join(base_dir, "testMap.csv")
    cov_map_path  = os.path.join(base_dir, "covMap.csv")

    # 1) Carica testMap.csv
    test_names = {}
    if os.path.exists(test_map_path):
        with open(test_map_path, newline='') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    test_no, test_name = row[:2]
                    test_names[test_no] = test_name

    # 2) Carica covMap.csv
    mutant_tests = defaultdict(set)
    if os.path.exists(cov_map_path):
        with open(cov_map_path, newline='') as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    test_no, mutant_no = row[:2]
                    mutant_tests[mutant_no].add(test_no)

    # 3) Aggrega DataFrame per mutante + linea + mutatore + status
    grouped = df.groupby(["ID", "Class", "Mutator", "Method", "Line", "Status"], dropna=False)

    rows = []

    for (mutant_id, class_name, mutator, method, line, status), group in grouped:
        class_name = class_name or "UnknownClass"
        file_name = class_name.split(".")[-1] + ".java"
        mutator = mutator or "UnknownMutator"
        method = method or "unknown"
        line = line or "?"
        status = status

        test_list = mutant_tests.get(str(mutant_id), set())
        if not test_list:
            test_list = {"none"}

        for t in sorted(test_list):
            rows.append([file_name, class_name, mutator, method, line, status, test_names.get(t, t)])

    # 4) Scrivi CSV
    out_path = os.path.join(base_dir, "mutants_major.csv")
    with open(out_path, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["File", "Class", "Mutator", "Method", "Line", "Status", "Test"])
        writer.writerows(rows)

    print(f"Creato file PIT-like: {out_path}")