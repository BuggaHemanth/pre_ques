"""
AI-powered analysis module with TWO-PHASE approach
VERSION 4: Phase 1 = Gaps only, Phase 2 = Final content with score-based opportunities
Scoring: 35% website + 65% MCQ
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from tavily import TavilyClient
from typing import Dict, List
import json
import os


class AIMaturityAnalyzer:
    """Two-phase analyzer: Gaps first, then final content after MCQs"""

    def __init__(self, gemini_api_key: str, tavily_api_key: str):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=gemini_api_key,
            temperature=0.0
        )
        self.tavily = TavilyClient(api_key=tavily_api_key)

        self.dimensions = [
            "AI Technology Adoption",
            "LLM & AI Agents Implementation",
            "Digital Infrastructure",
            "Data Capabilities",
            "Innovation & R&D"
        ]

    def generate_search_queries(self, company_name: str, website_content: str) -> Dict:
        """Generate targeted search queries based on gaps"""

        query_prompt = f"""Analyze this company's website content and identify what information is MISSING for assessing their AI readiness and maturity.

Company: {company_name}

Website Content (first 8000 chars):
{website_content[:8000]}

Your task:
1. Identify 3 key information gaps that would help assess AI readiness and maturity
2. Generate 3 specific, targeted search queries to fill those gaps

CRITICAL QUERY RULES:
1. Keep queries SIMPLE and CLEAN - just company name + 2-4 keywords maximum
2. DO NOT use quotation marks, parentheses, or special operators
3. DO NOT chain multiple concepts with "and" or commas
4. Focus on finding EVIDENCE of actual implementation (case studies, reviews, implementations)
5. AVOID searches that return individual employee profiles or company blog posts

Return ONLY valid JSON:
{{
    "gaps_identified": [
        "gap 1 description",
        "gap 2 description",
        "gap 3 description"
    ],
    "search_queries": [
        "query 1",
        "query 2",
        "query 3"
    ]
}}

Examples of GOOD queries (simple, clean, effective):
- "{company_name} AI case studies"
- "{company_name} machine learning projects"
- "{company_name} AI implementation review"
- "{company_name} technology stack"

