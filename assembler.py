import os
import sys

COMP = {
    "0": "0101010", "1": "0111111", "-1": "0111010",
    "D": "0001100", "A": "0110000", "!D": "0001101", "!A": "0110001",
    "-D": "0001111", "-A": "0110011", "D+1": "0011111", "A+1": "0110111",
    "D-1": "0001110", "A-1": "0110010", "D+A": "0000010", "D-A": "0010011",
    "A-D": "0000111", "D&A": "0000000", "D|A": "0010101",
    "M": "1110000", "!M": "1110001", "-M": "1110011", "M+1": "1110111",
    "M-1": "1110010", "D+M": "1000010", "D-M": "1010011", "M-D": "1000111",
    "D&M": "1000000", "D|M": "1010101",
}
for _a, _b in (("A+D", "D+A"), ("M+D", "D+M"), ("A&D", "D&A"),
               ("M&D", "D&M"), ("A|D", "D|A"), ("M|D", "D|M"),
               ("1+D", "D+1"), ("1+A", "A+1"), ("1+M", "M+1")):
    COMP[_a] = COMP[_b]

DEST = {"": "000", "M": "001", "D": "010", "MD": "011", "DM": "011",
        "A": "100", "AM": "101", "MA": "101", "AD": "110", "DA": "110",
        "AMD": "111", "ADM": "111", "MAD": "111", "MDA": "111",
        "DAM": "111", "DMA": "111"}

JUMP = {"": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
        "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111"}


def predefined_symbols():
    symbols = {"SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
               "SCREEN": 16384, "KBD": 24576}
    for i in range(16):
        symbols["R%d" % i] = i
    return symbols


def valid_symbol(name):
    if not name or name[0].isdigit():
        return False
    return all(c.isalnum() or c in "_.$:" for c in name)


def clean_source(text):
    """Strip comments / whitespace / blank lines; keep original line numbers."""
    out = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("//", 1)[0]
        line = "".join(line.split())  # Hack has no meaningful inner spaces
        if line:
            out.append((number, line))
    return out


def first_pass(lines):
    """Record (LABEL) addresses. Returns (symbols, instructions, errors)."""
    symbols = predefined_symbols()
    instructions = []
    errors = []
    rom = 0
    for number, line in lines:
        if line.startswith("("):
            if not line.endswith(")") or not valid_symbol(line[1:-1]):
                errors.append("Line %d: invalid label declaration '%s'" % (number, line))
                continue
            label = line[1:-1]
            if label in symbols:
                errors.append("Line %d: label '%s' is already defined" % (number, label))
                continue
            symbols[label] = rom
        else:
            instructions.append((number, line))
            rom += 1
    return symbols, instructions, errors


def translate_c(number, line):
    """Return (binary, error)."""
    dest, jump = "", ""
    rest = line
    if "=" in rest:
        dest, rest = rest.split("=", 1)
    if ";" in rest:
        rest, jump = rest.split(";", 1)
    if dest not in DEST:
        return None, "Line %d: invalid destination '%s' in '%s'" % (number, dest, line)
    if rest not in COMP:
        return None, "Line %d: invalid computation '%s' in '%s'" % (number, rest, line)
    if jump not in JUMP:
        return None, "Line %d: invalid jump '%s' in '%s'" % (number, jump, line)
    return "111" + COMP[rest] + DEST[dest] + JUMP[jump], None


def second_pass(symbols, instructions):
    """Translate to 16-bit words. Variables get RAM 16, 17, ... on first use."""
    words = []
    errors = []
    next_var = 16
    for number, line in instructions:
        if line.startswith("@"):
            sym = line[1:]
            if not sym:
                errors.append("Line %d: invalid instruction '@' has no address" % number)
                continue
            if sym.isdigit():
                value = int(sym)
            elif valid_symbol(sym):
                if sym not in symbols:
                    symbols[sym] = next_var
                    next_var += 1
                value = symbols[sym]
            else:
                errors.append("Line %d: invalid A-instruction '%s'" % (number, line))
                continue
            if value > 32767:
                errors.append("Line %d: address %d does not fit in 15 bits" % (number, value))
                continue
            words.append("0" + format(value, "015b"))
        else:
            word, err = translate_c(number, line)
            if err:
                errors.append(err)
            else:
                words.append(word)
    return words, errors


def assemble(text):
    """Return (words, errors)."""
    lines = clean_source(text)
    symbols, instructions, errors1 = first_pass(lines)
    words, errors2 = second_pass(symbols, instructions)
    errors = sorted(errors1 + errors2, key=lambda e: int(e.split(":")[0].split()[1]))
    return words, errors


def assemble_file(path):
    with open(path, encoding="utf-8") as f:
        words, errors = assemble(f.read())
    if errors:
        for e in errors:
            print(e)
        print("%d error(s) found - %s not written." % (len(errors), os.path.splitext(path)[0] + ".hack"))
        return 1
    out = os.path.splitext(path)[0] + ".hack"
    with open(out, "w", newline="\n") as f:
        f.write("\n".join(words) + "\n")
    print("Wrote %s (%d instructions)" % (out, len(words)))
    return 0


def self_test():
    ok = True

    def check(n, name, cond):
        nonlocal ok
        print("TEST %d: %s %s" % (n, name, "PASSED" if cond else "FAILED"))
        ok = ok and cond

    words, errs = assemble("@2\nD=A\n@3\nD=D+A\n@0\nM=D\n")
    check(1, "Addition translation", not errs and words == [
        "0000000000000010", "1110110000010000", "0000000000000011",
        "1110000010010000", "0000000000000000", "1110001100001000"])

    words, errs = assemble("@counter\nM=1\n@result\nM=1\n@counter\nM=0\n")
    check(2, "Variable allocation",
          not errs and words[0] == "0000000000010000" and words[2] == "0000000000010001"
          and words[4] == "0000000000010000")

    words, errs = assemble("@1\n(END)\n@END\n0;JMP\n")
    check(3, "Label address resolution", not errs and words[1] == "0000000000000001")

    _, errs = assemble("@1\nD=A\nFOO\nD=Q+1\nD=A;JXX\n")
    check(4, "Invalid lines reported with line numbers (K feature)",
          len(errs) == 3 and errs[0].startswith("Line 3:")
          and errs[1].startswith("Line 4:") and errs[2].startswith("Line 5:"))
    for e in errs:
        print("   ", e)

    words, errs = assemble("D=A\nM=D\n0;JMP\n")
    check(5, "C-instruction translation", not errs and words == [
        "1110110000010000", "1110001100001000", "1110101010000111"])

    print("===== SELF-TEST %s =====" % ("COMPLETE" if ok else "FAILED"))
    return 0 if ok else 1


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) != 2:
        print("Usage: python assembler.py Prog.asm | --self-test")
        return 2
    try:
        return assemble_file(argv[1])
    except OSError as exc:
        print("Cannot read file: %s" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
