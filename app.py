"""
AI Maturity Assessment Tool - Website Analysis
VERSION 4: Two-phase analysis with score-based opportunities
- Phase 1: Identify gaps, generate MCQs
- Phase 2: Calculate score (35% web + 65% MCQ), generate final content
- Opportunities: 1 if >90, 2 if 75-90, 3 if <75
- MCQs stored in Google Sheets (Q1-Q5 columns)
"""
import streamlit as st
from scraper import scrape_company_website
from analyzer_v4 import analyze_company_phase1, analyze_company_phase2
from utils_v4 import (
    load_config, validate_config, save_to_google_sheets,
    get_maturity_badge, get_tag_color, format_score_display,
    validate_url, validate_email, truncate_text, prepare_mcq_data_for_sheets
)
from pdf_generator import generate_assessment_pdf
import time
import plotly.graph_objects as go


# Page configuration
st.set_page_config(
    page_title="AI Maturity Assessment - DataBeat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Navy Blue Theme CSS + Logo
st.markdown("""
<style>
    /* Navy Blue Theme - RGB(32,42,68) */
    :root {
        --navy-blue: rgb(32, 42, 68);
        --navy-blue-light: rgb(52, 62, 88);
        --navy-blue-dark: rgb(22, 32, 58);
    }

    /* Logo Section */
    .logo-container {
        position: relative;
        background: white;
        padding: 10px 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
        margin: 0 0 0.5rem 0;
    }

    .logo-img {
        height: 35px;
        width: auto;
        display: block;
    }

    /* Main content spacing */
    .main .block-container {
        padding-top: 1rem !important;
    }

    /* Typography */
    h1 {
        font-size: 1.8rem !important;
        color: var(--navy-blue);
    }

    h2, h3 {
        color: var(--navy-blue);
    }

    /* Buttons - Navy Blue */
    .stButton > button {
        background-color: var(--navy-blue) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 500 !important;
    }

    .stButton > button:hover {
        background-color: var(--navy-blue-light) !important;
        box-shadow: 0 4px 8px rgba(32, 42, 68, 0.3) !important;
    }

    /* Primary button */
    button[kind="primary"] {
        background-color: var(--navy-blue) !important;
    }

    /* Radio buttons - Simple format without background */
    .stRadio > div {
        gap: 0.2rem !important;
    }

    .stRadio > div > label {
        background-color: transparent !important;
        padding: 0.3rem 0.5rem !important;
        border-radius: 0px;
        border: none !important;
        margin-bottom: 0.2rem !important;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 0.9rem !important;
    }

    /* Reduce spacing between questions */
    .element-container:has(.stRadio) {
        margin-bottom: 0.2rem !important;
    }

    h3 {
        margin-top: 0.3rem !important;
        margin-bottom: 0.2rem !important;
        font-size: 1rem !important;
    }

    .stRadio > div > label:hover {
        color: var(--navy-blue);
    }

    .stRadio > div > label[data-checked="true"] {
        color: var(--navy-blue) !important;
        font-weight: bold !important;
    }

    /* Question text smaller */
    .stRadio > label {
        font-size: 0.95rem !important;
        font-weight: 500 !important;
    }

    /* Score badge */
    .score-badge {
        font-size: 1.5rem;
        font-weight: bold;
        text-align: center;
        padding: 0.75rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        background: linear-gradient(135deg, var(--navy-blue) 0%, var(--navy-blue-light) 100%) !important;
    }

    /* Finding items */
    .finding-item {
        padding: 0.5rem;
        margin: 0.3rem 0;
        background-color: #f8f9fa;
        border-left: 3px solid var(--navy-blue);
        border-radius: 3px;
    }

    /* Metric cards - Much Smaller */
    .metric-card {
        background: linear-gradient(135deg, var(--navy-blue) 0%, var(--navy-blue-light) 100%);
        color: white;
        padding: 0.6rem;
        border-radius: 6px;
    }

    .metric-card h1 {
        font-size: 1.6rem !important;
        margin: 0.2rem 0 !important;
    }

    .metric-card p {
        font-size: 0.75rem !important;
        margin: 0 !important;
    }

    /* Reduce section spacing - more compact */
    .element-container {
        margin-bottom: 0.2rem !important;
    }

    div[data-testid="stVerticalBlock"] > div {
        gap: 0.2rem !important;
    }

    /* Reduce heading spacing - more compact */
    h2, h3, h4 {
        margin-top: 0.4rem !important;
        margin-bottom: 0.2rem !important;
    }

    /* Reduce text box sizes */
    .stMarkdown {
        font-size: 0.9rem !important;
        line-height: 1.4 !important;
    }

    /* Compact paragraphs */
    p {
        margin-bottom: 0.3rem !important;
    }

    /* Progress bar */
    .stProgress > div > div {
        background-color: var(--navy-blue) !important;
    }

    /* Info boxes */
    .stInfo {
        background-color: #f0f4ff;
        border-left-color: var(--navy-blue) !important;
    }
</style>

<!-- Logo Header -->
<div class="logo-container">
    <img src="https://databeat.io/wp-content/uploads/2025/05/DataBeat-Mediamint-Logo-1-1.png" class="logo-img" alt="DataBeat Logo">
</div>
""", unsafe_allow_html=True)


# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 'input'
if 'scraping_results' not in st.session_state:
    st.session_state.scraping_results = None
if 'phase1_results' not in st.session_state:
    st.session_state.phase1_results = None
if 'final_results' not in st.session_state:
    st.session_state.final_results = None


def reset_app():
    """Reset application state"""
    st.session_state.step = 'input'
    st.session_state.scraping_results = None
    st.session_state.phase1_results = None
    st.session_state.final_results = None


def display_landing_page():
    """Display landing page with URL, Name, and Email input"""
    st.title("AI Maturity Assessment")
    st.markdown("Assess your organization's AI readiness and maturity")

    st.markdown("""
    **How it works:**
    1. Enter your details and company website URL
    2. AI analyzes your digital presence and external sources
    3. Answer 5 questions about your organization
    4. Get comprehensive AI maturity report
    """)

    st.markdown("---")

    # Input form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        url = st.text_input(
            "Company Website URL",
            placeholder="example.com",
            help="Enter your company's website URL"
        )

        name = st.text_input(
            "Your Name",
            placeholder="John Doe"
        )

        email = st.text_input(
            "Your Email",
            placeholder="john@company.com"
        )

        if st.button("Start Assessment", type="primary", use_container_width=True):
            if not url:
                st.error("Please enter a website URL")
                return
            if not name:
                st.error("Please enter your name")
                return
            if not email:
                st.error("Please enter your email")
                return

            # Validate URL and email
            is_valid, result = validate_url(url)
            if not is_valid:
                st.error(result)
                return

            if not validate_email(email):
                st.error("Please enter a valid email address")
                return

            # Start analysis
            st.session_state.website_url = result
            st.session_state.user_name = name
            st.session_state.user_email = email
            st.session_state.step = 'analyzing'
            st.rerun()


