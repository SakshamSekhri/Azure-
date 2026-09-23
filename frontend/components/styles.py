import streamlit as st


def apply_custom_styles(theme: str = "light"):
    """Apply centralized SaaS CSS design tokens supporting Light Mode (White Screen)
    and Dark Mode (Black Screen) with full contrast across all Streamlit components.
    """
    is_dark = (str(theme).lower() == "dark")

    # Light palette tokens
    if not is_dark:
        tokens = """
        --bg: #F8FAFC;
        --surface: #FFFFFF;
        --surface-hover: #F1F5F9;
        --text-primary: #0F172A;
        --text-secondary: #64748B;
        --text-muted: #94A3B8;
        --border: #E2E8F0;
        --border-subtle: #F1F5F9;
        --accent: #6366F1;
        --accent-hover: #4F46E5;
        --accent-light: #EEF2FF;
        --success: #10B981;
        --success-light: #ECFDF5;
        --warning: #F59E0B;
        --warning-light: #FFFBEB;
        --danger: #EF4444;
        --danger-light: #FEF2F2;

        --badge-success-text: #065F46;
        --badge-success-border: #A7F3D0;
        --badge-warning-text: #92400E;
        --badge-warning-border: #FDE68A;
        --badge-danger-text: #991B1B;
        --badge-danger-border: #FECACA;
        --badge-info-text: #3730A3;
        --badge-info-border: #C7D2FE;
        --badge-neutral-bg: #F1F5F9;
        --badge-neutral-text: #475569;
        """
        sidebar_bg = "#FFFFFF"
        chat_user_bg = "#EEF2FF"
        chat_user_text = "#1E1B4B"
    else:
        # Dark / Black screen palette tokens (Linear + Vercel aesthetic)
        tokens = """
        --bg: #090D16;
        --surface: #111827;
        --surface-hover: #1F2937;
        --text-primary: #F8FAFC;
        --text-secondary: #94A3B8;
        --text-muted: #64748B;
        --border: #1E293B;
        --border-subtle: #161F30;
        --accent: #818CF8;
        --accent-hover: #6366F1;
        --accent-light: rgba(99, 102, 241, 0.2);
        --success: #34D399;
        --success-light: rgba(16, 185, 129, 0.15);
        --warning: #FBBF24;
        --warning-light: rgba(245, 158, 11, 0.15);
        --danger: #F87171;
        --danger-light: rgba(239, 68, 68, 0.15);

        --badge-success-text: #34D399;
        --badge-success-border: rgba(52, 211, 153, 0.35);
        --badge-warning-text: #FBBF24;
        --badge-warning-border: rgba(251, 191, 36, 0.35);
        --badge-danger-text: #F87171;
        --badge-danger-border: rgba(248, 113, 113, 0.35);
        --badge-info-text: #A5B4FC;
        --badge-info-border: rgba(165, 180, 252, 0.35);
        --badge-neutral-bg: #1E293B;
        --badge-neutral-text: #94A3B8;
        """
        sidebar_bg = "#0B0F19"
        chat_user_bg = "#4338CA"
        chat_user_text = "#FFFFFF"

    custom_css = f"""
    <style>
    /* -------------------------------------------------------------
       GLOBAL DESIGN SYSTEM (Linear + Vercel Modern AI SaaS)
       ------------------------------------------------------------- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

    :root {{
        {tokens}
    }}

    /* Base typography applied safely to document without breaking Material Symbols */
    html, body {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: var(--text-primary);
        background-color: var(--bg);
        -webkit-font-smoothing: antialiased;
    }}

    input, select, textarea, button {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}

    .stMarkdown, .stText, .saas-page-title, .saas-page-subtitle, .saas-section-title {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}

    /* -------------------------------------------------------------
       STREAMLIT MATERIAL SYMBOLS & ICONS PRESERVATION
       Protects Material Symbols from being overridden by sans-serif fonts,
       ensuring ligatures (expand_more, check, etc.) render as glyphs.
       ------------------------------------------------------------- */
    [data-testid="stIconMaterial"],
    .material-symbols-rounded,
    [class*="material-symbols"],
    span[data-testid="stIconMaterial"],
    [data-testid="stPopover"] [data-testid="stIconMaterial"],
    [data-testid="stExpander"] [data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"] {{
        font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
        font-weight: 400 !important;
        font-style: normal !important;
        font-size: 1.25rem !important;
        line-height: 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        direction: ltr !important;
        -webkit-font-feature-settings: 'liga' 1 !important;
        font-feature-settings: 'liga' 1 !important;
        font-variant-ligatures: normal !important;
        -webkit-font-smoothing: antialiased !important;
        text-rendering: optimizeLegibility !important;
        flex-shrink: 0 !important;
        min-width: 1.15rem !important;
        max-width: 1.35rem !important;
        overflow: hidden !important;
    }}

    /* Streamlit App Background Containers */
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > section,
    .stApp,
    [data-testid="stHeader"],
    [data-testid="stBottom"],
    [data-testid="stBottom"] > div,
    [data-testid="stBottomBlockContainer"],
    .stBottom {{
        background-color: var(--bg) !important;
        color: var(--text-primary) !important;
    }}

    /* Container Spacing & Layout */
    .block-container {{
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
        max-width: 1240px !important;
    }}

    /* Typography Hierarchy */
    h1, .saas-page-title {{
        font-size: 1.85rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.025em !important;
        color: var(--text-primary) !important;
        margin: 0 0 0.35rem 0 !important;
        line-height: 1.25 !important;
    }}

    .saas-page-subtitle {{
        font-size: 0.92rem !important;
        color: var(--text-secondary) !important;
        margin-bottom: 1.5rem !important;
        line-height: 1.5 !important;
        font-weight: 400 !important;
    }}

    h2, h3, .saas-section-title {{
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.015em !important;
        color: var(--text-primary) !important;
        margin: 1.2rem 0 0.5rem 0 !important;
    }}

    h4, h5 {{
        font-size: 0.98rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        margin: 0.8rem 0 0.4rem 0 !important;
    }}

    p:not(button *), label:not(button *), span:not([data-testid="stIconMaterial"]):not([class*="material-symbols"]):not([translate="no"]):not(button *) {{
        font-size: 0.88rem;
        color: var(--text-primary);
    }}

    /* Streamlit Sidebar Redesign (Linear / Vercel Navigation) */
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
        border-right: 1px solid var(--border) !important;
        box-shadow: none !important;
    }}

    [data-testid="stSidebar"] .block-container {{
        padding-top: 1.5rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
    }}

    /* Hide standard radio circles for a sleek menu link feel */
    [data-testid="stSidebar"] [data-testid="stRadio"] > label {{
        display: none !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {{
        gap: 0.15rem !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label {{
        background: transparent;
        padding: 0.48rem 0.75rem !important;
        border-radius: 6px !important;
        font-size: 0.84rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        transition: all 0.15s ease !important;
        cursor: pointer !important;
        margin: 0 !important;
        border: 1px solid transparent !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:hover {{
        background: var(--surface-hover) !important;
        color: var(--text-primary) !important;
    }}

    /* Active navigation indicator */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"],
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {{
        background: var(--accent-light) !important;
        color: var(--accent) !important;
        font-weight: 600 !important;
        border-left: 3px solid var(--accent) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] input[type="radio"] {{
        display: none !important;
    }}

    /* Sidebar Group Section Headers */
    .sidebar-section-label {{
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted);
        margin: 1.1rem 0 0.35rem 0.5rem;
    }}

    /* Modern Buttons */
    button[kind="primary"],
    button[kind="primary"] *,
    button[kind="primary"] p,
    button[kind="primary"] span,
    button[kind="primary"] div,
    .stButton > button[kind="primary"],
    .stButton > button[kind="primary"] *,
    .stButton > button[kind="primary"] p,
    .stButton > button[kind="primary"] span,
    .stButton > button[kind="primary"] div,
    button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-primary"] *,
    button[data-testid="stBaseButton-primary"] p,
    button[data-testid="stBaseButton-primary"] span,
    button[data-testid="stBaseButton-primary"] div {{
        color: #FFFFFF !important;
    }}

    button[kind="primary"],
    .stButton > button[kind="primary"],
    button[data-testid="stBaseButton-primary"] {{
        background-color: var(--accent) !important;
        border: 1px solid var(--accent) !important;
        border-radius: 7px !important;
        font-weight: 500 !important;
        font-size: 0.86rem !important;
        padding: 0.42rem 0.95rem !important;
        box-shadow: 0 1px 2px 0 rgba(99, 102, 241, 0.18) !important;
        transition: all 0.15s ease !important;
    }}

    button[kind="primary"]:hover,
    .stButton > button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {{
        background-color: var(--accent-hover) !important;
        border-color: var(--accent-hover) !important;
        box-shadow: 0 2px 4px 0 rgba(99, 102, 241, 0.25) !important;
    }}

    button[kind="secondary"],
    .stButton > button:not([kind="primary"]),
    button[data-testid="stBaseButton-secondary"] {{
        background-color: var(--surface) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 7px !important;
        font-weight: 500 !important;
        font-size: 0.86rem !important;
        padding: 0.42rem 0.95rem !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03) !important;
        transition: all 0.15s ease !important;
    }}

    button[kind="secondary"] *,
    button[kind="secondary"] p,
    button[kind="secondary"] span,
    .stButton > button:not([kind="primary"]) *,
    .stButton > button:not([kind="primary"]) p,
    .stButton > button:not([kind="primary"]) span,
    button[data-testid="stBaseButton-secondary"] *,
    button[data-testid="stBaseButton-secondary"] p,
    button[data-testid="stBaseButton-secondary"] span {{
        color: var(--text-primary) !important;
    }}

    button[kind="secondary"]:hover,
    .stButton > button:not([kind="primary"]):hover,
    button[data-testid="stBaseButton-secondary"]:hover {{
        background-color: var(--surface-hover) !important;
        border-color: var(--border) !important;
        color: var(--text-primary) !important;
    }}

    /* Inputs, Selectboxes & Textareas */
    input[type="text"], input[type="password"], textarea, .stSelectbox div[data-baseweb="select"] > div {{
        background-color: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 7px !important;
        color: var(--text-primary) !important;
        font-size: 0.87rem !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02) !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    }}

    input[type="text"]:focus, input[type="password"]:focus, textarea:focus, .stSelectbox div[data-baseweb="select"]:focus-within > div {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
        outline: none !important;
    }}

    div[data-baseweb="popover"] div[role="listbox"] {{
        background-color: var(--surface) !important;
        border: 1px solid var(--border) !important;
    }}

    div[data-baseweb="popover"] li[role="option"] {{
        color: var(--text-primary) !important;
        background-color: var(--surface) !important;
    }}

    div[data-baseweb="popover"] li[role="option"]:hover {{
        background-color: var(--surface-hover) !important;
    }}

    /* Streamlit Metrics Clean Restyling */
    [data-testid="stMetric"] {{
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }}

    [data-testid="stMetricLabel"] {{
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }}

    [data-testid="stMetricValue"] {{
        font-size: 1.7rem !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.02em !important;
    }}

    /* Modern Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 1.5rem !important;
        border-bottom: 1px solid var(--border) !important;
        background-color: transparent !important;
        padding-bottom: 0.2rem !important;
    }}

    .stTabs [data-baseweb="tab"] {{
        background-color: transparent !important;
        border: none !important;
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
        padding: 0.5rem 0.2rem !important;
    }}

    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        color: var(--accent) !important;
        font-weight: 600 !important;
        border-bottom: 2px solid var(--accent) !important;
    }}

    /* Subtle Dividers */
    hr {{
        border: none !important;
        border-top: 1px solid var(--border) !important;
        margin: 1.5rem 0 !important;
    }}

    /* Linear/Vercel Content Surface Panels */
    .saas-panel, .saas-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.03);
    }}

    /* Micro Status Badges */
    .status-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.18rem 0.55rem;
        border-radius: 9999px;
        line-height: 1.2;
    }}
    .badge-success {{ background: var(--success-light); color: var(--badge-success-text); border: 1px solid var(--badge-success-border); }}
    .badge-warning {{ background: var(--warning-light); color: var(--badge-warning-text); border: 1px solid var(--badge-warning-border); }}
    .badge-danger  {{ background: var(--danger-light);  color: var(--badge-danger-text);  border: 1px solid var(--badge-danger-border); }}
    .badge-info    {{ background: var(--accent-light);  color: var(--badge-info-text);    border: 1px solid var(--badge-info-border); }}
    .badge-neutral {{ background: var(--badge-neutral-bg); color: var(--badge-neutral-text); border: 1px solid var(--border); }}

    /* Clean Progress Bar */
    .saas-bar-track {{
        background-color: var(--border);
        border-radius: 9999px;
        height: 6px;
        width: 100%;
        overflow: hidden;
        margin-top: 0.3rem;
    }}
    .saas-bar-fill {{
        height: 100%;
        border-radius: 9999px;
        transition: width 0.3s ease;
    }}

    /* Modern Table (Zero Iframe, Pure Clean CSS) */
    .saas-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.86rem;
        margin: 0.5rem 0 1rem 0;
    }}
    .saas-table th {{
        text-align: left;
        padding: 0.65rem 0.85rem;
        font-size: 0.74rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-secondary);
        border-bottom: 1px solid var(--border);
        background: var(--surface-hover);
    }}
    .saas-table td {{
        padding: 0.75rem 0.85rem;
        border-bottom: 1px solid var(--border);
        color: var(--text-primary);
        vertical-align: middle;
    }}
    .saas-table tr:hover td {{
        background-color: var(--surface-hover);
    }}

    /* Clean Chat Interface */
    .chat-bubble-user {{
        background: {chat_user_bg};
        color: {chat_user_text};
        border-radius: 12px 12px 2px 12px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0 0.5rem auto;
        max-width: 80%;
        font-size: 0.88rem;
        line-height: 1.5;
    }}
    .chat-bubble-ai {{
        background: var(--surface);
        border: 1px solid var(--border);
        color: var(--text-primary);
        border-radius: 12px 12px 12px 2px;
        padding: 0.85rem 1.15rem;
        margin: 0.5rem auto 0.5rem 0;
        max-width: 90%;
        font-size: 0.88rem;
        line-height: 1.55;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
    }}

    /* Citation Box */
    .citation-box {{
        background-color: var(--surface-hover);
        border-left: 3px solid var(--accent);
        padding: 0.6rem 0.85rem;
        margin-top: 0.5rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.82rem;
        color: var(--text-secondary);
    }}

    /* Modern SaaS Chat Input Container (Zero Dark Bar Artifacts) */
    [data-testid="stChatInput"] {{
        background-color: transparent !important;
    }}

    [data-testid="stChatInput"] > div {{
        background-color: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.05) !important;
        transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
    }}

    [data-testid="stChatInput"] > div:focus-within {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
    }}

    [data-testid="stChatInputTextArea"],
    [data-testid="stChatInput"] textarea {{
        background-color: transparent !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-size: 0.88rem !important;
    }}

    [data-testid="stChatInputTextArea"]::placeholder,
    [data-testid="stChatInput"] textarea::placeholder {{
        color: var(--text-muted) !important;
    }}

    [data-testid="stChatInputSubmitButton"] {{
        background-color: var(--accent) !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: none !important;
        transition: background-color 0.15s ease !important;
    }}

    [data-testid="stChatInputSubmitButton"]:hover {{
        background-color: var(--accent-hover) !important;
    }}

    [data-testid="stChatInputSubmitButton"] [data-testid="stIconMaterial"],
    [data-testid="stChatInputSubmitButton"] svg {{
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }}

    /* Popover Trigger Buttons & Layout */
    [data-testid="stPopover"] {{
        display: inline-block;
        width: 100%;
    }}

    [data-testid="stPopover"] > div > button,
    [data-testid="stPopover"] button,
    button[data-testid="stPopoverButton"] {{
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.45rem !important;
        width: 100% !important;
    }}

    /* Prevent popover icon container from pulling backwards into label text */
    [data-testid="stPopover"] div[class*="StyledPopoverLabelContainer"] {{
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.45rem !important;
        margin-right: 0 !important;
    }}

    /* -------------------------------------------------------------
       POPOVER BODY & DROPDOWN CONTAINERS (THEME-AWARE POPUP)
       Guarantees White Screen uses pure white surface background and
       crisp dark text, while Black Screen uses dark surface background.
       ------------------------------------------------------------- */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    [data-testid="stPopoverBody"],
    div[data-testid="stPopoverBody"] {{
        background-color: var(--surface) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.08) !important;
    }}

    [data-testid="stPopoverBody"] p,
    [data-testid="stPopoverBody"] span,
    [data-testid="stPopoverBody"] label,
    [data-testid="stPopoverBody"] div,
    [data-testid="stPopoverBody"] [data-testid="stWidgetLabel"] {{
        color: var(--text-primary);
    }}

    [data-testid="stPopoverBody"] button[kind="primary"] *,
    [data-testid="stPopoverBody"] button[kind="primary"] p,
    [data-testid="stPopoverBody"] button[kind="primary"] span {{
        color: #FFFFFF !important;
    }}

    /* Checkboxes & Radios */
    [data-testid="stCheckbox"],
    [data-testid="stCheckbox"] label,
    [data-testid="stCheckbox"] label p,
    [data-testid="stCheckbox"] label span,
    [data-testid="stRadio"],
    [data-testid="stRadio"] label,
    [data-testid="stRadio"] label p,
    [data-testid="stRadio"] label span {{
        color: var(--text-primary) !important;
    }}

    [data-testid="stCheckbox"] [data-baseweb="checkbox"] > div:first-child {{
        border-color: var(--border) !important;
        background-color: var(--surface) !important;
    }}

    [data-testid="stCheckbox"] [data-baseweb="checkbox"][aria-checked="true"] > div:first-child,
    [data-testid="stCheckbox"] input:checked + div {{
        background-color: var(--accent) !important;
        border-color: var(--accent) !important;
    }}

    /* File Uploader */
    [data-testid="stFileUploader"] section {{
        background-color: var(--surface) !important;
        border: 1px dashed var(--border) !important;
        border-radius: 8px !important;
    }}
    [data-testid="stFileUploader"] section * {{
        color: var(--text-primary) !important;
    }}

    /* Modals & Dialogs */
    div[data-baseweb="modal"] > div,
    [data-testid="stModal"],
    [data-testid="stDialog"] {{
        background-color: var(--surface) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
    }}

    /* Expanders */
    [data-testid="stExpander"] {{
        background-color: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
    }}
    [data-testid="stExpander"] summary {{
        color: var(--text-primary) !important;
        font-weight: 500 !important;
        display: flex !important;
        align-items: center !important;
        gap: 0.5rem !important;
    }}
    [data-testid="stExpander"] summary [data-testid="stIconMaterial"] {{
        min-width: 1.15rem !important;
        max-width: 1.25rem !important;
        overflow: hidden !important;
        flex-shrink: 0 !important;
    }}
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
