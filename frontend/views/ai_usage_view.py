import streamlit as st
from frontend.components.api_client import api
from frontend.components.ui import (
    render_page_header,
    render_section_header,
    render_progress_bar,
    render_status_badge,
    render_empty_state,
    render_styled_table,
    render_html
)


def render_ai_usage_view():
    render_page_header(
        title="Usage & Credit Audit",
        subtitle="Real-time telemetry on Azure AI Foundry consumption, SHA-256 cache hits, and token usage."
    )

    try:
        usage = api.get_ai_usage()
    except Exception as e:
        render_empty_state("Telemetry Offline", f"Could not load AI usage metrics: {str(e)}", icon="⚠️")
        return

    cost = usage.get("estimated_cost_usd", 0.0)
    budget = 10.00
    used_pct = min(100.0, round((cost / budget) * 100.0, 2))
    remaining = max(0.0, budget - cost)

    # -------------------------------------------------------------
    # 1. TOP USAGE BUDGET PANEL
    # -------------------------------------------------------------
    render_html(
        f"""
        <div class="saas-panel">
            <div style="font-size: 0.72rem; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.2rem;">
                AI CREDIT CONSUMPTION
            </div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap;">
                <h2 style="margin: 0; font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">
                    &dollar;{cost:.4f} <span style="font-size: 0.95rem; font-weight: 500; color: var(--text-secondary);">/ &dollar;{budget:.2f} Allocated</span>
                </h2>
                <span style="font-size: 0.85rem; font-weight: 600; color: #10B981;">&dollar;{remaining:.4f} remaining</span>
            </div>
            <div class="saas-bar-track" style="height: 7px; margin-top: 0.5rem; margin-bottom: 0.35rem;">
                <div class="saas-bar-fill" style="width: {used_pct}%; background-color: var(--accent);"></div>
            </div>
            <div style="font-size: 0.78rem; color: var(--text-secondary);">
                Telemetry computed strictly from token usage via Azure AI Foundry and local cache audits.
            </div>
        </div>
        """
    )

    # -------------------------------------------------------------
    # 2. KEY METRICS ROW
    # -------------------------------------------------------------
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total AI Operations", usage.get("total_operations", 0))
    with c2:
        hit_rate = round(usage.get("cache_hit_rate_percentage", 0.0), 1)
        st.metric("Cache Hit Rate", f"{hit_rate}%", delta=f"{usage.get('cached_calls', 0)} calls saved (0 tokens)")
    with c3:
        st.metric("Tokens Consumed", f"{usage.get('total_tokens_used', 0):,}")

    st.write("")
    st.markdown("---")

    # -------------------------------------------------------------
    # 3. USAGE BY SERVICE & OPERATION TYPE
    # -------------------------------------------------------------
    col_ops, col_rules = st.columns(2)

    with col_ops:
        render_section_header("Usage by Operation Type")
        ops = usage.get("operations_by_type", {})
        total_ops = sum(ops.values()) if ops else 1

        if ops:
            for op_name, count in ops.items():
                pct = round((count / total_ops) * 100.0, 1)
                render_html(
                    f"""
                    <div style="margin-bottom: 0.6rem;">
                        <div style="display: flex; justify-content: space-between; font-size: 0.84rem; margin-bottom: 0.2rem;">
                            <span style="font-weight: 600; color: var(--text-primary);">{op_name}</span>
                            <span style="color: var(--text-secondary);">{count} calls ({pct}%)</span>
                        </div>
                        <div class="saas-bar-track" style="height: 5px;">
                            <div class="saas-bar-fill" style="width: {pct}%; background-color: var(--accent);"></div>
                        </div>
                    </div>
                    """
                )
        else:
            st.caption("No operations recorded yet.")

    with col_rules:
        render_section_header("Active Credit Control Guardrails")
        st.markdown(
            "- **SHA-256 Prompt Hashing**: Identical queries return cached results instantly with **0 tokens consumed**.\n"
            "- **Single Persistent Agent**: Azure AI Foundry Agent runs with persistent state, preventing redundant initializations.\n"
            "- **Batch Evaluation Pass**: Question generation and diagnostic analyses execute in single passes with no conversational token waste.\n"
            "- **Transparent Failure Handling**: If API credentials expire, requests fail fast with clear errors instead of burning retries."
        )

    st.write("")
    st.markdown("---")

    # -------------------------------------------------------------
    # 4. RECENT AUDIT TRAIL TABLE (ZERO IFRAMES)
    # -------------------------------------------------------------
    render_section_header("Recent AI Operation Audit Log")
    recent = usage.get("recent_operations", [])
    if recent:
        headers = ["Operation ID", "Type", "Status", "Prompt Hash", "Tokens", "Duration", "Timestamp"]
        rows = []
        for op in recent[:15]:
            status = op.get("status", "SUCCESS")
            status_var = "success" if status == "SUCCESS" else ("info" if status == "CACHED" else "danger")
            status_badge = render_status_badge(status, status_var)
            hash_short = f"<code>{op.get('prompt_hash', '')[:10]}...</code>"
            dur = f"{op.get('duration_ms', 0):.1f} ms"

            rows.append([
                f"<code>{op.get('operation_id', '')[:8]}...</code>",
                f"<strong>{op.get('operation_type')}</strong>",
                status_badge,
                hash_short,
                op.get("tokens_used", 0),
                dur,
                str(op.get("created_at", ""))[:16].replace("T", " ")
            ])
        render_styled_table(headers, rows)
    else:
        st.caption("No recent operations logged.")
