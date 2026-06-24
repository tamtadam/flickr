#!/usr/bin/env python3
"""Simple CLI math practice for addition and subtraction."""

import random
import select
import sys
import termios
import tty


MIN_NUMBER = 0
NUMBER_RANGES = (10, 20)
MAX_RESULT = 30

# Basic ANSI colors for friendlier CLI output.
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"


def colorize(text: str, color: str) -> str:
    """Return colored text only when output is a terminal."""
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{RESET}"


def read_answer_with_spinner(prompt: str) -> str:
    """Read input with a spinner shown until the first keypress."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return input(colorize(prompt, CYAN)).strip()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    spinner_chars = "|/-\\"
    spinner_index = 0
    typed_chars: list[str] = []

    try:
        tty.setcbreak(fd)

        while True:
            # Show animated spinner only while no key has been pressed yet.
            if typed_chars:
                line = "".join(typed_chars)
            else:
                line = spinner_chars[spinner_index % len(spinner_chars)]
                spinner_index += 1

            print(f"\r{colorize(prompt, CYAN)}{line} ", end="", flush=True)

            ready, _, _ = select.select([sys.stdin], [], [], 0.12)
            if not ready:
                continue

            ch = sys.stdin.read(1)

            if ch == "\x03":
                raise KeyboardInterrupt

            if ch in ("\n", "\r"):
                print()
                return "".join(typed_chars).strip()

            if ch in ("\x7f", "\b"):
                if typed_chars:
                    typed_chars.pop()
                continue

            typed_chars.append(ch)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def generate_task() -> tuple[str, int]:
    """Generate one random math task and the expected answer."""
    task_type = random.choice(["add", "sub", "missing_add"])
    max_operand = random.choice(NUMBER_RANGES)

    if task_type == "add":
        a = random.randint(MIN_NUMBER, max_operand)
        b_max = min(max_operand, MAX_RESULT - a)
        b = random.randint(MIN_NUMBER, b_max)
        question = f"Mennyi: {a} + {b} = "
        answer = a + b
        return question, answer

    if task_type == "sub":
        a = random.randint(MIN_NUMBER, min(max_operand, MAX_RESULT))
        b = random.randint(MIN_NUMBER, a)
        question = f"Mennyi: {a} - {b} = "
        answer = a - b
        return question, answer

    base = random.randint(MIN_NUMBER, max_operand)
    addend_max = min(max_operand, MAX_RESULT - base)
    addend = random.randint(MIN_NUMBER, addend_max)
    target = base + addend
    question = f"Mennyit kell hozzaadni {base}-hoz, hogy {target} legyen? "
    answer = addend
    return question, answer


def ask_until_correct(question: str, expected_answer: int) -> None:
    """Keep asking the same task until the user provides the correct number."""
    while True:
        user_input = read_answer_with_spinner(question)

        try:
            user_answer = int(user_input)
        except ValueError:
            print(colorize("Hibas bemenet. Egesz szamot adj meg!", YELLOW))
            continue

        if user_answer == expected_answer:
            print(colorize("Helyes!", GREEN))
            break

        print(colorize("Hibas eredmeny, probald ujra!", RED))


def main() -> None:
    """Run the practice loop forever."""
    print(colorize(f"{BOLD}Matek gyakorlo indult.{RESET}", CYAN))
    print(colorize("Feladattipusok: osszeadas, kivonas, mennyit kell hozzaadni.", YELLOW))
    print(colorize("Szamkor: 10-es es 20-as, 30 folotti ertek nem lesz.", YELLOW))
    print(colorize("Uj feladat csak helyes valasz utan jon.", YELLOW))
    print(colorize("Leallitas: Ctrl+C", YELLOW))

    while True:
        question, expected_answer = generate_task()
        ask_until_correct(question, expected_answer)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(colorize("\nKilepes.", CYAN))
