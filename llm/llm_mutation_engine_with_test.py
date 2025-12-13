import json
import re
import requests
from environment.config import OPENROUTER_API_KEY

class LLMMutationEngineWithTest:
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

    def mutate_java_file(self, java_file_path: str, test_file_path: str = ""):
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
        if test_file_path != "":
            try:
                with open(test_file_path, "r") as f:
                    test_class = f.read()
            except Exception as e:
                print(f" Error reading file {test_file_path}: {e}")
                return []
        else:
            test_class = ""

        return self._mutate_java_class(java_class, test_class)

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

    def _mutate_java_class(self, java_class: str, test_class: str = "") -> list:
        """
        Generate mutations for the provided Java class code using the selected LLM.

        Args:
            java_class (str): Original Java class code.

        Returns:
            list: A list of mutation dictionaries.
        """
        # Remove comments before mutation
        java_class_clean = self._remove_comments(java_class)

        test_class_clean = self._remove_comments(test_class)

        # Keep only non-empty lines for validation
        valid_lines = {line.strip() for line in java_class_clean.split("\n") if line.strip()}

        # Construct the LLM prompt with strict rules
        prompt = f"""
            You are a mutation generation engine.

            Your objective is to generate Java code mutations that are
            HIGHLY LIKELY to produce mutants that SURVIVE the given test suite.

            You may apply ANY mutation operator or code transformation,
            as long as:
            - the code still compiles
            - the change is plausible and subtle
            - the behavior change is NOT obviously asserted by the tests

            Use only the following mutators:
            {self.MUTATORS_DESCRIPTION}

            STRICT RULES:
            - Output ONLY JSON objects, one per line
            - NO explanations, NO markdown, NO comments
            - Mutate EXACTLY ONE LINE per mutation
            - Do NOT modify class or method declarations
            - Do NOT add or remove methods
            - Do NOT introduce new control structures
            - Do NOT replace variables with method calls
            - The mutated line must be syntactically valid Java
            - Prefer mutations that change semantics WITHOUT changing structure
            - Prefer mutations that exploit missing assertions, default values, or edge cases
            - DON'T GIVE ME TOO MUCH MUTATIONS, JUST THE ONES YOU ARE 100% SURE THEY WILL SURVIVE THE TESTS
            - GENERATE AT LEAST 5 MUTATIONS

            MANDATORY JSON FORMAT:
            {{"original_code":"<exact original line>","mutated_code":"<mutated line>"}}

            Original Java class:
            <CODE>
            {java_class_clean}
            </CODE>

            Test class:
            <TESTS>
            {test_class_clean}
            </TESTS>



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

        response.json()
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
