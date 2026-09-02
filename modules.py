import time
import os
import re
import configparser
from datetime import date as date_type

_config = configparser.ConfigParser()
_config.read(os.path.join(os.path.dirname(__file__), "config.ini"))

TEMP_DIR = _config.get("temp", "temp_dir", fallback="temp")
MAX_AGE_SECONDS = _config.getint("temp", "max_age_seconds", fallback=24 * 60 * 60)

# LaTeX preamble snippets for each selectable font, using standard psnfss
# packages that ship with every TeX distribution (no extra font installs needed).
FONT_PREAMBLES = {
    "Latin Modern": "",  # letter.latex already loads lmodern by default
    "Times New Roman": r"\usepackage{mathptmx}",
    "Arial": "\\usepackage{helvet}\n\\renewcommand{\\familydefault}{\\sfdefault}",
    "Calibri": "\\renewcommand{\\familydefault}{\\sfdefault}",
}


def get_font_preamble(font_name: str) -> str:
    """Return the LaTeX preamble snippet (possibly empty) for the given font selection."""
    return FONT_PREAMBLES.get(font_name, "")


def delete_temp_file(filename: str):
    """Delete a temporary file if it exists."""
    try:
        if os.path.exists(f"{TEMP_DIR}/{filename}.pdf"):
            os.remove(f"{TEMP_DIR}/{filename}.pdf")
            os.remove(f"{TEMP_DIR}/{filename}.md")
    except Exception as e:
        print(f"Error deleting temporary file {TEMP_DIR}/{filename}.pdf or {TEMP_DIR}/{filename}.md: {e}")


def _yaml_str(value: str) -> str:
    """Escape a value for use as a YAML double-quoted scalar."""
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


_LONG_WORD_THRESHOLD = 30
_BREAK_INTERVAL = 20
_FENCED_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)


def _break_long_words(text: str) -> str:
    """Insert zero-width spaces into unbroken long tokens so LaTeX can wrap them.

    Skips fenced code blocks (e.g. raw ```{=latex}``` blocks) so raw commands aren't corrupted.
    """
    def _break(match: re.Match) -> str:
        word = match.group(0)
        if len(word) <= _LONG_WORD_THRESHOLD:
            return word
        chunks = [word[i:i + _BREAK_INTERVAL] for i in range(0, len(word), _BREAK_INTERVAL)]
        return "\u200b".join(chunks)

    parts = _FENCED_CODE_BLOCK.split(text)
    fences = _FENCED_CODE_BLOCK.findall(text)
    broken_parts = [re.sub(r"\S+", _break, part) for part in parts]
    out = []
    for i, part in enumerate(broken_parts):
        out.append(part)
        if i < len(fences):
            out.append(fences[i])
    return "".join(out)


def _expand_blank_lines(text: str) -> str:
    """Preserve extra blank lines as extra paragraph gaps (Markdown collapses them by default).

    Also forces single newlines within a paragraph to be hard line breaks, since
    Markdown otherwise collapses them into a single space (a "soft break"), which
    made e.g. a closing signature on its own line merge onto the previous line.
    Lines inside fenced code blocks (```...```) or Markdown table rows (starting
    with "|") are left untouched, since a trailing hard-break marker would corrupt
    their syntax.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    out = []
    blank_run = 0
    in_fence = False
    for line in lines:
        is_fence_marker = line.strip().startswith("```")
        if not in_fence and not is_fence_marker and line.strip() == "":
            blank_run += 1
            continue
        # Flush any pending blank-line gap before the fence/table/content line itself,
        # so it never gets injected inside a fenced block or immediately after it opens.
        if blank_run:
            out.append("")
            for _ in range(blank_run - 1):
                out.append("&nbsp;")
                out.append("")
            blank_run = 0
        if is_fence_marker:
            in_fence = not in_fence
            out.append(line)
        elif in_fence or line.strip().startswith("|"):
            out.append(line)
        else:
            out.append(line + "  ")
    return "\n".join(out)


def generate_markdown_table(rows: int, cols: int, align: str = "left") -> str:
    """Build a placeholder Markdown table with the given number of rows, columns and column alignment."""
    separators = {"left": ":---", "center": ":---:", "right": "---:"}
    sep_cell = separators.get(align.lower(), ":---")
    header = "| " + " | ".join(f"Header {c + 1}" for c in range(cols)) + " |"
    separator = "| " + " | ".join([sep_cell] * cols) + " |"
    # Placeholder cells are deliberately much shorter than the header so the
    # chosen alignment leaves visible room to shift and is easy to see.
    body_rows = ["| " + " | ".join(str(r + 1) for _ in range(cols)) + " |" for r in range(rows)]
    return "\n".join([header, separator, *body_rows])


def align_table_block(markdown_table: str, table_align: str) -> str:
    """Wrap a Markdown table in raw LaTeX so the whole table is positioned on the page.

    longtable ignores surrounding environments like center/flushright and instead
    positions itself using \\LTleft/\\LTright (which default to \\fill/\\fill, i.e.
    centered), so those lengths must be set directly.
    """
    lengths = {
        "left": (r"0pt", r"\fill"),
        "center": (r"\fill", r"\fill"),
        "right": (r"\fill", r"0pt"),
    }
    pair = lengths.get(table_align.lower())
    if not pair:
        return markdown_table
    lt_left, lt_right = pair
    return f"""```{{=latex}}
{{\\setlength{{\\LTleft}}{{{lt_left}}}\\setlength{{\\LTright}}{{{lt_right}}}
```
{markdown_table}

