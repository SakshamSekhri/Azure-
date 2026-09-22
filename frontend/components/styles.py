import streamlit as st


def apply_custom_styles():
    custom_css = """
    <style>
    /* Google / Modern Clean Design Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Modern Cards */
    .app-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .app-card:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
    }

    /* Dark Mode Compatibility */
    @media (prefers-color-scheme: dark) {
        .app-card {
            background: #1e293b;
            border-color: #334155;
            color: #f8fafc;
        }
    }

    /* Custom Metric Display */
    .metric-badge {
        display: inline-block;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        margin-right: 0.4rem;
    }
    .badge-high {
        background-color: #dcfce7;
        color: #166534;
        border: 1px solid #bbf7d0;
    }
    .badge-medium {
        background-color: #fef9c3;
        color: #854d0e;
        border: 1px solid #fef08a;
    }
    .badge-low {
        background-color: #fee2e2;
        color: #991b1b;
        border: 1px solid #fecaca;
    }
    .badge-info {
        background-color: #e0f2fe;
        color: #0369a1;
        border: 1px solid #bae6fd;
    }

    /* Next Action Banner */
    .action-banner {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    .action-banner h4 {
        margin: 0 0 0.4rem 0;
        font-weight: 700;
        color: white !important;
    }
    .action-banner p {
        margin: 0;
        opacity: 0.95;
        font-size: 0.95rem;
    }

    /* Credit Control Pill */
    .credit-pill {
        display: inline-flex;
        align-items: center;
        background-color: #f1f5f9;
        border: 1px solid #cbd5e1;
        border-radius: 20px;
        padding: 0.2rem 0.75rem;
        font-size: 0.75rem;
        font-weight: 600;
        color: #475569;
        margin-bottom: 0.5rem;
    }

    /* Tables */
    .styled-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }
    .styled-table th {
        background-color: #f8fafc;
        border-bottom: 2px solid #e2e8f0;
        text-align: left;
        padding: 0.75rem;
        font-weight: 600;
        color: #475569;
    }
    .styled-table td {
        padding: 0.75rem;
        border-bottom: 1px solid #e2e8f0;
    }

    /* Source Citation Card */
    .citation-box {
        background-color: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 0.75rem 1rem;
        margin-top: 0.75rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.85rem;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
