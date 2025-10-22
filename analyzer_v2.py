"""
AI-powered analysis module with intelligent Multi-Query Tavily search
Uses Gemini to generate targeted search queries based on gaps in information
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from tavily import TavilyClient
from typing import Dict, List
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


class AIMaturityAnalyzer:
    """Analyzes company data with intelligent multi-query search"""

    def __init__(self, gemini_api_key: str, tavily_api_key: str):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",  # Experimental model is faster
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
        """
        Analyze website content and generate targeted search queries

        Returns:
            Dict with 'gaps' and 'queries'
        """
        query_prompt = f"""Analyze this company's website content and identify what information is MISSING for assessing their AI maturity.

Company: {company_name}

Website Content (first 5000 chars):
{website_content[:5000]}

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
- "{company_name} company "AI-powered" case study results" (too many quotes)
- "{company_name} "machine learning" client testimonials "results"" (too complex)
- "{company_name} AI solutions AdTech implementation reviews" (too many keywords)
- "{company_name} artificial intelligence blog" (returns their own articles)
"""

        print("\n" + "="*80)
        print("🧠 GEMINI GENERATING SEARCH QUERIES")
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

            print(f"\n✅ Generated {len(queries)} targeted queries")
            print("\nGaps Identified:")
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
            print(f"❌ Error generating queries: {e}")
            # Fallback queries
            return {
                'gaps_identified': [
                    "Limited information about specific AI projects",
                    "Unclear technical capabilities and infrastructure",
                    "Missing details on AI implementation and results"
                ],
                'search_queries': [
                    f'{company_name} company AI projects case studies',
                    f'{company_name} company technology stack infrastructure',
                    f'{company_name} company AI solutions deployed'
                ]
            }

    def is_valid_source(self, url: str) -> bool:
        """
        Filter out invalid sources like individual LinkedIn profiles, PDFs, etc.

        Returns:
            True if source is valid, False otherwise
        """
        url_lower = url.lower()

        # Block file downloads (PDFs, documents, etc.)
        file_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.ashx', '.aspx', '.zip', '.rar', '.tar', '.gz'
        ]
        for ext in file_extensions:
            if url_lower.endswith(ext) or ext + '?' in url_lower:
                return False

        # Block individual LinkedIn profiles (but allow company pages)
        if 'linkedin.com/in/' in url_lower:
            return False

        # Allow LinkedIn company pages
        if 'linkedin.com/company/' in url_lower:
            return True

        # Block other social media profiles
        invalid_patterns = [
            '/profile/',
            '/user/',
            '/u/',
            'twitter.com/',
            'facebook.com/',
            'instagram.com/',
        ]

        for pattern in invalid_patterns:
            if pattern in url_lower:
                return False

        return True

    def _execute_single_search(self, query: str, idx: int) -> tuple:
        """
        Execute a single Tavily search (helper for parallel execution)

        Returns:
            Tuple of (query_results, query_sources)
        """
        print(f"\n🔍 Query {idx}: {query}")

        query_results = []
        query_sources = []

        try:
            search_results = self.tavily.search(
                query=query,
                max_results=4,  # Request 4 to account for filtering
                include_answer=True,
                search_depth="basic",
                days=365  # Only results from past 1 year
            )

            total_returned = len(search_results.get('results', []))
            print(f"  Tavily returned: {total_returned} links")

            # Get AI answer if available
            if 'answer' in search_results and search_results['answer']:
                query_results.append(f"Query: {query}\nAnswer: {search_results['answer']}")
                print(f"  + AI answer extracted")

            # Get individual results with filtering
            valid_count = 0
            filtered_count = 0
            for result in search_results.get('results', []):
                if valid_count >= 2:  # Only take 2 valid results per query
                    break

                url = result.get('url', 'N/A')

                # Filter out invalid sources
                if not self.is_valid_source(url):
                    filtered_count += 1
                    print(f"  X Filtered: {url[:70]}")
                    continue

                title = result.get('title', 'Source')
                content = result.get('content', '')

                # Extract content from all valid links
                query_results.append(f"Source: {title}\nURL: {url}\n{content}")
                query_sources.append({
                    'url': url,
                    'title': title,
                    'query': query
                })
                print(f"  + [{valid_count + 1}] {title[:65]}")
                valid_count += 1

            print(f"  Summary: {valid_count} valid, {filtered_count} filtered")

        except Exception as e:
            print(f"  X Error: {e}")

        return query_results, query_sources

    def execute_searches(self, queries: List[str]) -> tuple[str, List[Dict]]:
        """
        Execute Tavily searches for all queries IN PARALLEL with filtering

        Returns:
            Tuple of (combined_text, sources_list)
        """
        print("\n" + "="*80)
        print("🔍 EXECUTING TAVILY SEARCHES (PARALLEL)")
        print("="*80)

        all_results = []
        all_sources = []

        # Execute all searches in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all search tasks
            future_to_query = {
                executor.submit(self._execute_single_search, query, idx): query
                for idx, query in enumerate(queries, 1)
            }

            # Collect results as they complete
            for future in as_completed(future_to_query):
                try:
                    query_results, query_sources = future.result()
                    all_results.extend(query_results)
                    all_sources.extend(query_sources)
                except Exception as e:
                    print(f"  X Task error: {e}")

        combined_text = "\n\n---\n\n".join(all_results) if all_results else "No external information found."

        print(f"\n✅ TOTAL VALID SOURCES: {len(all_sources)} (content extracted from all)")
        print("="*80 + "\n")

        return combined_text, all_sources

    def generate_mcqs(self, company_name: str, preliminary_analysis: Dict) -> List[Dict]:
        """Generate 5 MCQs based on analysis gaps"""

        question_prompt = f"""Based on the preliminary analysis of {company_name}, generate 5 multiple-choice questions to clarify ambiguous areas.

