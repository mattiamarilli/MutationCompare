import requests
import json

from environment.config import OPENROUTER_API_KEY, OPENROUTER_X_AI_GROK_MODEL_NAME

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
Generate ALL possible mutations of different lines in the following Java class for PIT mutation testing.
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
- Do not substitute variables with function calls like Integer.compare;
- Return exactly JSON objects, one per line: {{"original_code": "<original_code>", "mutated_code": "<mutated_code>"}}
- I don't want an array of JSON
Start output now (NO commentary, ONLY JSON objects, one per line):
"""

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps({
            "model": f"{OPENROUTER_X_AI_GROK_MODEL_NAME}",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
    )

    text = response.json()["choices"][0]["message"]["content"].strip()
    print(text)

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
package org.apache.commons.csv;

import java.io.IOException;
import java.io.Reader;
import java.io.Serializable;
import java.io.StringWriter;

public class CSVFormat implements Serializable {

    private static final String CRLF = "\r\n";
    
    private final char delimiter;
    private final char encapsulator;
    private final char commentStart;
    private final char escape;
    private final boolean surroundingSpacesIgnored;
    private final boolean emptyLinesIgnored;
    private final String lineSeparator;
    private final String[] header;

    static final char DISABLED = '\ufffe';

    public static final CSVFormat DEFAULT =
            PRISTINE.
            withDelimiter(',')
            .withEncapsulator('"')
            .withEmptyLinesIgnored(true)
            .withLineSeparator(CRLF);

    public static final CSVFormat RFC4180 =
            PRISTINE.
            withDelimiter(',')
            .withEncapsulator('"')
            .withLineSeparator(CRLF);

    public static final CSVFormat EXCEL =
            PRISTINE
            .withDelimiter(',')
            .withEncapsulator('"')
            .withLineSeparator(CRLF);

    public static final CSVFormat TDF =
            PRISTINE
            .withDelimiter('\t')
            .withEncapsulator('"')
            .withSurroundingSpacesIgnored(true)
            .withEmptyLinesIgnored(true)
            .withLineSeparator(CRLF);

    public static final CSVFormat MYSQL =
            PRISTINE
            .withDelimiter('\t')
            .withEscape('\\')
            .withLineSeparator("\n");


    CSVFormat(
            char delimiter,
            char encapsulator,
            char commentStart,
            char escape,
            boolean surroundingSpacesIgnored,
            boolean emptyLinesIgnored,
            String lineSeparator,
            String[] header) {
        this.delimiter = delimiter;
        this.encapsulator = encapsulator;
        this.commentStart = commentStart;
        this.escape = escape;
        this.surroundingSpacesIgnored = surroundingSpacesIgnored;
        this.emptyLinesIgnored = emptyLinesIgnored;
        this.lineSeparator = lineSeparator;
        this.header = header;
    }

    private static boolean isLineBreak(char c) {
        return c == '\n' || c == '\r';
    }

    void validate() throws IllegalArgumentException {
        if (delimiter == encapsulator) {
            throw new IllegalArgumentException("The encapsulator character and the delimiter cannot be the same (\"" + encapsulator + "\")");
        }
        
        if (delimiter == escape) {
            throw new IllegalArgumentException("The escape character and the delimiter cannot be the same (\"" + escape + "\")");
        }
        
        if (delimiter == commentStart) {
            throw new IllegalArgumentException("The comment start character and the delimiter cannot be the same (\"" + commentStart + "\")");
        }
        
        if (encapsulator != DISABLED && encapsulator == commentStart) {
            throw new IllegalArgumentException("The comment start character and the encapsulator cannot be the same (\"" + commentStart + "\")");
        }
        
        if (escape != DISABLED && escape == commentStart) {
            throw new IllegalArgumentException("The comment start and the escape character cannot be the same (\"" + commentStart + "\")");
        }
    }

    public char getDelimiter() {
        return delimiter;
    }

    public CSVFormat withDelimiter(char delimiter) {
        if (isLineBreak(delimiter)) {
            throw new IllegalArgumentException("The delimiter cannot be a line break");
        }

        return new CSVFormat(delimiter, encapsulator, commentStart, escape, surroundingSpacesIgnored, emptyLinesIgnored, lineSeparator, header);
    }

    public char getEncapsulator() {
        return encapsulator;
    }

    public CSVFormat withEncapsulator(char encapsulator) {
        if (isLineBreak(encapsulator)) {
            throw new IllegalArgumentException("The encapsulator cannot be a line break");
        }
        
        return new CSVFormat(delimiter, encapsulator, commentStart, escape, surroundingSpacesIgnored, emptyLinesIgnored, lineSeparator, header);
    }

    boolean isEncapsulating() {
        return this.encapsulator != DISABLED;
    }

    public char getCommentStart() {
        return commentStart;
    }

    public CSVFormat withCommentStart(char commentStart) {
        if (isLineBreak(commentStart)) {
            throw new IllegalArgumentException("The comment start character cannot be a line break");
        }
        
        return new CSVFormat(delimiter, encapsulator, commentStart, escape, surroundingSpacesIgnored, emptyLinesIgnored, lineSeparator, header);
    }

    public boolean isCommentingEnabled() {
        return this.commentStart != DISABLED;
    }

    public char getEscape() {
        return escape;
    }

    public CSVFormat withEscape(char escape) {
        if (isLineBreak(escape)) {
            throw new IllegalArgumentException("The escape character cannot be a line break");
        }
        
        return new CSVFormat(delimiter, encapsulator, commentStart, escape, surroundingSpacesIgnored, emptyLinesIgnored, lineSeparator, header);
    }

    boolean isEscaping() {
        return this.escape != DISABLED;
    }

    public boolean isSurroundingSpacesIgnored() {
        return surroundingSpacesIgnored;
    }

    public CSVFormat withSurroundingSpacesIgnored(boolean surroundingSpacesIgnored) {
        return new CSVFormat(delimiter, encapsulator, commentStart, escape, surroundingSpacesIgnored, emptyLinesIgnored, lineSeparator, header);
    }

    public boolean isEmptyLinesIgnored() {
        return emptyLinesIgnored;
    }

    public CSVFormat withEmptyLinesIgnored(boolean emptyLinesIgnored) {
        return new CSVFormat(delimiter, encapsulator, commentStart, escape, surroundingSpacesIgnored, emptyLinesIgnored, lineSeparator, header);
    }

    public String getLineSeparator() {
        return lineSeparator;
    }

    public CSVFormat withLineSeparator(String lineSeparator) {
        return new CSVFormat(delimiter, encapsulator, commentStart, escape, surroundingSpacesIgnored, emptyLinesIgnored, lineSeparator, header);
    }

    String[] getHeader() {
        return header;
    }

    public CSVFormat withHeader(String... header) {
        return new CSVFormat(delimiter, encapsulator, commentStart, escape, surroundingSpacesIgnored, emptyLinesIgnored, lineSeparator, header);
    }

    public Iterable<CSVRecord> parse(Reader in) throws IOException {
        return new CSVParser(in, this);
    }


    public String format(String... values) {
        StringWriter out = new StringWriter();
        try {
            new CSVPrinter(out, this).println(values);
        } catch (IOException e) {
        }
        
        return out.toString().trim();
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("Delimiter=<").append(delimiter).append('>');
        if (isEscaping()) {
            sb.append(' ');
            sb.append("Escape=<").append(escape).append('>');
        }
        if (isEncapsulating()) {
            sb.append(' ');
            sb.append("Encapsulator=<").append(encapsulator).append('>');            
        }
        if (isCommentingEnabled()) {
            sb.append(' ');
            sb.append("CommentStart=<").append(commentStart).append('>');
        }
        if (isEmptyLinesIgnored()) {
            sb.append(" EmptyLines:ignored");            
        }
        if (isSurroundingSpacesIgnored()) {
            sb.append(" SurroundingSpaces:ignored");            
        }
        return sb.toString();
    }
    
}
"""

mutations = mutate_java_class(java_code, memory_mutations, num_mutations=20)

print(f"\n# Mutazioni generate: {len(mutations)} mutations\n")

print("Mutazioni generate:")
for m in mutations:
    print(m)
