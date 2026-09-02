# EasyDIN5008Streamlit

A local Streamlit application for creating German business letters following the
DIN 5008 layout and exporting them as PDFs.

## Features

- Captures sender, recipient, subject, date, letter body, and footer content.
- Supports back address, sender address, or both in the address window.
- Offers configurable page-number and footer placement.
- Inserts Markdown tables with selectable table and content alignment.
- Exports a PDF using the included Pandoc LaTeX template.
- Provides Latin Modern, Times, Arial, and Calibri-style font selections.

## Prerequisites

- Python 3.14 or later.
- [Pandoc](https://pandoc.org/installing.html), available on your `PATH`.
- A TeX distribution with PDF support, such as [MiKTeX](https://miktex.org/download)
  on Windows or TeX Live on other platforms.

Pandoc and TeX are required because PDF generation is performed by Pandoc using
the included [`letter.latex`](letter.latex) template.

## Installation

### Using uv

```powershell
uv sync
```

### Using pip

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install streamlit[pdf] pypandoc
```

## Run the application

```powershell
uv run streamlit run app.py
```

Or, when using an activated virtual environment:

```powershell
streamlit run app.py
```

Streamlit opens the application in your default browser, normally at
`http://localhost:8501`.

## Debug in VS Code

Choose **Run and Debug** and start the **Run Streamlit App** configuration. It
is defined in [`.vscode/launch.json`](.vscode/launch.json) and runs
`python -m streamlit run app.py` in the integrated terminal.

## Creating a letter

1. Enter sender and recipient addresses. Each address must contain at least
	three non-empty lines.
2. Set the letter options in the sidebar, including the sender-address style,
	font, page-number visibility, and footer alignment.
3. Enter a subject, date, body, and optional footer. The body supports Markdown;
	use **Add table** in the sidebar to insert a table scaffold.
4. Select **Generate Letter**, review the in-app PDF preview, then download the
	generated file.

Generated source and PDF files are kept temporarily in the directory configured
by `temp_dir` in [`config.ini`](config.ini). Files older than `max_age_seconds`
(five minutes by default) are removed when the app runs; downloaded PDFs are
also deleted after download.

## Project structure

| Path | Purpose |
| --- | --- |
| [`app.py`](app.py) | Streamlit user interface and PDF-generation workflow. |
| [`modules.py`](modules.py) | Letter model, Markdown handling, font settings, and temporary-file helpers. |
| [`letter.latex`](letter.latex) | Pandoc LaTeX template for the DIN 5008 layout. |
| [`config.ini`](config.ini) | Temporary-file directory and retention configuration. |
| [`value_help.py`](value_help.py) | Help text displayed in the application. |
