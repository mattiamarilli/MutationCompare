import json
import re
import requests
from environment.config import OPENROUTER_API_KEY

class LLMMutationEngine:
    """
    Engine to generate mutations of Java classes using an LLM.

    Attributes:
        MUTATORS_DESCRIPTION (str): Description of available mutators for PIT mutation testing.
        is_open_router (bool): Whether to use OpenRouter API instead of Google GenAI.
        client / model: API client or model name depending on the chosen engine.
    """
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

    def __init__(self, model=""):
        """
        Initialize the mutation engine.
        Args:
            model (str): Model name to use with OpenRouter.
        """
        self.model = model

    def mutate_java_file(self, java_file_path: str):
        """
        Read a Java file and generate mutations.

        Args:
            java_file_path (str): Path to the Java file.

        Returns:
            list: A list of mutation dictionaries with 'original_code' and 'mutated_code'.
        """
        try:
            with open(java_file_path, "r") as f:
                java_class = f.read()
        except Exception as e:
            print(f" Error reading file {java_file_path}: {e}")
            return []

        return self._mutate_java_class(java_class)

    def _remove_comments(self, java_class: str) -> str:
        """
        Remove comments from the Java class to prevent LLM from mutating them.

        Args:
            java_class (str): Original Java class code.

        Returns:
            str: Java class code without comments.
        """
        java_class = re.sub(r"/\*[\s\S]*?\*/", "", java_class, flags=re.MULTILINE)
        java_class = re.sub(r"//.*", "", java_class)
        return java_class

    def _mutate_java_class(self, java_class: str):
        """
        Generate mutations for the provided Java class code using the selected LLM.

        Args:
            java_class (str): Original Java class code.

        Returns:
            list: A list of mutation dictionaries.
        """
        # Remove comments before mutation
        java_class_clean = self._remove_comments(java_class)

        # Keep only non-empty lines for validation
        valid_lines = {line.strip() for line in java_class_clean.split("\n") if line.strip()}

        # Construct the LLM prompt with strict rules
        prompt = f"""
            Generate exactly 3 mutations of different lines in the following Java class 
            for PIT mutation testing.
            Use only the following mutators:
            {self.MUTATORS_DESCRIPTION}

            RULES:
            - Mutate exactly ONE line per mutation.
            - Do NOT modify class or method declarations.
            - Do NOT introduce new operators; only change existing ones.
            - The mutated line must differ from the original.
            - Do not replace variables with function calls.
            - Output MUST be JSON objects, one per line:
              {{{{"original_code": "<original_code>", "mutated_code": "<mutated_code>"}}}}
            - If the original line does not exist, skip the mutation.
            - No commentary, only JSON objects.

            Original Java class:
            {java_class_clean}
        """

        # Send request to OpenRouter
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        #print(response.json())
        text = response.json()["choices"][0]["message"]["content"].strip()

        # Parse JSON lines from LLM output
        new_mutations = []
        for line in text.split("\n"):
            try:
                mutation_json = json.loads(line)
                original = mutation_json.get("original_code", "").strip()
                mutated = mutation_json.get("mutated_code", "").strip()

                # Validate that the original line exists in the class
                if original not in valid_lines:
                    continue

                new_mutations.append({
                    "original_code": original,
                    "mutated_code": mutated
                })
            except Exception:
                continue

        print(f"Generated {len(new_mutations)} valid mutations")
        return new_mutations
