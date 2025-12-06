import json
from transformers import AutoModelForCausalLM, CodeLlamaTokenizer, BitsAndBytesConfig
import torch

print("CUDA disponibile:", torch.cuda.is_available())

model_name = "codellama/CodeLlama-7b-hf"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True
)

tokenizer = CodeLlamaTokenizer.from_pretrained(model_name)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map={"": "cuda:0"},
    quantization_config=bnb_config
)

# Lista completa dei mutatori PIT
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
Generate {num_mutations} mutations of different lines in the following Java class for PIT mutation testing.
Use only the following mutators:
{mutators_description}

PREVIOUS MUTATIONS:
{previous_mutations_str}

Each mutation MUST modify exactly ONE LINE of the following original Java class:
{java_class}

- Find a mutable lines in the java code above i.e. NOT method or class declarations.
- Applpy all th epossible mutation to that line.
- Then find another mutable line and repeat. and do the same.
- if there are no more mutable lines in the above java cide to mautate, stop.

RULES:
- Mutate ONLY ONE line if the class above.
- Do NOT modify method or class declarations.
- Do NOT add operators, mutate only existing ones.
- The mutated line MUST be different from the original.
- Each mutation must be different from previous ones.
- Return exactly {num_mutations} JSON objects, one per line:
{{"original_code": "<original_code>", "mutated_code": "<mutated_code>" (mutation!)}}
- No extra text.
- if the <original_code> doeseen't exist in the class above skip outputting that mutation.

Start output now:
"""

    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=1000,
        pad_token_id=tokenizer.eos_token_id
    )

    prompt_len = inputs["input_ids"].shape[1]
    generated_text = tokenizer.decode(outputs[0][prompt_len:], skip_special_tokens=True).strip()

    # Parsiamo JSON e filtriamo duplicati
    new_mutations = []
    for line in generated_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            mutation_json = json.loads(line)
            original = mutation_json.get("original_code", "").strip()
            mutated = mutation_json.get("mutated_code", "").strip()

            # ignore invalid
            if original not in valid_lines:
                continue

            signature = (original, mutated)

            # filter duplicates properly
            if signature not in memory_mutations:
                new_mutations.append(line)
                memory_mutations.add(signature)
        except:
            continue

    return new_mutations

# Esempio
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

iteration = 1
while True:
    print(f"\nIterazione {iteration}")
    mutations = mutate_java_class(java_code, memory_mutations, num_mutations=3)
    if not mutations:
        print("⚠ Nessuna nuova mutazione disponibile, termine.")
        break
    print(f"Mutazioni generate ({mutations}:")
    iteration += 1

# Stampa finale ordinata
print("\nTutte le mutazioni generate:")
for i, m in enumerate(memory_mutations, 1):
    print(f"{i}: {m}")