Examples of BAD queries (too complex, will fail):
- "{company_name} company "AI-powered" case study results"
- "{company_name} "machine learning" client testimonials "results""
- "{company_name} AI solutions AdTech implementation reviews"
"""

        print("\n" + "="*80)
        print("🧠 PHASE 1: ANALYZING GAPS")
        print("="*80)

        try:
            response = self.llm.invoke(query_prompt)
            response_text = response.content

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            query_data = json.loads(response_text)

            gaps = query_data.get('gaps_identified', [])
            queries = query_data.get('search_queries', [])

            print(f"\n✅ Identified {len(gaps)} gaps")
            print("\nGaps:")
            for i, gap in enumerate(gaps, 1):
                print(f"  {i}. {gap}")
            print("\nSearch Queries:")
            for i, query in enumerate(queries, 1):
                print(f"  {i}. {query}")
            print("="*80 + "\n")

            return {
                'gaps_identified': gaps,
                'search_queries': queries
            }

        except Exception as e:
            print(f"❌ Error: {e}")
            # Fallback
            return {
                'gaps_identified': [
                    "Limited information about specific AI projects",
                    "Unclear technical capabilities",
                    "Missing details on AI implementation"
                ],
                'search_queries': [
                    f'{company_name} AI projects case studies',
                    f'{company_name} technology stack',
                    f'{company_name} AI solutions'
                ]
            }

    def is_valid_source(self, url: str) -> bool:
        """Filter out invalid sources"""
        url_lower = url.lower()

        # Block file downloads
        file_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.ashx', '.aspx', '.zip', '.rar', '.tar', '.gz'
        ]
        for ext in file_extensions:
            if url_lower.endswith(ext) or ext + '?' in url_lower:
                return False

        # Block individual LinkedIn profiles
        if 'linkedin.com/in/' in url_lower:
            return False

        # Allow LinkedIn company pages
        if 'linkedin.com/company/' in url_lower:
            return True

        # Block other social media profiles
        invalid_patterns = [
            '/profile/', '/user/', '/u/',
            'twitter.com/', 'facebook.com/', 'instagram.com/',
        ]

        for pattern in invalid_patterns:
            if pattern in url_lower:
                return False

        return True

    def is_company_mentioned(self, content: str, company_name: str) -> bool:
        """
        Check if company name is mentioned in the content

        Args:
            content: Text content to search
            company_name: Company name to look for

        Returns:
            True if company name appears at least once
        """
        if not content or not company_name:
            return False

        # Normalize for case-insensitive search
        content_lower = content.lower()
        company_lower = company_name.lower()

        return company_lower in content_lower

    def execute_searches(self, queries: List[str], company_name: str) -> tuple[str, List[Dict]]:
        """Execute Tavily searches with company name filtering and duplicate removal"""

        print("\n" + "="*80)
        print("🔍 EXECUTING TAVILY SEARCHES")
        print("="*80)

        all_results = []
        all_sources = []
        seen_urls = set()  # Track URLs to prevent duplicates

        for idx, query in enumerate(queries, 1):
            print(f"\nQuery {idx}: {query}")

            try:
                search_results = self.tavily.search(
                    query=query,
                    max_results=3,
                    include_answer=True,
                    search_depth="advanced",
                    exclude_domains=[
                        "facebook.com", "m.facebook.com", "twitter.com", "x.com",
                        "instagram.com", "linkedin.com", "youtube.com", "reddit.com",
                        "medium.com", "stackoverflow.com",'sciencedirect.com'
                    ],
                    days=365
                )

                total_returned = len(search_results.get('results', []))
                print(f"  Tavily returned: {total_returned} links")

                # Get AI answer
                if 'answer' in search_results and search_results['answer']:
                    all_results.append(f"Query: {query}\nAnswer: {search_results['answer']}")
                    print(f"  + AI answer extracted")

                # Get individual results
                valid_count = 0
                filtered_url_count = 0
                filtered_content_count = 0
                filtered_duplicate_count = 0

                for result in search_results.get('results', []):
                    if valid_count >= 2:
                        break

                    url = result.get('url', 'N/A')

                    # First filter: URL validation
                    if not self.is_valid_source(url):
                        filtered_url_count += 1
                        print(f"  X Filtered (invalid URL): {url[:70]}")
                        continue

                    # Second filter: Check for duplicate URL
                    if url in seen_urls:
                        filtered_duplicate_count += 1
                        print(f"  X Filtered (duplicate URL): {url[:70]}")
                        continue

                    title = result.get('title', 'Source')
                    content = result.get('content', '')

                    # Third filter: Company name must be mentioned in content
                    if not self.is_company_mentioned(content, company_name):
                        filtered_content_count += 1
                        print(f"  X Filtered (no company mention): {title[:60]}")
                        continue

                    # Add to seen_urls set
                    seen_urls.add(url)

                    all_results.append(f"Source: {title}\nURL: {url}\n{content}")
                    all_sources.append({
                        'url': url,
                        'title': title,
                        'query': query
                    })
                    print(f"  + [{valid_count + 1}] {title[:65]}")
                    valid_count += 1

                total_filtered = filtered_url_count + filtered_content_count + filtered_duplicate_count
                print(f"  Summary: {valid_count} valid, {total_filtered} filtered ({filtered_url_count} URL, {filtered_duplicate_count} duplicate, {filtered_content_count} content)")

            except Exception as e:
                print(f"  X Error: {e}")
                continue

        combined_text = "\n\n---\n\n".join(all_results) if all_results else "No external information found."

        print(f"\n✅ TOTAL SOURCES: {len(all_sources)} unique")
        print("="*80 + "\n")

        return combined_text, all_sources

    def analyze_and_score_initial(self, website_content: str, external_info: str, company_name: str) -> Dict:
        """
        Analyze website + Tavily data to generate initial score and identify gaps
        Similar to analyzer_v2 approach - holistic analysis in one call

        Returns:
            Dict with initial_score and gaps
        """

        analysis_prompt = f"""You are an AI maturity assessment expert. Analyze the company {company_name} and provide an initial assessment.

WEBSITE CONTENT:
{website_content[:12000]}

EXTERNAL RESEARCH:
{external_info[:4000]}