Gaps identified: {', '.join(preliminary_analysis.get('evidence', {}).get('gaps', []))}

Generate 5 questions with 5 options each (A-E), progressing from low to high maturity.

CRITICAL REQUIREMENTS:
- Focus on AI adoption, data infrastructure, technology, and innovation
- DO NOT ask about employee count or team size
- Keep options SHORT and CRISP (maximum 6-8 words per option)
- Use simple, direct language
- Avoid lengthy descriptions

Example of GOOD options:
- "No AI usage"
- "Exploring AI tools"
- "Pilot AI projects"
- "Production AI systems"
- "Advanced AI at scale"

Example of BAD options (too long):
- "We have not yet started exploring artificial intelligence technologies"
- "We are currently in the process of evaluating various AI solutions"

Return ONLY valid JSON:
{{
    "questions": [
        {{
            "question": "Question text?",
            "options": [
                {{"label": "A", "text": "Short option (max 6-8 words)", "score": 0}},
                {{"label": "B", "text": "Short option (max 6-8 words)", "score": 25}},
                {{"label": "C", "text": "Short option (max 6-8 words)", "score": 50}},
                {{"label": "D", "text": "Short option (max 6-8 words)", "score": 75}},
                {{"label": "E", "text": "Short option (max 6-8 words)", "score": 100}}
            ]
        }}
    ]
}}
"""

        print("\n" + "="*80)
        print("❓ GENERATING MCQs")
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
            print(f"❌ Error generating MCQs: {e}")
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
                        {"label": "E", "text": "Continuous AI research & development", "score": 100}
                    ]
                },
                {
                    "question": "What AI technologies are you currently using?",
                    "options": [
                        {"label": "A", "text": "None at all", "score": 0},
                        {"label": "B", "text": "Basic automation tools", "score": 25},
                        {"label": "C", "text": "ML for analytics", "score": 50},
                        {"label": "D", "text": "NLP and computer vision", "score": 75},
                        {"label": "E", "text": "Advanced AI agents and LLMs", "score": 100}
                    ]
                },
                {
                    "question": "How is AI integrated in your workflows?",
                    "options": [
                        {"label": "A", "text": "Not integrated", "score": 0},
                        {"label": "B", "text": "Ad-hoc individual usage", "score": 25},
                        {"label": "C", "text": "Some team-level tools", "score": 50},
                        {"label": "D", "text": "Department-wide systems", "score": 75},
                        {"label": "E", "text": "Enterprise-wide AI platform", "score": 100}
                    ]
                }
            ]

    def analyze_and_score(self, website_content: str, external_info: str, company_name: str, mcq_answers: Dict = None) -> Dict:
        """Perform AI maturity analysis and scoring"""

        analysis_prompt = f"""You are an AI maturity assessment expert. Analyze this information about {company_name}.

WEBSITE CONTENT:
{website_content[:8000]}

EXTERNAL RESEARCH:
{external_info[:3000]}

Assess AI maturity across these dimensions:
1. AI Technology Adoption (ML, computer vision, NLP, predictive analytics)
2. LLM & AI Agents Implementation (GPT, Claude, custom LLMs, autonomous agents, RAG systems)
3. Digital Infrastructure (cloud, APIs, microservices, data pipelines)
4. Data Capabilities (data lakes, real-time analytics, data governance)
5. Innovation & R&D (AI research, experimentation, proof of concepts)

CRITICAL SCORING INSTRUCTIONS:
1. Base assessment ONLY on concrete evidence of ACTUAL IMPLEMENTATION, not marketing claims
2. DISTINGUISH between:
   - Content the company PUBLISHES about AI (blog posts, thought leadership, articles) → Lower weight
   - Evidence of what the company IMPLEMENTS/DOES (case studies, client results, technical deployments) → Higher weight
