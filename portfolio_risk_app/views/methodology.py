"""Page 5 — plain-language methodology, generated from ui/glossary.py."""

import streamlit as st

from ui.components import note, page_header
from ui.glossary import SECTIONS

page_header(
    "Methodology",
    "What every number means for an investor, how it is computed, and how to read it.",
)
note("Opened from an ⓘ link? Your analysis is still open in the other tab.")

# Table of contents
toc = []
for sec in SECTIONS:
    items = " · ".join(f"[{e['title']}](#{e['anchor']})" for e in sec["entries"])
    toc.append(f"**[{sec['title']}](#{sec['anchor']})** — {items}")
with st.container(border=True):
    st.markdown("\n\n".join(toc))

for sec in SECTIONS:
    st.header(sec["title"], anchor=sec["anchor"], divider="gray")
    for e in sec["entries"]:
        st.subheader(e["title"], anchor=e["anchor"])
        st.markdown(
            f"**What it tells you.** {e['meaning']}\n\n"
            f"**How it is computed.** {e['computed']}\n\n"
            f"**How to read it.** {e['reading']}"
        )

st.header("Limits", anchor="limits", divider="gray")
st.markdown(
    "Past data do not predict the future. Yahoo data can contain gaps or errors, especially for funds. The models "
    "assume that the past structure of risk (volatility, correlation) remains representative. This tool is for "
    "education and discussion, not investment advice."
)
