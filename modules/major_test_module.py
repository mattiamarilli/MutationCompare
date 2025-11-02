import os
import csv
import xml.etree.ElementTree as ET
from collections import Counter
from utils import run_command

def run_defects4j_mutation(working_dir):
    stdout, stderr, returncode = run_command(f"defects4j mutation -w {working_dir}", cwd=working_dir)
    if returncode != 0:
        print(f"Errore nell'esecuzione di Defects4J Mutation: {stderr}")
        return False
    return True


def analyze_defects4j_report(csv_path):
    statuses = []

    with open(csv_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            # Salta righe vuote o commentate
            if not row or row[0].startswith("#"):
                continue

            # Pulisce e rimuove celle vuote
            row = [r.strip() for r in row if r.strip()]
            if len(row) < 2:
                continue

            mutant_id, status = row[:2]

            # Mappa gli stati Defects4J → formati standard
            status_map = {
                "LIVE": "SURVIVED",
                "FAIL": "KILLED",
                "UNCOV": "NO_COVERAGE",
                "EXC": "ERROR",
            }
            xml_status = status_map.get(status, "UNKNOWN")
            statuses.append(xml_status)

    # Conta le occorrenze degli stati
    counts = Counter(statuses)
    total = sum(counts.values())

    killed = counts.get("KILLED", 0)
    survived = counts.get("SURVIVED", 0)
    no_coverage = counts.get("NO_COVERAGE", 0)
    error = counts.get("ERROR", 0)
    unknown = counts.get("UNKNOWN", 0)

    denominator = killed + survived + error
    mutation_score = ((killed + error) / denominator * 100) if denominator > 0 else 0.0

    print("=== Defects4J Mutation Testing Summary ===")
    print(f"Total mutations: {total}")
    print(f" - KILLED:       {killed}")
    print(f" - SURVIVED:     {survived}")
    print(f" - NO_COVERAGE:  {no_coverage}")
    print(f" - ERROR:        {error}")
    print(f" - UNKNOWN:      {unknown}")
    print(f"Mutation Score:  {mutation_score:.2f}%")
    print()