def display_analysis_progress():
    """Display Phase 1 analysis in progress"""

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.title("Analyzing Company...")

    # Load config
    config = load_config()
    is_valid, error_msg = validate_config(config)

    if not is_valid:
        st.error(f"Configuration error: {error_msg}")
        st.info("Please check your .env file or Streamlit secrets configuration.")
        if st.button("Back"):
            reset_app()
            st.rerun()
        return

    # Progress tracking
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        progress_bar = st.progress(0)
        status_text = st.empty()

    try:
        # Step 1: Scraping
        status_text.info("🌐 Extracting content from your website...")
        progress_bar.progress(0.1)

        scraping_results = scrape_company_website(
            st.session_state.website_url,
            max_pages=10
        )

        if 'error' in scraping_results:
            st.error(f"Failed to scrape website: {scraping_results['error']}")
            if st.button("Try Again"):
                st.session_state.step = 'input'
                st.rerun()
            return

        st.session_state.scraping_results = scraping_results
        progress_bar.progress(0.3)

        # Step 2: Show crawling results
        status_text.info(f"✓ Found {scraping_results['page_count']} pages")
        time.sleep(0.2)
        progress_bar.progress(0.4)

        # Step 3: Phase 1 Analysis (Gaps + MCQs)
        status_text.info("🔎 Generating questions...")
        progress_bar.progress(0.5)

        phase1_results = analyze_company_phase1(
            company_name=scraping_results['company_name'],
            website_content=scraping_results['total_text'],
            gemini_api_key=config['gemini_api_key'],
            tavily_api_key=config['tavily_api_key'],
            scraped_pages=scraping_results.get('pages_scraped', [])
        )

        st.session_state.phase1_results = phase1_results
        progress_bar.progress(0.9)

        # Step 4: Complete
        status_text.success("✓ Analysis complete!")
        progress_bar.progress(1.0)

        time.sleep(0.3)

        # Move to MCQ questions
        st.session_state.step = 'mcq_questions'
        st.rerun()

    except Exception as e:
        import traceback
        st.error(f"An error occurred during analysis:")
        st.error(f"**Error:** {str(e)}")
        with st.expander("View detailed error"):
            st.code(traceback.format_exc())
        st.info("Please try again or contact support if the issue persists.")
        if st.button("Back"):
            reset_app()
            st.rerun()


