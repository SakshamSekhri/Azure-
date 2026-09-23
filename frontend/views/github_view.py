import streamlit as st
from frontend.components.api_client import api


from frontend.components.ui import render_html


def render_github_view():
    st.markdown("### 🐙 Public GitHub Evidence Collection")
    st.markdown("Connect your public GitHub username to extract supporting code evidence from your repositories.")
    render_html("<span class='credit-pill'>🔒 Supporting Evidence Only — Explicitly Not Proof of Mastery</span>")

    try:
        profile = api.get_profile()
        current_username = profile.get("github_username", "") or ""
    except Exception:
        current_username = ""

    col1, col2 = st.columns([2, 1])
    with col1:
        username_input = st.text_input("GitHub Public Username", value=current_username, placeholder="e.g. torvalds / octocat")
    with col2:
        st.write("")
        st.write("")
        connect_btn = st.button("Fetch & Analyze Public Repos", type="primary", use_container_width=True)

    if connect_btn:
        if not username_input.strip():
            st.error("Please provide a valid GitHub username.")
        else:
            with st.spinner(f"Fetching bounded public repositories for @{username_input}..."):
                try:
                    result = api.connect_github(username_input.strip())
                    st.success(result.get("summary", "GitHub analysis complete!"))
                    st.session_state["last_github_result"] = result
                except Exception as e:
                    st.error(f"GitHub connection failed: {str(e)}")

    # Display results if available in session or fetch evidences
    res = st.session_state.get("last_github_result")
    if res:
        st.markdown("---")
        st.markdown(f"#### Analysis for `@{res.get('username')}`")

        c1, c2, c3 = st.columns(3)
        c1.metric("Repos Inspected", res.get("total_repos_inspected", 0))
        c2.metric("Languages Detected", len(res.get("primary_languages", [])))
        c3.metric("Frameworks Identified", len(res.get("detected_frameworks", [])))

        st.markdown("##### Detected Languages & Technologies")
        badges_html = " ".join([f"<span class='saas-badge saas-badge-info'>{lang}</span>" for lang in res.get("primary_languages", [])])
        badges_html += " " + " ".join([f"<span class='saas-badge saas-badge-success'>{fw}</span>" for fw in res.get("detected_frameworks", [])])
        render_html(f"<div>{badges_html}</div>")

        st.markdown("##### 📁 Inspected Repositories")
        for r in res.get("repos", []):
            with st.expander(f"📦 {r.get('name')} ({r.get('language') or 'N/A'})"):
                st.write(r.get("description") or "No description provided.")
                st.caption(f"⭐ Stars: {r.get('stargazers_count')} | Forks: {r.get('forks_count')} | [Open Repository]({r.get('html_url')})")
                if r.get("has_readme"):
                    st.markdown("**README Preview:**")
                    st.code(r.get("readme_snippet", "")[:400] + "...", language="markdown")
