import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

# 🔹 Inserisci qui il percorso del file mutations.xml
XML_PATH = "mutations.xml"

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

if __name__ == "__main__":
    analyze_pitest_report(XML_PATH)
