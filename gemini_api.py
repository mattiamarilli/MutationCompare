from google import genai
import json

client = genai.Client(api_key="")

mutators_description = """
- AOR (Arithmetic Operator Replacement): +, -, *, /, %
- LOR (Logical Operator Replacement): &&, ||
- ROR (Relational Operator Replacement): <, <=, >, >=, ==, !=
- UOI (Unary Operator Insertion/Deletion): ++, --, !
- COI (Conditional Operator Inversion): invert conditions in if/loops
- PRV (Primitive Return Values): change return values of primitives
- SAI (Statement Removal/Replacement): modify or remove assignment/return statements
- LVR (Literal Value Replacement): replace numeric or boolean literals
- NPE (Null Pointer Injection): replace variables with null
- MTD (Method Call Replacement): replace a method call with another valid one
"""

def mutate_java_class(java_class: str, memory_mutations, num_mutations=3):

    valid_lines = {line.strip() for line in java_class.split("\n") if line.strip()}

    previous_mutations_str = (
        "\n".join(
            json.dumps({"original_code": orig, "mutated_code": mut})
            for (orig, mut) in memory_mutations
        )
        if memory_mutations
        else "None so far."
    )

    prompt = f"""
        Generate ALL the possible mutations of different lines in the following Java class for PIT mutation testing.
        Use only the following mutators:
        {mutators_description}
        
        Each mutation MUST modify exactly ONE LINE of the following original Java class:
        {java_class}
        
        RULES:
        - Mutate ONLY ONE line from the class above.
        - Do NOT modify method or class declarations.
        - Do NOT add new operators; mutate only existing ones.
        - The mutated line MUST differ from the original.
        - Each mutation must be new (not previously generated).
        - Do not substitute variables with function calls like Integer.compare or something like this;
        - Return exactly one mutation per line:
        { '{"original_code": "<original_code>", "mutated_code": "<mutated_code>"}' }
        - If <original_code> does NOT exist in the class, skip mutation.
        
        Start output now (NO commentary, ONLY JSON objects, one per line):
        """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    text = response.text.strip()

    new_mutations = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        try:
            mutation_json = json.loads(line)
            original = mutation_json.get("original_code", "").strip()
            mutated = mutation_json.get("mutated_code", "").strip()

            if original not in valid_lines:
                continue

            pair = (original, mutated)
            if pair not in memory_mutations:
                new_mutations.append(line)
                memory_mutations.add(pair)

        except Exception:
            continue

    return new_mutations


# ================================================================
# ESEMPIO DI UTILIZZO
# ================================================================

memory_mutations = set()

java_code = """
class Calculator {
    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return a - b;
    }
}
"""

mutations = mutate_java_class(java_code, memory_mutations, num_mutations=100)

print(f"\n# Mutazioni generate: {len(mutations)} mutations")

print("\nMutazioni generate:")
for m in mutations:
    print(m)
