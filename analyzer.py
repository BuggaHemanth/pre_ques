"""
AI-powered analysis and scoring module using Gemini and Tavily
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from tavily import TavilyClient
from typing import Dict, List
import json
import os


class AIMaturityAnalyzer:
    """Analyzes company data and scores AI maturity"""

    def __init__(self, gemini_api_key: str, tavily_api_key: str):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=gemini_api_key,
            temperature=0.0
        )
        self.tavily = TavilyClient(api_key=tavily_api_key)

        # Scoring dimensions
        self.dimensions = [
            "AI Technology Adoption",
            "Digital Infrastructure",
            "Innovation & R&D",
            "Data Capabilities",
            "Technical Talent & Expertise"
        ]

    def search_external_info(self, company_name: str) -> tuple[str, List[Dict]]:
        """Use Tavily to search for external information about the company

        Returns:
            Tuple of (info_text, source_links)
        """
        try:
            # Search for AI-related information
            query = f'"{company_name}" artificial intelligence AI Large Lanugage Models LLM technology digital transformation'

            print("\n" + "="*80)
            print("🔍 TAVILY SEARCH QUERY:")
            print("="*80)
            print(f"Query: {query}")
            print(f"Search Depth: advanced")
            print(f"Topic: news")
            print(f"Max Results: 5")
            print("="*80 + "\n")

            search_results = self.tavily.search(
                query=query,
                search_depth="advanced",
                topic = 'news',
                max_results=5
            )

            print(f"✓ Tavily returned {len(search_results.get('results', []))} results\n")

            # Compile results and track sources
            external_info = []
            sources = []
            for result in search_results.get('results', []):
                url = result.get('url', 'N/A')
                content = result.get('content', '')
                title = result.get('title', 'External Source')
                external_info.append(f"Source: {url}\n{content}")
                sources.append({
                    'url': url,
                    'title': title,
                    'type': 'Tavily Search'
                })
                print(f"  - {title}: {url}")

            info_text = "\n\n".join(external_info) if external_info else "No external information found."
            print(f"\n✓ Compiled {len(sources)} external sources\n")
            return info_text, sources

        except Exception as e:
            return f"Error fetching external data: {str(e)}", []

    def generate_intelligent_questions(self, website_content: str, external_info: str, company_name: str, preliminary_analysis: Dict) -> List[Dict]:
        """
        Generate 3 intelligent MCQs based on gaps in available information

        Returns:
            List of 3 questions with options
        """
        question_prompt = f"""Based on the preliminary analysis of {company_name}, generate 3 multiple-choice questions to fill gaps in understanding their AI maturity.

PRELIMINARY FINDINGS:
- Score: {preliminary_analysis.get('overall_score', 0)}/100
- Gaps identified: {', '.join(preliminary_analysis.get('evidence', {}).get('gaps', []))}

Generate 3 strategic questions that will help refine the assessment. Each question should have 5 options (A-E) ranging from low to high maturity.

Return ONLY valid JSON in this exact format:
{{
    "questions": [
        {{
            "question": "Question text here?",
            "options": [
                {{"label": "A", "text": "Option A text", "score": 0}},
                {{"label": "B", "text": "Option B text", "score": 25}},
                {{"label": "C", "text": "Option C text", "score": 50}},
                {{"label": "D", "text": "Option D text", "score": 75}},
                {{"label": "E", "text": "Option E text", "score": 100}}
            ]
        }},
        {{
            "question": "Second question?",
            "options": [...]
        }},
        {{
            "question": "Third question?",
            "options": [...]
        }}
    ]
}}

Make questions specific to areas where information was unclear or missing."""

        print("\n" + "="*80)
        print("❓ GEMINI MCQ GENERATION PROMPT:")
        print("="*80)
        print(question_prompt[:800] + "..." if len(question_prompt) > 800 else question_prompt)
        print("="*80 + "\n")

        try:
            print("Generating MCQs with Gemini...")
            response = self.llm.invoke(question_prompt)
            print("✓ MCQs generated\n")
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

            questions_data = json.loads(response_text)
            return questions_data.get('questions', [])

        except Exception as e:
            print(f"Error generating questions: {e}")
            # Return default questions
            return [
                {
                    "question": "What best describes your current data infrastructure?",
                    "options": [
                        {"label": "A", "text": "Primarily paper-based or legacy systems", "score": 0},
                        {"label": "B", "text": "Digital but siloed across departments", "score": 25},
                        {"label": "C", "text": "Centralized with some integration", "score": 50},
                        {"label": "D", "text": "Cloud-based with APIs and data lakes", "score": 75},
                        {"label": "E", "text": "Real-time, AI-ready data architecture", "score": 100}
                    ]
                },
                {
                    "question": "How does your organization approach AI adoption?",
                    "options": [
                        {"label": "A", "text": "No current plans for AI", "score": 0},
                        {"label": "B", "text": "Exploring possibilities", "score": 25},
                        {"label": "C", "text": "Running pilot projects", "score": 50},
                        {"label": "D", "text": "Deploying AI in production", "score": 75},
                        {"label": "E", "text": "AI-first strategy across operations", "score": 100}
                    ]
                },
                {
                    "question": "What is your team's AI/ML expertise level?",
                    "options": [
                        {"label": "A", "text": "No AI expertise in-house", "score": 0},
                        {"label": "B", "text": "Basic understanding, no specialists", "score": 25},
                        {"label": "C", "text": "1-2 AI specialists or contractors", "score": 50},
                        {"label": "D", "text": "Dedicated AI/ML team", "score": 75},
                        {"label": "E", "text": "Advanced AI research & development team", "score": 100}
                    ]
                }
            ]

    def analyze_and_score(self, website_content: str, external_info: str, company_name: str, mcq_answers: Dict = None) -> Dict:
        """
        Analyze website and external content to score AI maturity

        Returns:
            Dict with score, tag, summary, and dimensional breakdown
        """

        analysis_prompt = f"""You are an AI readiness and maturity assessment expert. Analyze the following information about {company_name} and provide a comprehensive AI readiness and maturity assessment.

