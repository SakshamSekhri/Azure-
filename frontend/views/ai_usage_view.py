import streamlit as st
import streamlit.components.v1 as components
from frontend.components.api_client import api

TABLE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif; box-sizing: border-box; }
.styled-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.styled-table th { background-color: #f8fafc; border-bottom: 2px solid #e2e8f0; text-align: left; padding: 0.75rem; font-weight: 600; color: #475569; }
.styled-table td { padding: 0.75rem; border-bottom: 1px solid #e2e8f0; color: #1e293b; }
.styled-table tr:hover td { background-color: #f8fafc; }
.metric-badge { display: inline-block; font-size: 0.78rem; font-weight: 600; padding: 0.2rem 0.55rem; border-radius: 9999px; }
.badge-high   { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.badge-medium { background: #fef9c3; color: #854d0e; border: 1px solid #fef08a; }
.badge-low    { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.badge-info   { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
code { background: #f1f5f9; border-radius: 4px; padding: 0.15rem 0.4rem; font-size: 0.8rem; color: #0f172a; }
</style>
"""


def render_ai_usage_view():
    st.markdown("### 💳 AI Credit Control & Audit Dashboard")
    st.markdown("Transparent real-time telemetry on Azure AI Foundry consumption, SHA-256 cache hits, and token usage.")

    try:
        usage = api.get_ai_usage()
    except Exception as e:
        st.error(f"Failed to load AI usage: {str(e)}")
        return

    # Top Metrics Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total AI Requests", usage.get("total_operations", 0))
    with c2:
        hit_rate = usage.get("cache_hit_rate_percentage", 0.0)
        st.metric("Cache Hit Rate", f"{hit_rate}%", delta=f"{usage.get('cached_calls', 0)} calls saved")
    with c3:
        st.metric("Tokens Consumed", f"{usage.get('total_tokens_used', 0):,}")
    with c4:
        cost = usage.get("estimated_cost_usd", 0.0)
        st.metric("Est. Azure Cost", f"${cost:.4f}")

    st.markdown("---")

    col_breakdown, col_info = st.columns([1, 1])
    with col_breakdown:
        st.markdown("##### 📊 Operations Breakdown by Type")
        ops_by_type = usage.get("operations_by_type", {})
        if ops_by_type:
            for op_type, count in ops_by_type.items():
                st.markdown(f"- **{op_type}**: `{count}` operations")
        else:
            st.info("No AI operations triggered yet.")

    with col_info:
        st.markdown("##### 🔒 Credit Control Guardrails Enforced")
        st.markdown("""
        - **SHA-256 Prompt Hashing**: Identical requests instantly return cached results with **0 new tokens**.
        - **Single Persistent Agent**: Azure AI Foundry Agent Service runs with one persistent agent ID.
        - **One-Shot Interaction**: Assessment generation and diagnostic result analyses are evaluated in single batch passes—no token-wasting conversation loops.
        - **Strict Error Transparency**: If Azure AI Foundry fails or credentials expire, clear errors are returned immediately without silently serving stale or fake data.
        """)

    st.markdown("---")

    # Recent Audit Log Table
    st.markdown("##### 📜 Recent AI Operation Audit Trail")
    recent = usage.get("recent_operations", [])
    if recent:
        table_rows = []
        for op in recent:
            status_style = "badge-high" if op.get("status") == "SUCCESS" else ("badge-info" if op.get("status") == "CACHED" else "badge-low")
            hash_short = op.get("prompt_hash", "")[:12] + "..."
            duration = f"{op.get('duration_ms', 0):.1f} ms"

            row_html = f"""
            <tr>
                <td><code>{op.get('operation_id')[:8]}...</code></td>
                <td><strong>{op.get('operation_type')}</strong></td>
                <td><span class="metric-badge {status_style}">{op.get('status')}</span></td>
                <td><code>{hash_short}</code></td>
                <td>{op.get('tokens_used')}</td>
                <td>{duration}</td>
                <td>{op.get('created_at')}</td>
            </tr>
            """
            table_rows.append(row_html)

        html_table = f"""
        <table class="styled-table">
            <thead>
                <tr>
                    <th>Op ID</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>SHA-256 Hash</th>
                    <th>Tokens</th>
                    <th>Latency</th>
                    <th>Timestamp</th>
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
        """
        components.html(TABLE_CSS + html_table, height=max(200, 50 * len(recent) + 60), scrolling=True)
    else:
        st.caption("No operations logged yet.")