3. Look for specific evidence:
   - Named AI projects with results
   - Client testimonials about AI solutions
   - Technical details of implementations
   - Third-party validation or reviews
   - Specific tools/frameworks used
4. Red flags that indicate inflated claims (score lower):
   - Only general AI discussions without specifics
   - Thought leadership articles without implementation details
   - Marketing language without concrete evidence
   - Claims about "AI-powered" without technical details
5. Do NOT make assumptions. If information is missing, reflect that in lower scores
6. Be consistent - same input should produce same output

Return ONLY valid JSON:
{{
    "overall_score": <0-100>,
    "maturity_tag": "<Novice|Explorer|Pacesetter|Trailblazer>",
    "dimensional_scores": {{
        "AI Technology Adoption": <0-100>,
        "LLM & AI Agents Implementation": <0-100>,
        "Digital Infrastructure": <0-100>,
        "Data Capabilities": <0-100>,
        "Innovation & R&D": <0-100>
    }},
    "summary": "<2-3 paragraph analysis>",
    "key_findings": ["<finding 1>", "<finding 2>", "<finding 3>"],
    "evidence": {{
        "strengths": ["<strength 1>", "<strength 2>"],
        "gaps": ["<gap 1>", "<gap 2>"],
        "opportunities": ["<opportunity 1>", "<opportunity 2>"]
    }}
}}

Scoring: 0-25=Novice, 26-50=Explorer, 51-75=Pacesetter, 76-100=Trailblazer
"""

        print("\n" + "="*80)
        print("🤖 GEMINI ANALYZING & SCORING")
        print("="*80)

        try:
            response = self.llm.invoke(analysis_prompt)
            response_text = response.content

            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            analysis_result = json.loads(response_text)

            # Adjust score with MCQ answers if provided
            base_score = analysis_result['overall_score']

            if mcq_answers:
                mcq_scores = [ans.get('score', 50) for ans in mcq_answers.values()]
                mcq_avg = sum(mcq_scores) / len(mcq_scores)

                # 70% website analysis + 30% MCQ responses
                final_score = int((base_score * 0.4) + (mcq_avg * 0.60))
                analysis_result['overall_score'] = final_score
                analysis_result['base_score'] = base_score
                analysis_result['mcq_score'] = int(mcq_avg)

                print(f"✅ Final Score: {final_score} (Base: {base_score} [70%] + MCQ: {int(mcq_avg)} [30%])")
            else:
                print(f"✅ Initial Score: {base_score}")

            # Ensure correct tag
            score = analysis_result['overall_score']
            if score <= 25:
                tag = "Novice"
            elif score <= 50:
                tag = "Explorer"
            elif score <= 75:
                tag = "Pacesetter"
            else:
                tag = "Trailblazer"

            analysis_result['maturity_tag'] = tag
            print(f"✅ Maturity Tag: {tag}")
            print("="*80 + "\n")

            return analysis_result

        except Exception as e:
            print(f"❌ Analysis error: {e}")
            return {
                "overall_score": 0,
                "maturity_tag": "Novice",
                "dimensional_scores": {dim: 0 for dim in self.dimensions},
                "summary": f"Error during analysis: {str(e)}",
                "key_findings": ["Analysis error occurred"],
                "evidence": {"strengths": [], "gaps": [], "opportunities": []},
                "error": str(e)
            }


def analyze_company(company_name: str, website_content: str,
                   gemini_api_key: str, tavily_api_key: str,
                   mcq_answers: Dict = None, scraped_pages: List[Dict] = None) -> Dict:
    """
    Main analysis function with Multi-Query approach

    Returns:
        Complete analysis with queries, gaps, sources, and scores
    """
    analyzer = AIMaturityAnalyzer(gemini_api_key, tavily_api_key)

    # Step 1: Generate intelligent search queries
    query_data = analyzer.generate_search_queries(company_name, website_content)
    gaps = query_data['gaps_identified']
    queries = query_data['search_queries']

    # Step 2: Execute searches
    external_info, external_sources = analyzer.execute_searches(queries)

    # Step 3: Analyze and score
    analysis = analyzer.analyze_and_score(website_content, external_info, company_name, mcq_answers)

    # Step 4: Generate MCQs if first time
    if not mcq_answers:
        analysis['questions'] = analyzer.generate_mcqs(company_name, analysis)

    # Step 5: Add metadata
    analysis['sources'] = {
        'external_sources': external_sources,
        'scraped_pages': scraped_pages if scraped_pages else []
    }

    analysis['search_metadata'] = {
        'gaps_identified': gaps,
        'queries_generated': queries
    }

    print(f"\n✅ ANALYSIS COMPLETE - Questions: {len(analysis.get('questions', []))}, Sources: {len(external_sources)}\n")

    return analysis
