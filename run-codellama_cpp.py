import json
from llama_cpp import Llama

# ====== 1️⃣ Caricamento modello GGUF ======
llm = Llama.from_pretrained(
    repo_id="TheBloke/CodeLlama-7B-Instruct-GGUF",
    filename="codellama-7b-instruct.Q2_K.gguf",
    n_gpu_layers=50,
)

# ====== 2️⃣ Descrizione dei mutatori ======
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

# ====== 3️⃣ Funzione per generare mutazioni ======
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
Generate {num_mutations} mutations of different lines in the following Java class for PIT mutation testing.
Use only the following mutators:
{mutators_description}

PREVIOUS MUTATIONS:
{previous_mutations_str}

Each mutation MUST modify exactly ONE LINE of the following original Java class:
{java_class}

RULES:
- Mutate ONLY ONE line at a time.
- Do NOT modify method or class declarations.
- Do NOT add operators, mutate only existing ones.
- The mutated line MUST be different from the original.
- Each mutation must be different from previous ones.
- Return exactly {num_mutations} JSON objects, one per line:
{{"original_code": "<original_code>", "mutated_code": "<mutated_code>"}}
- No extra text.

Start output now:
"""

    # ====== 4️⃣ Generazione testo con llama_cpp ======
    response = llm(
        prompt,
        max_tokens=800,
        temperature=0.0,
        stop=["\n\n"]
    )

    # ====== 5️⃣ Estrazione testo generato ======
    try:
        generated_text = response['choices'][0]['text'].strip()
    except (KeyError, IndexError):
        print("⚠ Errore: output del modello non valido")
        return []

    # ====== 6️⃣ Parsiamo JSON e filtriamo duplicati ======
    new_mutations = []
    for line in generated_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            mutation_json = json.loads(line)
            original = mutation_json.get("original_code", "").strip()
            mutated = mutation_json.get("mutated_code", "").strip()

            if original not in valid_lines:
                continue

            signature = (original, mutated)
            if signature not in memory_mutations:
                new_mutations.append(line)
                memory_mutations.add(signature)
        except json.JSONDecodeError:
            continue

    return new_mutations

# ====== 7️⃣ Esempio di utilizzo ======
memory_mutations = set()

java_code = """
    private static boolean isLineBreak(char c) {
        return c == '\n' || c == '\r';
    }
"""

iteration = 1
while True:
    print(f"\nIterazione {iteration}")
    mutations = mutate_java_class(java_code, memory_mutations, num_mutations=3)
    if not mutations:
        print("⚠ Nessuna nuova mutazione disponibile, termine.")
        break
    print(f"Mutazioni generate: {mutations}")
    iteration += 1

print("\nTutte le mutazioni generate:")
for i, m in enumerate(memory_mutations, 1):
    print(f"{i}: {m}")