WEBSITE CONTENT:
{website_content[:15000]}

EXTERNAL INFORMATION:
{external_info[:5000]}

Based on this information, provide a detailed assessment covering these dimensions:
1. AI Technology Adoption (current use of AI/ML technologies)
2. Digital Infrastructure (cloud, APIs, data architecture)
3. Innovation & R&D (investment in new technologies)
4. Data Capabilities (data collection, management, analytics)
5. Technical Talent & Expertise (team capabilities, hiring patterns)

Provide your response in the following JSON format:
{{
    "overall_score": <number between 0-100>,
    "maturity_tag": "<Novice|Explorer|Pacesetter|Trailblazer>",
    "dimensional_scores": {{
        "AI Technology Adoption": <0-100>,
        "Digital Infrastructure": <0-100>,
        "Innovation & R&D": <0-100>,
        "Data Capabilities": <0-100>,
        "Technical Talent & Expertise": <0-100>
    }},
    "summary": "<2-3 paragraph summary of current state, strengths, and gaps>",
    "key_findings": [
        "<finding 1>",
        "<finding 2>",
        "<finding 3>",
        "<finding 4>"
    ],
    "evidence": {{
        "strengths": ["<strength 1>", "<strength 2>"],
        "gaps": ["<gap 1>", "<gap 2>"],
        "opportunities": ["<opportunity 1>", "<opportunity 2>"]
    }}
}}

Scoring guidelines:
- 0-25 (Novice): No AI adoption, traditional processes, limited digital infrastructure
- 26-50 (Explorer): Experimenting with AI, some digital transformation, pilot projects
- 51-75 (Pacesetter): Active AI integration, modern infrastructure, proven use cases
- 76-100 (Trailblazer): AI-native operations, advanced implementation, industry leadership

Be objective and evidence-based. If information is limited, acknowledge it in the summary."""

        print("\n" + "="*80)
        print("🤖 GEMINI ANALYSIS PROMPT:")
        print("="*80)
        print(analysis_prompt[:1000] + "..." if len(analysis_prompt) > 1000 else analysis_prompt)
        print("="*80 + "\n")

        try:
            # Use Gemini for analysis
            print("Calling Gemini API...")
            response = self.llm.invoke(analysis_prompt)
            print("✓ Gemini response received\n")

            # Parse JSON response
            response_text = response.content

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            analysis_result = json.loads(response_text)

            # Validate and ensure all fields exist
            if 'overall_score' not in analysis_result:
                raise ValueError("Missing overall_score in response")

            # Adjust score based on MCQ answers if provided
            base_score = analysis_result['overall_score']

            if mcq_answers:
                # Calculate MCQ score (average of answered questions)
                mcq_scores = [answer.get('score', 50) for answer in mcq_answers.values()]
                mcq_avg = sum(mcq_scores) / len(mcq_scores) if mcq_scores else 50

                # Weight: 70% website analysis, 30% MCQ answers
                final_score = int((base_score * 0.7) + (mcq_avg * 0.3))
                analysis_result['overall_score'] = final_score
                analysis_result['base_score'] = base_score
                analysis_result['mcq_score'] = int(mcq_avg)
                score = final_score
            else:
                score = base_score

            # Determine tag based on final score
            if score <= 25:
                correct_tag = "Novice"
            elif score <= 50:
                correct_tag = "Explorer"
            elif score <= 75:
                correct_tag = "Pacesetter"
            else:
                correct_tag = "Trailblazer"

            analysis_result['maturity_tag'] = correct_tag

            return analysis_result

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Analysis Error: {error_details}")  # Log to console

            # Return default structure on error
            return {
                "overall_score": 0,
                "maturity_tag": "Novice",
                "dimensional_scores": {dim: 0 for dim in self.dimensions},
                "summary": f"Error during analysis: {str(e)}\n\nPlease check the console for detailed error information.",
                "key_findings": [f"Analysis error: {str(e)}"],
                "evidence": {
                    "strengths": [],
                    "gaps": [],
                    "opportunities": []
                },
                "error": str(e),
                "error_details": error_details
            }

    def generate_personalized_message(self, company_name: str, score: int, tag: str) -> str:
        """Generate personalized email message based on assessment results"""

        cta_map = {
            "Novice": "Start Your AI Journey - Discover What's Possible",
            "Explorer": "Accelerate Your AI Adoption - See Our Proven Framework",
            "Pacesetter": "Scale Your AI Initiatives - Enterprise Solutions",
            "Trailblazer": "Maintain Your Edge - Advanced AI Optimization"
        }

        message = f"""Dear {company_name} Team,