def display_mcq_questions():
    """Display MCQ questions from Phase 1"""
    results = st.session_state.phase1_results
    scraping = st.session_state.scraping_results

    if not results or not scraping:
        st.error("No results available")
        reset_app()
        st.rerun()
        return

    st.title(f"Assessment: {scraping['company_name']}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("📋 Answer these 5 questions to help us assess your AI maturity accurately.")

    questions = results.get('questions', [])

    if not questions or len(questions) == 0:
        st.error("No questions available. Please try again.")
        if st.button("Restart"):
            reset_app()
            st.rerun()
        return

    # Display questions and collect answers
    answers = {}

    for idx, q in enumerate(questions, 1):
        st.markdown(f"**Q{idx}. {q['question']}**")

        options = q.get('options', [])
        option_labels = [f"{opt['label']}. {opt['text']}" for opt in options]

        selected = st.radio(
            f"Select your answer for Q{idx}:",
            options=option_labels,
            key=f"q{idx}",
            label_visibility="collapsed",
            index=None  # No preselected option
        )

        # Store answer
        if selected:
            selected_label = selected.split('.')[0]
            selected_option = next((opt for opt in options if opt['label'] == selected_label), None)
            if selected_option:
                answers[f"q{idx}"] = selected_option

        # Minimal spacing between questions
        if idx < len(questions):
            st.markdown("<div style='margin: 0.4rem 0;'></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Submit button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🎯 Calculate My Score", type="primary", use_container_width=True):
            if len(answers) < len(questions):
                st.error("Please answer all questions before proceeding")
            else:
                # Store MCQ answers and move to Phase 2
                st.session_state.mcq_answers = answers
                st.session_state.step = 'calculating_final'
                st.rerun()


def display_final_calculation():
    """Calculate final score and generate final content (Phase 2)"""

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.title("Calculating Your Final Score...")

    # Centered progress elements
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        progress_bar = st.progress(0.5)
        status_text = st.info("Generating your personalized report...")

    try:
        phase1_results = st.session_state.phase1_results
        mcq_answers = st.session_state.mcq_answers

        # Phase 2: Calculate score and generate final content
        final_results = analyze_company_phase2(phase1_results, mcq_answers)

        st.session_state.final_results = final_results
        progress_bar.progress(1.0)
        status_text.success("✓ Report ready!")

        time.sleep(0.5)
        st.session_state.step = 'full_results'
        st.rerun()

    except Exception as e:
        st.error(f"Error during calculation: {str(e)}")
        if st.button("Try Again"):
            st.session_state.step = 'mcq_questions'
            st.rerun()


def display_full_results():
    """Display full analysis results"""
    results = st.session_state.final_results
    scraping = st.session_state.scraping_results
    phase1 = st.session_state.phase1_results
    config = load_config()

    if not results or not scraping:
        st.error("No results available")
        reset_app()
        st.rerun()
        return

    # Header
    st.markdown(
    f"""
    <h2 style='font-size:32px; font-weight:700; color:#1E1E1E;'>
        AI Maturity Report: {scraping['company_name']}
    </h2>
    """,
    unsafe_allow_html=True
)
    st.caption(f"Generated on: {__import__('datetime').datetime.now().strftime('%B %d, %Y')}")

    # Main score display
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class='metric-card' style='text-align: center;'>
            <p style='margin: 0 0 0.3rem 0; font-size: 0.85rem; opacity: 0.9;'>Overall Score</p>
            <h1 style='color: #667eea; margin: 0;'>{results['overall_score']}</h1>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='metric-card' style='text-align: center;'>
            <p style='margin: 0 0 0.3rem 0; font-size: 0.85rem; opacity: 0.9;'>AI Maturity</p>
            <h1 style='margin: 0; font-size: 1.4rem;'>{results['maturity_tag']}</h1>
        </div>
        """, unsafe_allow_html=True)

    # Highlighted CTA
    st.markdown("""
    <div style='text-align: center; padding: 1rem; background: linear-gradient(135deg, rgb(32, 42, 68) 0%, rgb(52, 62, 88) 100%); border-radius: 8px; margin: 1rem 0;'>
        <p style='font-size: 1.1rem; margin: 0; color: white; font-weight: 600;'>
            🎯 Want a more comprehensive score? Complete our full questionnaire:
        </p>
        <a href='https://ai-maturity.streamlit.app/' target='_blank' style='color: #FFD700; font-weight: bold; font-size: 1.05rem; text-decoration: underline;'>
            https://ai-maturity.streamlit.app/
        </a>
    </div>
    """, unsafe_allow_html=True)

    # Summary
    st.markdown("#### Executive Summary")
    st.write(results.get('summary', 'No summary available'))

    # Key findings
    st.markdown("#### Key Findings")

    evidence = results.get('evidence', {})
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**💪 Strengths**")
        for strength in evidence.get('strengths', []):
            st.markdown(f"""<div class='finding-item'>{strength}</div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("**🎯 Opportunities**")
        for opp in evidence.get('opportunities', []):
            st.markdown(f"""<div class='finding-item'>{opp}</div>""", unsafe_allow_html=True)

    # Links Analyzed
    st.markdown("#### Sources Analyzed")

    sources = results.get('sources', {})
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Website Pages**")
        scraped_pages = sources.get('scraped_pages', [])
        if scraped_pages:
            for page in scraped_pages[:8]:
                st.markdown(f"• [{page.get('title', 'Page')}]({page.get('url', '#')})")
        else:
            st.markdown("*No pages recorded*")

    with col2:
        st.markdown("**External Research**")
        external_sources = sources.get('external_sources', [])
        if external_sources:
            for source in external_sources[:6]:
                st.markdown(f"• [{source.get('title', 'Source')}]({source.get('url', '#')})")
        else:
            st.markdown("*No external sources*")

    # Save to Google Sheets
    metadata = results.get('search_metadata', {})

    # Extract links
    tavily_links = ', '.join([s.get('url', '') for s in sources.get('external_sources', [])])
    scraped_links = ', '.join([p.get('url', '') for p in sources.get('scraped_pages', [])])

    # Prepare MCQ data for sheets
    questions = phase1.get('questions', [])
    mcq_answers = st.session_state.get('mcq_answers', {})
    mcq_sheet_data = prepare_mcq_data_for_sheets(questions, mcq_answers)

    save_data = {
        'name': st.session_state.get('user_name', ''),
        'email': st.session_state.get('user_email', ''),
        'company_name': scraping['company_name'],
        'website_url': st.session_state.website_url,
        'initial_score': results.get('web_score', 0),
        'mcq_score': results.get('mcq_score', 0),
        'final_score': results['overall_score'],
        'maturity_tag': results['maturity_tag'],
        'gaps_identified': '; '.join(metadata.get('gaps_identified', [])),
        'queries_generated': '; '.join(metadata.get('queries_generated', [])),
        'tavily_links': tavily_links,
        'scraped_links': scraped_links,
        'pages_crawled': scraping['page_count'],
        'summary': results.get('summary', '')[:500]
    }

    success, message = save_to_google_sheets(save_data, config, mcq_sheet_data)
    if not success and 'not configured' not in message:
        st.warning(f"⚠️ {message}")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # PDF Download at bottom
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Generate PDF
        pdf_buffer = generate_assessment_pdf(results, scraping, mcq_answers)

        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_buffer,
            file_name=f"{scraping['company_name']}_AI_Maturity_Report.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )


# Main app logic
def main():
    """Main application flow"""
    step = st.session_state.step

    if step == 'input':
        display_landing_page()
    elif step == 'analyzing':
        display_analysis_progress()
    elif step == 'mcq_questions':
        display_mcq_questions()
    elif step == 'calculating_final':
        display_final_calculation()
    elif step == 'full_results':
        display_full_results()
    else:
        # Fallback
        reset_app()
        st.rerun()


if __name__ == "__main__":
    main()
