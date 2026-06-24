import streamlit as st
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Page config ────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Requirement Validator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
  .score-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 24px;
    border-radius: 16px;
    text-align: center;
    margin-bottom: 12px;
  }
  .score-number { font-size: 64px; font-weight: 700; line-height: 1; }
  .score-label  { font-size: 14px; opacity: 0.85; margin-top: 4px; }
  .metric-card  {
    background: #f8faff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
  }
  .metric-value { font-size: 32px; font-weight: 700; }
  .metric-label { font-size: 12px; color: #64748b; margin-top: 2px; }
  .severity-critical { color: #dc2626; font-weight: 700; }
  .severity-high     { color: #ea580c; font-weight: 600; }
  .severity-medium   { color: #d97706; font-weight: 600; }
  .severity-low      { color: #16a34a; font-weight: 500; }
  .issue-card {
    border-left: 4px solid #e2e8f0;
    padding: 12px 16px;
    margin-bottom: 8px;
    background: #fafafa;
    border-radius: 0 8px 8px 0;
  }
  .issue-card.critical { border-left-color: #dc2626; background: #fff5f5; }
  .issue-card.high     { border-left-color: #ea580c; background: #fff7ed; }
  .issue-card.medium   { border-left-color: #d97706; background: #fffbeb; }
  .issue-card.low      { border-left-color: #16a34a; background: #f0fdf4; }
  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    margin-right: 6px;
  }
  .badge-critical { background: #fee2e2; color: #dc2626; }
  .badge-high     { background: #ffedd5; color: #ea580c; }
  .badge-medium   { background: #fef3c7; color: #d97706; }
  .badge-low      { background: #dcfce7; color: #16a34a; }
  .section-title  { font-size: 18px; font-weight: 600; color: #1e293b; margin: 16px 0 8px; }
</style>
""", unsafe_allow_html=True)


def severity_badge(severity: str) -> str:
    return f'<span class="badge badge-{severity}">{severity}</span>'


def render_issue_card(issue: dict) -> None:
    sev = issue.get("severity", "low")
    st.markdown(
        f"""
        <div class="issue-card {sev}">
          {severity_badge(sev)}
          <span style="font-size:11px;color:#64748b;">{issue.get("category","")}</span>
          {'  · <span style="font-size:11px;color:#94a3b8;">📍 ' + issue.get("location","") + '</span>' if issue.get("location") else ''}
          <div style="font-weight:600;margin:4px 0 2px;">{issue.get("title","")}</div>
          <div style="font-size:13px;color:#475569;">{issue.get("description","")}</div>
          <div style="font-size:12px;color:#64748b;margin-top:6px;">
            💡 <em>{issue.get("recommendation","")}</em>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def call_backend(requirements: str, figma_url: str) -> dict:
    with httpx.Client(timeout=150) as client:
        resp = client.post(
            f"{BACKEND_URL}/api/v1/analyze",
            json={"requirements": requirements, "figma_url": figma_url},
        )
    resp.raise_for_status()
    return resp.json()


def render_dashboard(report: dict) -> None:
    score = report["overall_score"]
    coverage = report["requirement_coverage"]

    # ── Top metrics row ─────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns([1.4, 1, 1, 1, 1])

    with col1:
        st.markdown(
            f"""
            <div class="score-card">
              <div class="score-number">{score}</div>
              <div class="score-label">Overall Score / 100</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
              <div class="metric-value">{coverage:.0f}%</div>
              <div class="metric-label">Requirement Coverage</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
              <div class="metric-value">{report["total_issues"]}</div>
              <div class="metric-label">Total Issues</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
              <div class="metric-value severity-critical">{report["critical_count"]}</div>
              <div class="metric-label">Critical</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col5:
        st.markdown(
            f"""
            <div class="metric-card">
              <div class="metric-value severity-high">{report["high_count"]}</div>
              <div class="metric-label">High</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Secondary counts ─────────────────────────────────────────
    col_m, col_l, col_screens, col_components = st.columns(4)
    with col_m:
        st.metric("⚠️ Medium", report["medium_count"])
    with col_l:
        st.metric("ℹ️ Low", report["low_count"])
    with col_screens:
        st.metric("🖥 Screens Found", len(report.get("screens_found", [])))
    with col_components:
        st.metric("🧩 Components Found", len(report.get("components_found", [])))

    st.divider()

    # ── AI Summary ───────────────────────────────────────────────
    st.markdown('<div class="section-title">🤖 AI Summary</div>', unsafe_allow_html=True)
    st.info(report.get("ai_summary", "No summary available."))

    # ── Issues list ──────────────────────────────────────────────
    issues = report.get("issues", [])
    if issues:
        st.markdown('<div class="section-title">🔍 Detected Issues</div>', unsafe_allow_html=True)

        # Filter controls
        all_cats = sorted({i.get("category", "") for i in issues})
        filter_col1, filter_col2 = st.columns([1, 3])
        with filter_col1:
            filter_sev = st.multiselect(
                "Severity",
                ["critical", "high", "medium", "low"],
                default=["critical", "high", "medium", "low"],
                key="sev_filter",
            )
        with filter_col2:
            filter_cat = st.multiselect(
                "Category",
                all_cats,
                default=all_cats,
                key="cat_filter",
            )

        filtered = [
            i for i in issues
            if i.get("severity") in filter_sev and i.get("category") in filter_cat
        ]

        st.caption(f"Showing {len(filtered)} of {len(issues)} issues")
        for issue in filtered:
            render_issue_card(issue)
    else:
        st.success("No issues detected! The design closely matches the requirements.")

    # ── Screens & components ─────────────────────────────────────
    if report.get("screens_found") or report.get("components_found"):
        st.divider()
        e1, e2 = st.columns(2)
        with e1:
            with st.expander(f"📋 Screens Found ({len(report.get('screens_found',[]))})"):
                for s in report.get("screens_found", []):
                    st.write(f"• {s}")
        with e2:
            with st.expander(f"🧩 Components Found ({len(report.get('components_found',[]))})"):
                for c in report.get("components_found", []):
                    st.write(f"• {c}")


# ── Main UI ─────────────────────────────────────────────────────
st.title("🔍 AI Requirement Validation Platform")
st.markdown(
    "Compare your **software requirements** against a **Figma design** and get a detailed AI-powered mismatch report."
)

with st.form("analyze_form"):
    requirements = st.text_area(
        "📋 Software Requirements",
        height=220,
        placeholder=(
            "Paste your requirements here. Example:\n"
            "1. User can register with email and password\n"
            "2. Login screen with forgot password link\n"
            "3. Dashboard showing recent orders\n"
            "4. Product listing with search and filters\n"
            "5. Cart with quantity update and remove\n"
            "6. Checkout with address form and payment\n"
            "7. Order confirmation screen\n"
            "8. Profile page with edit capabilities"
        ),
    )
    figma_url = st.text_input(
        "🎨 Figma Design URL",
        placeholder="https://www.figma.com/file/XXXXXXXXXX/Your-Design",
    )
    submitted = st.form_submit_button("🚀 Analyze", use_container_width=True, type="primary")

if submitted:
    if not requirements.strip():
        st.error("Please enter your software requirements.")
    elif not figma_url.strip():
        st.error("Please enter a Figma design URL.")
    elif "figma.com" not in figma_url:
        st.error("URL must be a valid Figma link (figma.com).")
    else:
        with st.spinner("🔄 Analyzing requirements against Figma design... This may take up to 60 seconds."):
            try:
                result = call_backend(requirements.strip(), figma_url.strip())
                if result.get("success") and result.get("report"):
                    st.success("✅ Analysis complete!")
                    render_dashboard(result["report"])
                else:
                    st.error(f"Analysis failed: {result.get('error', 'Unknown error')}")
            except httpx.ConnectError:
                st.error(
                    "❌ Cannot connect to the backend. "
                    "Make sure FastAPI is running: `uvicorn backend.api.app:app --reload`"
                )
            except httpx.HTTPStatusError as e:
                st.error(f"❌ Backend error {e.response.status_code}: {e.response.text[:300]}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