TASK:
1. Assess their AI maturity and assign an initial score (0-100)
2. Identify gaps in information (what's missing that would help assess AI readiness)

SCORING GUIDANCE:
- Consider the company's known position in the industry
- Base assessment on concrete evidence from website and external sources
- Be objective and evidence-based
- If this is a well-known tech/AI company, factor in their industry reputation

Score ranges:
- 0-25 : No AI adoption, traditional processes
- 26-50 : Experimenting with AI, pilot projects
- 51-75 : Active AI integration, proven use cases
- 76-100 : AI-native operations, industry leadership

Return ONLY valid JSON:
{{
    "initial_score": <0-100>,
    "gaps": ["<information gap 1>", "<information gap 2>", "<information gap 3>"]
}}
"""

        print("\n" + "="*80)
        print("📊 ANALYZING & SCORING (PHASE 1)")
        print("="*80)

        try:
            response = self.llm.invoke(analysis_prompt)
            response_text = response.content

            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result = json.loads(response_text)
            initial_score = result.get('initial_score', 50)
            gaps = result.get('gaps', [])

            print(f"✅ Initial Score: {initial_score}/100")
            print(f"✅ Gaps Identified: {len(gaps)}")
            for i, gap in enumerate(gaps, 1):
                print(f"   {i}. {gap}")
            print("="*80 + "\n")

            return {
                'initial_score': initial_score,
                'gaps': gaps
            }

        except Exception as e:
            print(f"❌ Error during analysis: {e}")
            print("   Using fallback values")
            print("="*80 + "\n")
            return {
                'initial_score': 50,
                'gaps': [
                    "Limited information about AI implementation",
                    "Unclear technical infrastructure details",
                    "Missing details on team expertise"
                ]
            }

    def generate_mcqs(self, company_name: str, gaps: List[str]) -> List[Dict]:
        """Generate 5 MCQs based on identified gaps"""

        question_prompt = f"""Based on gaps in information about the company {company_name}, generate 5 multiple-choice questions.

Gaps identified:
{chr(10).join(f'{i+1}. {gap}' for i, gap in enumerate(gaps))}

Generate 5 questions with 5 options each (A-E), progressing from low to high maturity.

CRITICAL REQUIREMENTS:
- Focus on AI strategy, data infrastructure, technology and innovation
- DO NOT ask about employee count or team size or company culture
- Keep options CRISP (max 6-8 words each)
- Use simple, direct language
- Avoid lengthy descriptions

Example of GOOD options:
- "No AI usage"
- "Exploring AI tools"
- "Pilot AI projects"
- "Production AI systems"
- "Advanced AI at scale"

Return ONLY valid JSON:
{{
    "questions": [
        {{
            "question": "Question text?",
            "options": [
                {{"label": "A", "text": "Short option", "score": 0}},
                {{"label": "B", "text": "Short option", "score": 25}},
                {{"label": "C", "text": "Short option", "score": 50}},
                {{"label": "D", "text": "Short option", "score": 75}},
                {{"label": "E", "text": "Short option", "score": 100}}
            ]
        }}
    ]
}}
"""

        print("\n" + "="*80)
        print("❓ GENERATING MCQs FROM GAPS")
        print("="*80)

        try:
            response = self.llm.invoke(question_prompt)
            response_text = response.content

            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            questions_data = json.loads(response_text)
            questions = questions_data.get('questions', [])

            print(f"✅ Generated {len(questions)} questions")
            print("="*80 + "\n")

            return questions

        except Exception as e:
            print(f"❌ Error: {e}")
            # Default 5 questions
            return [
                {
                    "question": "What is your data infrastructure maturity?",
                    "options": [
                        {"label": "A", "text": "Legacy systems, minimal digitization", "score": 0},
                        {"label": "B", "text": "Digital but siloed databases", "score": 25},
                        {"label": "C", "text": "Centralized with basic integration", "score": 50},
                        {"label": "D", "text": "Cloud-based with APIs", "score": 75},
                        {"label": "E", "text": "Real-time data lakes, AI-ready", "score": 100}
                    ]
                },
                {
                    "question": "What is your AI/LLM implementation status?",
                    "options": [
                        {"label": "A", "text": "No AI usage", "score": 0},
                        {"label": "B", "text": "Exploring LLMs (ChatGPT, etc.)", "score": 25},
                        {"label": "C", "text": "Pilot AI projects running", "score": 50},
                        {"label": "D", "text": "Production AI systems deployed", "score": 75},
                        {"label": "E", "text": "Custom LLMs, AI agents in use", "score": 100}
                    ]
                },
                {
                    "question": "What is your innovation approach?",
                    "options": [
                        {"label": "A", "text": "Traditional, no experimentation", "score": 0},
                        {"label": "B", "text": "Aware of AI, no active R&D", "score": 25},
                        {"label": "C", "text": "Testing AI tools occasionally", "score": 50},
                        {"label": "D", "text": "Dedicated AI experiments", "score": 75},
                        {"label": "E", "text": "Continuous AI R&D", "score": 100}
                    ]
                },
                {
                    "question": "What AI technologies are you using?",
                    "options": [
                        {"label": "A", "text": "None at all", "score": 0},
                        {"label": "B", "text": "Basic automation tools", "score": 25},
                        {"label": "C", "text": "Classical ML algorithms", "score": 50},
                        {"label": "D", "text": "Deep Learning/NLP/Computer Vision", "score": 75},
                        {"label": "E", "text": "Advanced AI agents and LLMs", "score": 100}
                    ]
                },
                {
                    "question": "How is AI integrated in workflows?",
                    "options": [
                        {"label": "A", "text": "Not integrated", "score": 0},
                        {"label": "B", "text": "Ad-hoc individual usage", "score": 25},
                        {"label": "C", "text": "Some team-level tools", "score": 50},
                        {"label": "D", "text": "Department-wide systems", "score": 75},
                        {"label": "E", "text": "Enterprise-wide AI platform", "score": 100}
                    ]
                }
            ]

    def generate_final_content(self, website_content: str, external_info: str,
                              company_name: str, final_score: int,
                              mcq_answers: Dict, gaps: List[str]) -> Dict:
        """
        PHASE 2: Generate summary, strengths, opportunities based on final score

        Args:
            final_score: Already calculated (35% web + 65% MCQ)
            mcq_answers: User responses to MCQs
            gaps: Gaps identified in Phase 1
        """

        # Determine number of opportunities based on score
        if final_score > 90:
            num_opportunities = 1
            opp_instruction = "Generate EXACTLY 1 cutting-edge strategic opportunity for an elite performer."
        elif 75 <= final_score <= 90:
            num_opportunities = 2
            opp_instruction = "Generate EXACTLY 2 targeted optimization opportunities for a strong performer."
        else:
            num_opportunities = 3
            opp_instruction = "Generate EXACTLY 3 concrete improvement opportunities for growth."

        # Format MCQ answers for context
        mcq_context = "\n".join([
            f"Q: {ans.get('question', 'N/A')}\nA: {ans.get('text', 'N/A')} (Score: {ans.get('score', 0)})"
            for ans in mcq_answers.values()
        ])

        final_prompt = f"""You are an AI maturity expert. Generate the final assessment for {company_name}.

FINAL SCORE (already calculated): {final_score}/100

GAPS IDENTIFIED (from website analysis):
{chr(10).join(f'- {gap}' for gap in gaps)}

WEBSITE CONTENT:
{website_content[:10000]}

EXTERNAL RESEARCH:
{external_info[:4000]}

USER'S MCQ RESPONSES:
{mcq_context}

YOUR TASK:
Using BOTH the website information AND the user's questionnaire responses, generate:

1. Executive Summary
   - Maximum 170 words total
   - Current state incorporating both website, Tavily results and MCQ insights
   - Key AI maturity indicators
   - Overall assessment reflecting the {final_score}/100 score

2. Strengths (EXACTLY 3)
   - ONE sentence each (no more than one sentence per strength)

3. Opportunities (EXACTLY {num_opportunities})
   - ONE sentence each (no more than one sentence per opportunity)
   - {opp_instruction}
   - Be actionable and specific such that it adresses the gaps identifed and solves the issues found from the questionnaire.

CRITICAL FORMATTING RULES:
- Summary: Under 170 words total
- Each strength: ONE sentence only
- Each opportunity: ONE sentence only

SCORING CONTEXT:
- Score {final_score}/100 = {"Trailblazer (76-100)" if final_score > 75 else "Pacesetter (51-75)" if final_score > 50 else "Explorer (26-50)" if final_score > 25 else "Novice (0-25)"}

Return ONLY valid JSON:
{{
    "summary": "<concise summary under 180 words>",
    "strengths": ["<one sentence>", "<one sentence>", "<one sentence>"],
    "opportunities": ["<one sentence>", "<one sentence>" (if needed), "<one sentence>" (if needed)]
}}

IMPORTANT:
- Generate EXACTLY {num_opportunities} opportunities, no more, no less
- Each strength and opportunity must be ONE sentence only
- Summary must not exceed 170 words

** Be clear in your language and dont need to repeat the company name multiple times**
** Be professional and dont mention employee count of company. **
"""

        print("\n" + "="*80)
        print(f"🤖 PHASE 2: GENERATING FINAL CONTENT (Score: {final_score})")
        print(f"   Opportunities to generate: {num_opportunities}")
        print("="*80)

        try:
            response = self.llm.invoke(final_prompt)
            response_text = response.content

            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            final_content = json.loads(response_text)

            print(f"✅ Generated summary, {len(final_content.get('strengths', []))} strengths, {len(final_content.get('opportunities', []))} opportunities")
            print("="*80 + "\n")

            return final_content

        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                "summary": f"Analysis completed for {company_name} with score {final_score}/100.",
                "strengths": ["Digital presence established", "Business operations functional", "Growth potential identified"],
                "opportunities": ["Develop AI strategy", "Build data infrastructure", "Invest in AI talent"][:num_opportunities]
            }


def analyze_company_phase1(company_name: str, website_content: str,
                           gemini_api_key: str, tavily_api_key: str,
                           scraped_pages: List[Dict] = None) -> Dict:
    """
    PHASE 1: Analyze website, identify gaps, generate MCQs

    Returns:
        Dict with initial_score, gaps, MCQ questions, and sources
    """
    analyzer = AIMaturityAnalyzer(gemini_api_key, tavily_api_key)

    # Step 1: Generate search queries based on initial gap analysis
    query_data = analyzer.generate_search_queries(company_name, website_content)
    queries = query_data['search_queries']

    # Step 2: Execute Tavily searches (with company name filtering)
    external_info, external_sources = analyzer.execute_searches(queries, company_name)

    # Step 3: Analyze website + Tavily data to get initial score and identify gaps
    analysis_result = analyzer.analyze_and_score_initial(website_content, external_info, company_name)
    initial_score = analysis_result['initial_score']
    gaps = analysis_result['gaps']

    # Step 4: Generate MCQs based on identified gaps
    questions = analyzer.generate_mcqs(company_name, gaps)

    # Step 5: Store preliminary data
    result = {
        'initial_score': initial_score,
        'gaps': gaps,
        'queries': queries,
        'questions': questions,
        'external_info': external_info,
        'sources': {
            'external_sources': external_sources,
            'scraped_pages': scraped_pages if scraped_pages else []
        },
        'website_content': website_content,  # Store for Phase 2
        'company_name': company_name
    }

    print(f"\n✅ PHASE 1 COMPLETE - Initial Score: {initial_score}/100, {len(questions)} MCQs generated\n")

    return result


def analyze_company_phase2(phase1_data: Dict, mcq_answers: Dict) -> Dict:
    """
    PHASE 2: Calculate final score, generate summary/strengths/opportunities

    Args:
        phase1_data: Results from Phase 1
        mcq_answers: User responses to MCQs (dict with keys q1, q2, etc.)

    Returns:
        Complete analysis with final score and content
    """

    # Calculate final score: 35% web + 65% MCQ

    # Get initial score from Phase 1 (calculated from website + Tavily data)
    web_score = phase1_data.get('initial_score', 50)

    # Calculate MCQ average
    mcq_scores = [ans.get('score', 50) for ans in mcq_answers.values()]
    mcq_avg = sum(mcq_scores) / len(mcq_scores) if mcq_scores else 50

    # Final score: 35% web + 65% MCQ
    final_score = int((web_score * 0.35) + (mcq_avg * 0.65))

    print(f"\n📊 SCORE CALCULATION:")
    print(f"   Initial web score: {web_score} × 0.35 = {web_score * 0.35:.1f}")
    print(f"   MCQ average: {mcq_avg:.1f} × 0.65 = {mcq_avg * 0.65:.1f}")
    print(f"   Final Score: {final_score}/100\n")

    # Determine maturity tag
    if final_score <= 25:
        maturity_tag = "Novice"
    elif final_score <= 50:
        maturity_tag = "Explorer"
    elif final_score <= 75:
        maturity_tag = "Pacesetter"
    else:
        maturity_tag = "Trailblazer"

    # Get config for LLM (need to reinitialize)
    # Assuming keys are available in environment or passed through
    import os
    gemini_key = os.getenv('GEMINI_API_KEY', '')
    tavily_key = os.getenv('TAVILY_API_KEY', '')

    analyzer = AIMaturityAnalyzer(gemini_key, tavily_key)

    # Generate final content
    final_content = analyzer.generate_final_content(
        website_content=phase1_data['website_content'],
        external_info=phase1_data['external_info'],
        company_name=phase1_data['company_name'],
        final_score=final_score,
        mcq_answers=mcq_answers,
        gaps=phase1_data['gaps']
    )

    # Combine everything
    result = {
        'overall_score': final_score,
        'maturity_tag': maturity_tag,
        'web_score': web_score,
        'mcq_score': int(mcq_avg),
        'summary': final_content.get('summary', ''),
        'evidence': {
            'strengths': final_content.get('strengths', []),
            'gaps': phase1_data['gaps'],  # Gaps from Phase 1
            'opportunities': final_content.get('opportunities', [])
        },
        'sources': phase1_data['sources'],
        'search_metadata': {
            'gaps_identified': phase1_data['gaps'],
            'queries_generated': phase1_data['queries']
        }
    }

    print(f"✅ PHASE 2 COMPLETE - Final Score: {final_score}/100 ({maturity_tag})\n")

    return result
