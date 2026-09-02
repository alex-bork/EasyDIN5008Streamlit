import streamlit as st
from uuid import uuid7
import os
from datetime import datetime
from modules import (
    cleanup_temp_dir,
    create_letter,
    TEMP_DIR,
    create_temp_dir,
    delete_temp_file,
    generate_markdown_table,
    align_table_block,
    get_font_preamble,
)
import pypandoc

from value_help import FROM_TO_ADDRESS

st.set_page_config(page_title="EasyDin5008", layout="centered")

if "body" not in st.session_state:
    st.session_state["body"] = ""
    create_temp_dir()
    cleanup_temp_dir()

letter_id = str(uuid7())
st.session_state.setdefault(
    "letter_name",
    f"{datetime.now():%Y.%m.%d} - {letter_id[:3]}{letter_id[-3:]}",
)

with st.sidebar:
    lettername = st.text_input(
        "Letter name",
        help="This will be used as the filename for the generated letter. If not supplied, a random name will be generated.",
        key="letter_name",
    )
    st.selectbox("Language", ["German", "English"], index=0)
    font = st.selectbox("Font", ["Latin Modern", "Times New Roman", "Arial", "Calibri"])
    st.selectbox(
        "From address style",
        ["Backaddress", "Name and Address", "Both"],
        key="from_style",
    )
    show_page_numbers = st.checkbox("Show page numbers", value=False)
    page_number_position = st.selectbox(
        "Page number position",
        ["Left", "Center", "Right"],
        index=1,
        disabled=not show_page_numbers,
    )
    footer_position = st.selectbox(
        "Footer position", ["Left", "Center", "Right"], index=0
    )
    with st.expander("Add table"):
        with st.form("Table", clear_on_submit=True, border=False):
            cols = st.number_input(
                "Number of table columns", min_value=1, max_value=10, value=2
            )
            rows = st.number_input(
                "Number of table rows", min_value=1, max_value=10, value=2
            )
            align_content = st.selectbox(
                "Table text alignment", ["Left", "Center", "Right"]
            )
            align_table = st.selectbox("Table alignment", ["Left", "Center", "Right"])
            add_table = st.form_submit_button("Append table", use_container_width=True)
            if add_table:
                table_markdown = generate_markdown_table(
                    rows, cols, align_content.lower()
                )
                table_markdown = align_table_block(table_markdown, align_table.lower())
                separator = "\n\n" if st.session_state["body"].strip() else ""
                st.session_state["body"] += f"{separator}{table_markdown}"
                st.write(f"Appended a table with {cols} columns and {rows} rows.")


# with st.container(horizontal=True, horizontal_alignment="center"):
from_address = st.text_area("From Address", help=FROM_TO_ADDRESS)
to_address = st.text_area("To Address", help=FROM_TO_ADDRESS)

with st.container(horizontal=True, horizontal_alignment="center"):
    subject = st.text_input("Subject")
    date = st.date_input("Date", format="DD.MM.YYYY", width=150)

body = st.text_area("Body", height=300, key="body")

with st.expander("Footer"):
    footer = st.text_area(
        "Footer",
        height=100,
        label_visibility="collapsed"
    )


with st.container(horizontal=True, horizontal_alignment="center"):
    generate = st.button("Generate Letter", type="primary", width=200)
if generate:
    try:
        letter = create_letter(
            from_address,
            to_address,
            date,
            subject,
            body,
            footer,
            st.session_state["from_style"],
            page_number_position,
            show_page_numbers,
            footer_position,
        )
        markdown = letter.markdown
        cleanup_temp_dir()
        filename = str(uuid7())
        with open(f"{TEMP_DIR}/{filename}.md", "w", encoding="utf-8") as f:
            f.write(markdown)
        output_file = f"{TEMP_DIR}/{filename}.pdf"
        extra_args = ["--template=letter"]
        font_preamble = get_font_preamble(font)
        if font_preamble:
            header_file = f"{TEMP_DIR}/{filename}_font.tex"
            with open(header_file, "w", encoding="utf-8") as f:
                f.write(font_preamble)
            extra_args.append(f"--include-in-header={header_file}")
        pypandoc.convert_file(
            f"{TEMP_DIR}/{filename}.md",
            "pdf",
            outputfile=output_file,
            extra_args=extra_args,
        )
        st.success("Letter generated successfully. Please download it below or it will be deleted after 5 minutes.")
        st.pdf(output_file, height=900)
        with st.container(horizontal=True, horizontal_alignment="center"):
            st.download_button(
                "Download Letter",
                data=open(output_file, "rb"),
                type="primary",
                width=200,
                file_name=f"{lettername if lettername else filename}.pdf",
                mime="application/pdf",
                on_click=delete_temp_file,
                args=[filename],
            )
    except Exception as error:
        if "Footer is too tall for the DIN 5008 footer area" in str(error):
            st.error("The footer contains to much text. Change the text length.")
        else:
            st.error(str(error))
