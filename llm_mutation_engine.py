import json
import re
import requests
from google import genai
from environment.config import GOOGLE_AI_API_KEY, OPENROUTER_API_KEY


class LLMMutationEngine:
    MUTATORS_DESCRIPTION = """
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

    def __init__(self, open_router = False, model = ""):
        self.is_open_router = open_router
        if open_router == False:
            self.client = genai.Client(api_key=GOOGLE_AI_API_KEY)
        else:
            self.model = model

    def mutate_java_file(self, java_file_path: str):
        try:
            with open(java_file_path, "r") as f:
                java_class = f.read()
        except Exception as e:
            print(f"❌ Errore nel leggere il file {java_file_path}: {e}")
            return []

        return self._mutate_java_class(java_class)

    # === NEW: rimuove commenti singoli e multilinea ===
    def _remove_comments(self, java_class: str) -> str:
        # Rimuovi commenti multilinea
        java_class = re.sub(r"/\*[\s\S]*?\*/", "", java_class, flags=re.MULTILINE)

        # Rimuovi commenti singoli
        java_class = re.sub(r"//.*", "", java_class)

        return java_class

    def _mutate_java_class(self, java_class: str):
        # 🚀 PULIZIA COMMENTI QUI
        java_class_clean = self._remove_comments(java_class)

        valid_lines = {line.strip() for line in java_class_clean.split("\n") if line.strip()}

        prompt = f"""
            Generate exactly 3 of the possible mutations of different lines in the following Java class 
            for PIT mutation testing.
            Use only the following mutators:
            {self.MUTATORS_DESCRIPTION}

            Each mutation MUST modify exactly ONE LINE of the following original Java class:
            {java_class_clean}

            RULES:
            - Mutate ONLY ONE line from the class above.
            - Do NOT modify method or class declarations.
            - Do NOT add new operators; mutate only existing ones.
            - The mutated line MUST differ from the original.
            - Do not substitute variables with function calls like Integer.compare or similar.
            - Output MUST contain ONLY JSON objects, one per line:
              {'{"original_code": "<original_code>", "mutated_code": "<mutated_code>"}'}
            - If <original_code> does NOT exist in the class, skip mutation.
            - No commentary, no text, only JSON objects.
        """

        if self.is_open_router == True:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": f"{self.model}",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                })
            )
            text = response.json()["choices"][0]["message"]["content"].strip()
        else:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )
            text = response.text.strip()

        new_mutations = []

        for line in text.split("\n"):
            try:
                mutation_json = json.loads(line)

                original = mutation_json.get("original_code", "").strip()
                mutated = mutation_json.get("mutated_code", "").strip()

                if original not in valid_lines:
                    continue

                new_mutations.append({
                    "original_code": original,
                    "mutated_code": mutated
                })

            except Exception:
                continue

        return new_mutations