```{{=latex}}
}}
```"""


class Letter:
    def __init__(self, from_address:str, to_address:str, date:str, subject:str, body:str, footer:str, from_style:str = "Backaddress", page_number_position: str = "Right", show_page_numbers: bool = True, footer_position: str = "Left"):
        address_parts = [
            line.strip()
            for line in from_address.replace("\r\n", "\n").split("\n")
            if line.strip()
        ]
        if not address_parts or len(address_parts) < 3:
            raise ValueError("From address must have at least 3 lines.")
        self.from_lines = address_parts
        self.from_address = "  \n".join(address_parts)
        address_parts = [
            line.strip()
            for line in to_address.replace("\r\n", "\n").split("\n")
            if line.strip()
        ]
        if not address_parts or len(address_parts) < 3:
            raise ValueError("To address must have at least 3 lines.")
        self.to_address = "  \n".join(address_parts)
        self.date = date
        self.subject = subject
        self.body = body
        self.footer = footer
        self.from_style = from_style
        self.show_page_numbers = show_page_numbers
        self.footer_position = {
            "left": "l",
            "center": "c",
            "right": "r",
        }.get(footer_position.lower(), "l")
        self.page_number_position = {
            "left": "l",
            "center": "c",
            "right": "r",
        }.get(page_number_position.lower(), "r")

    def __check_address(self, address: str) -> bool:
        return bool(address and address.strip())

    @property
    def markdown(self):

        fields = []
        show_name_and_address = self.from_style in ("Name and Address", "Both")
        show_backaddress = self.from_style in ("Backaddress", "Both")
        if show_name_and_address and self.from_lines:
            fields.append(f"fromname: {_yaml_str(self.from_lines[0])}")
            if len(self.from_lines) > 1:
                fromaddress_value = "  \n".join(self.from_lines[1:])
                fields.append(f"fromaddress: {_yaml_str(fromaddress_value)}")
        if show_backaddress:
            backaddress_value = ", ".join(self.from_lines)
            fields.append(f"backaddress: {_yaml_str(backaddress_value)}")
        fields.append(f"to: {_yaml_str(self.to_address)}")
        fields.append(f"date: {_yaml_str(self.date)}")
        fields.append(f"subject: {_yaml_str(self.subject)}")
        fields.append(f"footer: {_yaml_str(self.footer)}")
        fields.append(f"footer-position: {_yaml_str(self.footer_position)}")
        fields.append(f"show-page-numbers: {str(self.show_page_numbers).lower()}")
        fields.append(f"page-number-position: {_yaml_str(self.page_number_position)}")
        frontmatter = "\n".join(fields)

        return f"""---
{frontmatter}
---
{_expand_blank_lines(_break_long_words(self.body))}
"""


def create_letter(from_address:str, to_address:str, date:str | date_type, subject:str, body:str, footer:str, from_style:str = "Backaddress", page_number_position: str = "Right", show_page_numbers: bool = True, footer_position: str = "Left") -> Letter:

    date = date.strftime("%d.%m.%Y") if isinstance(date, date_type) else date

    subject = subject.strip() if subject else ""

    body = body.strip() if body else ""

    footer = footer.strip() if footer else ""

    letter = Letter(from_address, to_address, date, subject, body, footer, from_style, page_number_position, show_page_numbers, footer_position)
    return letter


def cleanup_temp_dir():
    now = time.time()
    for entry in os.scandir(TEMP_DIR):
        if entry.is_file() and now - entry.stat().st_mtime > MAX_AGE_SECONDS:
            os.remove(entry.path)


def create_temp_dir():
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