Thank you for using our AI Maturity Assessment tool!

Based on our analysis of your website and public information, your organization scores {score}/100, placing you in the **{tag}** category.

"""

        if tag == "Novice":
            message += """This indicates you're at the beginning of your AI journey. Many successful companies started exactly where you are. The key is taking that first strategic step."""
        elif tag == "Explorer":
            message += """You're actively exploring AI possibilities. This experimental phase is crucial - it's where you learn what works for your specific context."""
        elif tag == "Pacesetter":
            message += """You're ahead of most organizations with active AI integration. The challenge now is scaling what works and filling strategic gaps."""
        else:  # Trailblazer
            message += """You're leading in AI adoption. Maintaining this edge requires continuous innovation and optimization of existing systems."""

        message += f"""

**Next Step: Complete Our Comprehensive Assessment**

This quick website scan provides valuable insights, but for a complete picture of your AI readiness, we invite you to complete our detailed questionnaire:

🔗 **Complete Full Assessment**: https://ai-maturity.streamlit.app/

The comprehensive assessment covers:
- Internal processes and workflows
- Data infrastructure and governance
- Team capabilities and organizational readiness
- Strategic planning and resource allocation
- Technology stack and integration capabilities

**{cta_map[tag]}**

Companies that complete both assessments receive:
✓ Holistic maturity scoring across all dimensions
✓ Detailed gap analysis with priorities
✓ Personalized AI roadmap
✓ Free 30-minute strategy consultation

We look forward to helping you advance your AI capabilities!

Best regards,
The AI Maturity Assessment Team
"""

        return message

    def compare_to_benchmarks(self, score: int) -> Dict:
        """Generate benchmark comparison data"""
        # Simulated benchmarks - in production, these would come from a database
        industry_avg = 52
        top_performers = 78

        percentile = min(99, max(1, int((score / 100) * 100)))

        return {
            "your_score": score,
            "industry_average": industry_avg,
            "top_performers": top_performers,
            "percentile": percentile,
            "comparison_text": f"You're ahead of {percentile}% of companies in digital maturity."
        }


def analyze_company(company_name: str, website_content: str,
                   gemini_api_key: str, tavily_api_key: str, mcq_answers: Dict = None,
                   scraped_pages: List[Dict] = None) -> Dict:
    """
    Main analysis function

    Args:
        company_name: Name of the company
        website_content: Scraped website text
        gemini_api_key: Gemini API key
        tavily_api_key: Tavily API key
        mcq_answers: Optional MCQ answers from user
        scraped_pages: Optional list of scraped pages for transparency

    Returns:
        Complete analysis results with sources
    """
    analyzer = AIMaturityAnalyzer(gemini_api_key, tavily_api_key)

    # Get external information (returns text and sources)
    external_info, external_sources = analyzer.search_external_info(company_name)

    # Perform analysis
    analysis = analyzer.analyze_and_score(website_content, external_info, company_name, mcq_answers)

    # Generate MCQs if no answers provided yet (for initial analysis)
    if not mcq_answers:
        analysis['questions'] = analyzer.generate_intelligent_questions(
            website_content, external_info, company_name, analysis
        )

    # Add benchmarks
    analysis['benchmarks'] = analyzer.compare_to_benchmarks(analysis['overall_score'])

    # Generate email message
    analysis['email_message'] = analyzer.generate_personalized_message(
        company_name,
        analysis['overall_score'],
        analysis['maturity_tag']
    )

    # Add sources for transparency
    analysis['sources'] = {
        'external_sources': external_sources,
        'scraped_pages': scraped_pages if scraped_pages else []
    }

    # Debug logging
    print("\n" + "="*80)
    print("📊 ANALYSIS RESULTS SUMMARY:")
    print("="*80)
    print(f"Questions generated: {len(analysis.get('questions', []))}")
    print(f"External sources: {len(external_sources)}")
    print(f"Scraped pages: {len(scraped_pages) if scraped_pages else 0}")
    print(f"MCQ answers provided: {mcq_answers is not None}")
    if 'questions' in analysis and analysis['questions']:
        print("\nGenerated Questions:")
        for i, q in enumerate(analysis['questions'][:3], 1):
            print(f"  Q{i}: {q.get('question', 'N/A')[:80]}...")
    print("="*80 + "\n")

    return analysis
