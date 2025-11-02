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


def convert_kill_csv_to_xml(csv_path, xml_path):
    root = ET.Element("mutations")

    with open(csv_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row or row[0].startswith("#"):
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
