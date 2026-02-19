"""
IndustrialRAG - Streamlit Frontend
"""

import streamlit as st
import requests
import os

API_BASE = os.environ.get("API_BASE", "http://localhost:8000")

st.set_page_config(
    page_title="IndustrialRAG",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"]  { font-family: 'IBM Plex Sans', sans-serif; }
.stApp                       { background: #0d0f14; color: #e0e4ef; }
[data-testid="stSidebar"]   { background: #13161f; border-right: 1px solid #1e2235; }
h1, h2, h3                  { font-family: 'IBM Plex Mono', monospace; color: #f0f4ff; }

.metric-card  { background:#13161f; border:1px solid #1e2235; border-left:3px solid #4f8ef7;
                border-radius:4px; padding:16px 20px; margin:8px 0; }
.sec-label    { font-family:'IBM Plex Mono',monospace; font-size:0.7rem; font-weight:600;
                color:#4f8ef7; text-transform:uppercase; letter-spacing:2px;
                margin-top:16px; margin-bottom:6px; }
.step-item    { background:#0d0f14; border:1px solid #1e2235; border-left:3px solid #22c55e;
                padding:10px 14px; margin:6px 0; border-radius:3px; font-size:0.9rem; line-height:1.5; }
.cause-item   { background:#0d0f14; border:1px solid #1e2235; border-left:3px solid #f59e0b;
                padding:10px 14px; margin:6px 0; border-radius:3px; font-size:0.9rem; }
.warn-item    { background:#1a0f0f; border:1px solid #3d1515; border-left:3px solid #ef4444;
                padding:10px 14px; margin:6px 0; border-radius:3px; font-size:0.9rem; }
.ref-link     { display:inline-block; background:#1a2240; border:1px solid #2a3a6a; color:#7ba8f7;
                padding:5px 12px; border-radius:3px; margin:4px 4px 4px 0;
                font-family:'IBM Plex Mono',monospace; font-size:0.78rem; text-decoration:none; }
.badge        { display:inline-block; background:#1e2a4a; border:1px solid #4f8ef7; color:#7ba8f7;
                padding:3px 12px; border-radius:2px; font-family:'IBM Plex Mono',monospace;
                font-size:0.75rem; letter-spacing:1px; text-transform:uppercase; margin-bottom:12px; }
.chunk-row    { border-left:3px solid; padding:8px 12px; margin:5px 0; background:#0d0f14;
                font-size:0.8rem; border-radius:2px; }

.stButton > button {
    background:#4f8ef7 !important; color:#fff !important; border:none !important;
    border-radius:3px !important; font-family:'IBM Plex Mono',monospace !important;
    font-size:0.85rem !important; font-weight:600 !important; letter-spacing:1px !important;
}
.stButton > button:hover { background:#6fa3ff !important; }
.stTextArea textarea, .stTextInput input {
    background:#13161f !important; border-color:#1e2235 !important;
    color:#e0e4ef !important; font-family:'IBM Plex Mono',monospace !important;
}
.stTabs [data-baseweb="tab"] {
    font-family:'IBM Plex Mono',monospace; font-size:0.82rem;
    letter-spacing:1px; text-transform:uppercase; color:#5a6380;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color:#4f8ef7; border-bottom:2px solid #4f8ef7;
}
hr { border-color:#1e2235; }
</style>
""", unsafe_allow_html=True)


# ── API helpers ──────────────────────────────────────────────────────────────

def api_get(path: str):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=20)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def api_post(path: str, json=None, data=None, files=None):
    try:
        r = requests.post(
            f"{API_BASE}{path}",
            json=json, data=data, files=files,
            timeout=180,
        )
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}: {r.text[:400]}"}
    except Exception as e:
        return {"error": str(e)}


def api_delete(path: str):
    try:
        r = requests.delete(f"{API_BASE}{path}", timeout=30)
        if r.status_code == 200:
            return r.json()
        return {"error": f"HTTP {r.status_code}: {r.text[:400]}"}
    except Exception as e:
        return {"error": str(e)}


# ── LLM output parser ────────────────────────────────────────────────────────

def parse_output(text: str) -> dict:
    out = {"summary": "", "causes": [], "steps": [], "safety": ""}
    section = None
    for raw_line in text.split("\n"):
        line  = raw_line.strip()
        upper = line.upper()
        if not line:
            continue
        if "PROBLEM SUMMARY" in upper:
            section = "summary"
            continue
        if "POSSIBLE CAUSES" in upper:
            section = "causes"
            continue
        if "CORRECTIVE ACTION" in upper or "STEP-BY-STEP" in upper:
            section = "steps"
            continue
        if "SAFETY" in upper:
            section = "safety"
            continue
        if section == "summary":
            out["summary"] += line + " "
        elif section == "causes":
            clean = line.lstrip("0123456789.-• ").strip()
            if clean:
                out["causes"].append(clean)
        elif section == "steps":
            clean = line.lstrip("0123456789.-• ").strip()
            if clean:
                out["steps"].append(clean)
        elif section == "safety":
            out["safety"] += line + " "
    return out


# ── Result renderer ──────────────────────────────────────────────────────────

def render_result(res: dict):
    machine    = res.get("machine", "Unknown")
    query      = res.get("query", "")
    context    = res.get("context", "")
    references = res.get("references", [])
    chunks     = res.get("_chunks", [])

    st.markdown(f'<div class="badge">⚙️ {machine}</div>', unsafe_allow_html=True)

    fmt = api_post("/format", json={"context": context, "query": query, "machine": machine})

    if not fmt or "error" in fmt or not fmt.get("formatted"):
        err = (fmt or {}).get("error", "Format endpoint unreachable")
        st.warning(f"Formatting failed: {err}")
        if context:
            with st.expander("Raw retrieved context"):
                st.text(context[:4000])
        st.markdown("---")
        return

    parsed = parse_output(fmt["formatted"])

    # Summary
    summary = parsed["summary"].strip()
    if summary:
        st.markdown('<div class="sec-label">Problem Summary</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:#c0c8e0;line-height:1.6;margin-bottom:12px">{summary}</div>',
            unsafe_allow_html=True,
        )

    # Causes + Steps side by side
    col_l, col_r = st.columns(2)
    with col_l:
        if parsed["causes"]:
            st.markdown('<div class="sec-label">Possible Causes</div>', unsafe_allow_html=True)
            for cause in parsed["causes"]:
                st.markdown(f'<div class="cause-item">⚡ {cause}</div>', unsafe_allow_html=True)

    with col_r:
        if parsed["steps"]:
            st.markdown('<div class="sec-label">Corrective Actions</div>', unsafe_allow_html=True)
            for i, step in enumerate(parsed["steps"], 1):
                num  = f'<span style="color:#4f8ef7;font-family:IBM Plex Mono,monospace;font-size:0.8rem">{i:02d}</span>'
                st.markdown(f'<div class="step-item">{num} &nbsp; {step}</div>', unsafe_allow_html=True)

    # Safety
    safety = parsed["safety"].strip()
    if safety and "none" not in safety.lower():
        st.markdown('<div class="sec-label">Safety Notes</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="warn-item">⚠️ {safety}</div>', unsafe_allow_html=True)

    # References
    if references:
        st.markdown('<div class="sec-label">Manual References</div>', unsafe_allow_html=True)
        links = ""
        for ref in references:
            pdf  = ref.get("pdf", "")
            page = ref.get("page", 1)
            url  = f"{API_BASE}/pdf/{pdf}#page={page}"
            links += f'<a href="{url}" target="_blank" class="ref-link">📄 {pdf} — Page {page}</a>'
        st.markdown(links, unsafe_allow_html=True)

    # Chunk inspector
    with st.expander("🔍 Retrieved context chunks & relevance scores"):
        if chunks:
            for c in chunks:
                score = c.get("score", 0)
                color = "#22c55e" if score > 0.6 else "#f59e0b" if score > 0.4 else "#ef4444"
                src   = (
                    f"Page {c.get('page_number', '?')} | {c.get('source_pdf', '')}"
                    if c.get("source") == "manual" else "Repair Log"
                )
                preview = c.get("text", "")[:300]
                st.markdown(
                    f'<div class="chunk-row" style="border-color:{color}">'
                    f'<span style="color:{color};font-family:IBM Plex Mono,monospace">'
                    f'score: {score:.2f} | {src}</span>'
                    f'<br><span style="color:#c0c8e0">{preview}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.text(context[:3000])

    st.markdown("---")


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="padding:16px 0 24px 0">'
        '<div style="font-family:IBM Plex Mono,monospace;font-size:1.3rem;font-weight:600;color:#4f8ef7">⚙️ IndustrialRAG</div>'
        '<div style="font-size:0.72rem;color:#5a6380;letter-spacing:3px;text-transform:uppercase">Maintenance Intelligence</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    health = api_get("/health")
    if health:
        st.markdown(
            f'<div class="metric-card">'
            f'<div style="font-size:0.7rem;color:#5a6380;text-transform:uppercase;letter-spacing:2px">System Status</div>'
            f'<div style="color:#22c55e;font-family:IBM Plex Mono,monospace;margin-top:4px">● ONLINE</div>'
            f'<div style="color:#5a6380;font-size:0.78rem;margin-top:4px">{health.get("chunks_indexed", 0)} chunks indexed</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="metric-card">'
            '<div style="font-size:0.7rem;color:#5a6380;text-transform:uppercase;letter-spacing:2px">System Status</div>'
            '<div style="color:#ef4444;font-family:IBM Plex Mono,monospace;margin-top:4px">● BACKEND OFFLINE</div>'
            '<div style="color:#5a6380;font-size:0.78rem;margin-top:4px">Run: ./start.sh</div>'
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    machines_resp = api_get("/admin/machines")
    machines = (machines_resp or {}).get("machines", [])

    if machines:
        st.markdown(
            '<div style="font-size:0.7rem;color:#5a6380;text-transform:uppercase;'
            'letter-spacing:2px;margin-bottom:8px">Indexed Machines</div>',
            unsafe_allow_html=True,
        )
        for m in machines:
            st.markdown(
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.8rem;'
                f'color:#7ba8f7;padding:4px 0">▸ {m}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#5a6380;font-size:0.8rem">No machines indexed yet.</div>',
            unsafe_allow_html=True,
        )


# ── Tabs ─────────────────────────────────────────────────────────────────────

tab_query, tab_admin = st.tabs(["🔍  TROUBLESHOOT", "⚙️  ADMIN"])


# ── TROUBLESHOOT ─────────────────────────────────────────────────────────────

with tab_query:
    st.markdown("## Troubleshooting Assistant")
    st.markdown(
        '<div style="color:#5a6380;font-size:0.85rem;margin-bottom:24px">'
        "Select a machine and describe the issue. Answers come strictly from uploaded manuals."
        "</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 2])
    with c1:
        sel_machine = st.selectbox("Select Machine", ["All Machines"] + machines)
    with c2:
        query_text = st.text_area(
            "Describe the Issue",
            placeholder="e.g. Motor overheating, battery not charging, spindle vibration...",
            height=100,
        )

    if st.button("▶  DIAGNOSE"):
        if not query_text.strip():
            st.warning("Please enter a problem description.")
        elif not machines:
            st.error("No machines indexed. Upload manuals via the Admin tab first.")
        else:
            mf = "all" if sel_machine == "All Machines" else sel_machine
            with st.spinner("Searching knowledge base..."):
                resp = api_post("/query", json={"query": query_text, "machine_name": mf})

            if "error" in resp:
                st.error(f"Query failed: {resp['error']}")
            else:
                results = resp.get("results", [])
                if not results:
                    st.warning(
                        "No relevant content found above the threshold. "
                        "Try rephrasing, or check the correct manual is uploaded."
                    )
                else:
                    st.markdown(f"### Results — *{query_text}*")
                    for res in results:
                        render_result(res)


# ── ADMIN ────────────────────────────────────────────────────────────────────

with tab_admin:
    st.markdown("## Knowledge Base Management")

    col_pdf, col_xls = st.columns(2)

    # Upload PDF
    with col_pdf:
        st.markdown("### 📘 Upload Manual (PDF)")
        pdf_machine = st.text_input("Machine Name", placeholder="e.g. Pioneer 3", key="k_pdf_machine")
        pdf_file    = st.file_uploader("Select PDF", type=["pdf"], key="k_pdf_file")
        if st.button("Upload & Index PDF", key="k_btn_pdf"):
            if not pdf_machine.strip():
                st.error("Machine name required.")
            elif pdf_file is None:
                st.error("Select a PDF file.")
            else:
                with st.spinner("Parsing and indexing PDF..."):
                    r = requests.post(
                        f"{API_BASE}/admin/upload/pdf",
                        data={"machine_name": pdf_machine.strip()},
                        files={"file": (pdf_file.name, pdf_file.getvalue(), "application/pdf")},
                        timeout=180,
                    )
                if r.status_code == 200:
                    d   = r.json()
                    msg = f"✓ Indexed {d['chunks_stored']} chunks from **{d['filename']}**"
                    if d.get("old_chunks_replaced"):
                        msg += f" (replaced {d['old_chunks_replaced']} old chunks)"
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(f"Upload failed: {r.text}")

    # Upload Excel
    with col_xls:
        st.markdown("### 📊 Upload Repair Log (Excel / CSV)")
        xls_machine = st.text_input("Machine Name", placeholder="e.g. Pioneer 3", key="k_xls_machine")
        xls_file    = st.file_uploader("Select File", type=["xlsx", "xls", "csv"], key="k_xls_file")
        if st.button("Upload & Index Log", key="k_btn_xls"):
            if not xls_machine.strip():
                st.error("Machine name required.")
            elif xls_file is None:
                st.error("Select a file.")
            else:
                with st.spinner("Parsing and indexing..."):
                    r = requests.post(
                        f"{API_BASE}/admin/upload/excel",
                        data={"machine_name": xls_machine.strip()},
                        files={"file": (xls_file.name, xls_file.getvalue())},
                        timeout=60,
                    )
                if r.status_code == 200:
                    d = r.json()
                    st.success(f"✓ Indexed {d['rows_stored']} rows from **{d['filename']}**")
                    st.rerun()
                else:
                    st.error(f"Upload failed: {r.text}")

    st.markdown("---")

    # Knowledge base status
    st.markdown("### 📋 Current Knowledge Base")
    stats = api_get("/admin/stats")
    if stats:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Chunks", stats.get("total_chunks", 0))
        m2.metric("Machines",     len(stats.get("machines", [])))
        m3.metric("Files",        len(stats.get("files", [])))

        files = stats.get("files", [])
        if files:
            st.markdown("**Indexed Files:**")
            for f in files:
                icon = "📘" if f["type"] == "pdf" else "📊"
                row_left, row_right = st.columns([5, 1])
                with row_left:
                    st.markdown(
                        f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.8rem;'
                        f'color:#7ba8f7;padding:6px 0">'
                        f'{icon} {f["filename"]} '
                        f'<span style="color:#4f8ef7">→ {f["machine"]}</span> '
                        f'<span style="color:#5a6380">({f["chunks"]} chunks)</span></div>',
                        unsafe_allow_html=True,
                    )
                with row_right:
                    if st.button("🗑️", key=f"del_{f['filename']}", help=f"Delete {f['filename']}"):
                        st.session_state[f"confirm_{f['filename']}"] = True

                if st.session_state.get(f"confirm_{f['filename']}"):
                    st.warning(f"Delete **{f['filename']}** ({f['chunks']} chunks)?")
                    yes, no = st.columns(2)
                    with yes:
                        if st.button("Yes, delete", key=f"yes_{f['filename']}"):
                            ep = (
                                f"/admin/delete/pdf/{f['filename']}"
                                if f["type"] == "pdf"
                                else f"/admin/delete/excel/{f['filename']}"
                            )
                            dr = api_delete(ep)
                            if "error" in dr:
                                st.error(dr["error"])
                            else:
                                st.success(
                                    f"Deleted {f['filename']} "
                                    f"({dr.get('chunks_removed', 0)} chunks removed)"
                                )
                            del st.session_state[f"confirm_{f['filename']}"]
                            st.rerun()
                    with no:
                        if st.button("Cancel", key=f"no_{f['filename']}"):
                            del st.session_state[f"confirm_{f['filename']}"]
                            st.rerun()
    else:
        st.info("No documents indexed yet.")

    st.markdown("---")

    # Reset
    st.markdown("### ⚠️ Reset Entire Knowledge Base")
    st.markdown(
        '<div style="color:#5a6380;font-size:0.82rem;margin-bottom:8px">'
        "Permanently deletes all indexed files, chunks, and uploaded documents."
        "</div>",
        unsafe_allow_html=True,
    )

    if st.button("🗑️ Reset Everything", key="k_reset_init"):
        st.session_state["confirm_reset"] = True

    if st.session_state.get("confirm_reset"):
        st.error("⚠️ This will permanently delete everything. Are you sure?")
        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("Yes, wipe all data", key="k_reset_yes"):
                dr = api_delete("/admin/reset")
                if "error" in dr:
                    st.error(dr["error"])
                else:
                    st.success("Knowledge base reset complete.")
                del st.session_state["confirm_reset"]
                st.rerun()
        with rc2:
            if st.button("Cancel", key="k_reset_no"):
                del st.session_state["confirm_reset"]
                st.rerun()
