from google import genai
import json

from environment.config import GOOGLE_AI_API_KEY

client = genai.Client(api_key=f"{GOOGLE_AI_API_KEY}")

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

def mutate_java_class(java_class: str, memory_mutations):

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

memory_mutations = set()

java_code = """

package org.apache.commons.csv;

import java.io.IOException;

abstract class Lexer {

    private final boolean isEncapsulating;
    private final boolean isEscaping;
    private final boolean isCommentEnabled;

    private final char delimiter;
    private final char escape;
    private final char encapsulator;
    private final char commmentStart;

    final boolean surroundingSpacesIgnored;
    final boolean emptyLinesIgnored;

    final CSVFormat format;

    final ExtendedBufferedReader in;

    Lexer(CSVFormat format, ExtendedBufferedReader in) {
        this.format = format;
        this.in = in;
        this.isEncapsulating = format.isEncapsulating();
        this.isEscaping = format.isEscaping();
        this.isCommentEnabled = format.isCommentingEnabled();
        this.delimiter = format.getDelimiter();
        this.escape = format.getEscape();
        this.encapsulator = format.getEncapsulator();
        this.commmentStart = format.getCommentStart();
        this.surroundingSpacesIgnored = format.isSurroundingSpacesIgnored();
        this.emptyLinesIgnored = format.isEmptyLinesIgnored();
    }

    int getLineNumber() {
        return in.getLineNumber();
    }

    int readEscape(int c) throws IOException {
        c = in.read();
        switch (c) {
            case 'r':
                return '\r';
            case 'n':
                return '\n';
            case 't':
                return '\t';
            case 'b':
                return '\b';
            case 'f':
                return '\f';
            default:
                return c;
        }
    }

    void trimTrailingSpaces(StringBuilder buffer) {
        int length = buffer.length();
        while (length > 0 && Character.isWhitespace(buffer.charAt(length - 1))) {
            length = length - 1;
        }
        if (length != buffer.length()) {
            buffer.setLength(length);
        }
    }

    boolean isWhitespace(int c) {
        return (c != format.getDelimiter()) && Character.isWhitespace((char) c);
    }

    boolean isEndOfLine(int c) throws IOException {
        if (c == '\r' && in.lookAhead() == '\n') {
            // note: does not change c outside of this method !!
            c = in.read();
        }
        return (c == '\n' || c == '\r');
    }

    boolean isEndOfFile(int c) {
        return c == ExtendedBufferedReader.END_OF_STREAM;
    }

    abstract Token nextToken(Token reusableToken) throws IOException;

    boolean isDelimiter(int c) {
        return c == delimiter;
    }

    boolean isEscape(int c) {
        return isEscaping && c == escape;
    }

    boolean isEncapsulator(int c) {
        return isEncapsulating && c == encapsulator;
    }

    boolean isCommentStart(int c) {
        return isCommentEnabled && c == commmentStart;
    }
}

"""

mutations = mutate_java_class(java_code, memory_mutations)

print(f"\n# Mutazioni generate: {len(mutations)} mutations")

print("\nMutazioni generate:")
for m in mutations:
    print(m)
