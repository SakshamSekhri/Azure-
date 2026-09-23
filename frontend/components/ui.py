"""Reusable UI component helpers for the Placement Preparation Platform.
Adheres to the Linear + Vercel design system specifications.
Guarantees zero raw HTML code leakages by stripping whitespace before rendering.
"""

from typing import List, Dict, Any, Optional
import streamlit as st


def clean_html(html_str: str) -> str:
    """Strip leading and trailing whitespace from each line so Markdown never treats HTML as an indented code block.
    Also protects dollar signs from accidental KaTeX LaTeX math block triggers.
    """
    if not html_str:
        return ""
    safe_str = str(html_str).replace("$", "&#36;")
    return "\n".join(line.strip() for line in safe_str.splitlines() if line.strip())


def render_html(html_str: str, sidebar: bool = False):
    """Renders raw HTML safely into Streamlit without accidental code block formatting."""
    cleaned = clean_html(html_str)
    if sidebar:
        st.sidebar.markdown(cleaned, unsafe_allow_html=True)
    else:
        st.markdown(cleaned, unsafe_allow_html=True)


def render_page_header(
    title: str,
    subtitle: Optional[str] = None,
    badge_text: Optional[str] = None,
    badge_variant: str = "neutral"
):
    """Render a clean, standard page header with title, optional badge, and subtitle."""
    badge_html = ""
    if badge_text:
        badge_html = f"&nbsp;&nbsp;<span class='status-badge badge-{badge_variant}'>{badge_text}</span>"

    html = f"""
    <div style="margin-bottom: 1.25rem;">
        <div style="display: flex; align-items: center; flex-wrap: wrap;">
            <h1 class="saas-page-title">{title}</h1>
            {badge_html}
        </div>
        {f'<div class="saas-page-subtitle">{subtitle}</div>' if subtitle else ''}
    </div>
    """
    render_html(html)


def render_section_header(title: str, subtitle: Optional[str] = None):
    """Render a clean section header."""
    html = f"""
    <div style="margin-top: 1.25rem; margin-bottom: 0.65rem;">
        <div class="saas-section-title">{title}</div>
        {f'<div style="font-size: 0.82rem; color: #64748B; margin-top: 0.1rem;">{subtitle}</div>' if subtitle else ''}
    </div>
    """
    render_html(html)


def render_progress_bar(percentage: float, label: Optional[str] = None, color: Optional[str] = None, height: int = 6):
    """Render a clean inline progress bar without Streamlit widget bloat."""
    clamped_pct = max(0.0, min(100.0, float(percentage)))
    if not color:
        if clamped_pct >= 80.0:
            color = "#10B981"  # Emerald
        elif clamped_pct >= 60.0:
            color = "#F59E0B"  # Amber
        else:
            color = "#EF4444"  # Rose

    label_html = ""
    if label:
        label_html = f"""
        <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 0.25rem;">
            <span style="font-weight: 500; color: var(--text-primary);">{label}</span>
            <span style="font-weight: 600; color: var(--text-secondary);">{clamped_pct:.1f}%</span>
        </div>
        """

    html = f"""
    <div style="margin-bottom: 0.6rem;">
        {label_html}
        <div class="saas-bar-track" style="height: {height}px;">
            <div class="saas-bar-fill" style="width: {clamped_pct}%; background-color: {color};"></div>
        </div>
    </div>
    """
    render_html(html)


def render_status_badge(text: str, variant: str = "neutral") -> str:
    """Return inline HTML for a micro status badge."""
    return f"<span class='status-badge badge-{variant}'>{text}</span>"


def render_empty_state(title: str, description: str, icon: str = "📋"):
    """Render a clean, minimal empty state."""
    html = f"""
    <div style="text-align: center; padding: 3rem 1.5rem; background: var(--surface); border: 1px dashed var(--border); border-radius: 10px; margin: 1rem 0;">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
        <div style="font-size: 0.98rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem;">{title}</div>
        <div style="font-size: 0.85rem; color: var(--text-secondary); max-width: 420px; margin: 0 auto;">{description}</div>
    </div>
    """
    render_html(html)


def render_styled_table(headers: List[str], rows: List[List[Any]]):
    """Render a sleek, zero-iframe responsive HTML table."""
    th_cells = "".join([f"<th>{h}</th>" for h in headers])
    tr_rows = []
    for r in rows:
        td_cells = "".join([f"<td>{cell}</td>" for cell in r])
        tr_rows.append(f"<tr>{td_cells}</tr>")

    html = f"""
    <div style="overflow-x: auto; margin-bottom: 1.25rem;">
        <table class="saas-table">
            <thead>
                <tr>{th_cells}</tr>
            </thead>
            <tbody>
                {''.join(tr_rows)}
            </tbody>
        </table>
    </div>
    """
    render_html(html)
