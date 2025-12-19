"""
Temporal agent for date-based filtering and chronological search.
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import dateparser
from langchain_openai import ChatOpenAI
from langchain.schema import Document

from .base_agent import BaseAgent
from .state import MultiAgentState
from ..config import settings
from ..vectorstore.vector_store import get_or_create_collection, similarity_search


class TemporalAgent(BaseAgent):
    """Agent for date-based filtering and chronological document search."""

    def __init__(self, use_llm_extraction: bool = True):
        """
        Initialize temporal agent.

        Args:
            use_llm_extraction: If True, use LLM to extract temporal intent (flexible).
                               If False, use only pattern matching (faster, cheaper).
        """
        super().__init__("TemporalAgent")
        self.vectorstore = None
        self.use_llm_extraction = use_llm_extraction
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0,  # Deterministic for date extraction
            max_tokens=300,
        )

    def execute(self, state: MultiAgentState) -> Dict[str, Any]:
        """
        Execute temporal agent: extract dates and filter documents.

        Args:
            state: Current multi-agent state

        Returns:
            Dict: Partial state update with temporal-specific fields only
        """
        query = state["query"]
        print(f"\n[TEMPORAL AGENT] Executing with query: {query}")

        # Extract date from query
        date_info = self.extract_date_from_query(query)

        if not date_info:
            # No date in query - return only temporal fields
            return {
                "temporal_response": "",
                "temporal_sources": [],
                "temporal_confidence": 0.0,
                "extracted_date": None,
                "temporal_filter": None
            }

        # Initialize vectorstore if needed
        if self.vectorstore is None:
            self.vectorstore = get_or_create_collection()

        # Filter documents by date
        filtered_docs = self.filter_by_date(query, date_info)

        if not filtered_docs:
            return {
                "temporal_response": f"No documents found for date range: {date_info}",
                "temporal_sources": [],
                "temporal_confidence": 0.3,
                "extracted_date": date_info.get("start_date"),
                "temporal_filter": date_info
            }

        # Sort chronologically
        sorted_docs = self.chronological_search(query, filtered_docs)

        # Generate temporal summary
        answer = self.generate_temporal_summary(query, sorted_docs, date_info)

        # Calculate confidence
        confidence = self.calculate_confidence(date_info, sorted_docs)

        # Return only temporal fields
        return {
            "temporal_response": answer,
            "temporal_sources": sorted_docs,
            "temporal_confidence": confidence,
            "extracted_date": date_info.get("start_date"),
            "temporal_filter": date_info
        }

    def extract_date_from_query(self, query: str) -> Optional[Dict]:
        """
        Extract date information from query using hybrid approach.

        Args:
            query: User query

        Returns:
            dict: Date info with keys: {start_date, end_date, operator, description}
                  Returns None if no date found
        """
        # Strategy 1: LLM extraction (flexible - catches variations)
        if self.use_llm_extraction:
            llm_result = self._extract_date_with_llm(query)
            if llm_result:
                return llm_result

        # Strategy 2: Pattern-based extraction (fast, reliable fallback)
        return self._extract_date_with_patterns(query)

    def _extract_date_with_llm(self, query: str) -> Optional[Dict]:
        """
        Use LLM to extract temporal intent - catches variations like 'νεότερα', 'σύγχρονοι'.

        This is flexible and understands intent, not just keywords.
        """
        now = datetime.now()
        current_year = now.year

        prompt = f"""Extract temporal information from this Greek/English query about laws. Return JSON only.

Current year: {current_year}

Query: {query}

If there's temporal intent, return:
{{
    "has_temporal": true,
    "type": "exact_year" | "year_range" | "recent" | "after" | "before",
    "start_year": 2020,
    "end_year": 2023,
    "description": "brief description"
}}

If NO temporal intent, return: {{"has_temporal": false}}

Examples:
"νόμοι το 2024" → {{"has_temporal": true, "type": "exact_year", "start_year": 2024, "end_year": 2024, "description": "in 2024"}}
"πρόσφατοι νόμοι" → {{"has_temporal": true, "type": "recent", "start_year": {current_year - 2}, "end_year": {current_year}, "description": "recent (last 2 years)"}}
"νεότερα νόμια" → {{"has_temporal": true, "type": "recent", "start_year": {current_year - 2}, "end_year": {current_year}, "description": "newer laws"}}
"παλιοί νόμοι" → {{"has_temporal": true, "type": "before", "start_year": 1900, "end_year": {current_year - 10}, "description": "old laws"}}
"μεταξύ 2020 και 2023" → {{"has_temporal": true, "type": "year_range", "start_year": 2020, "end_year": 2023, "description": "2020-2023"}}
"νόμοι για φόρους" → {{"has_temporal": false}}

JSON:"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)

            if result.get("has_temporal"):
                start_year = result["start_year"]
                end_year = result["end_year"]

                # Validate years
                if not (1900 <= start_year <= 2100 and 1900 <= end_year <= 2100):
                    return None

                return {
                    "start_date": datetime(start_year, 1, 1),
                    "end_date": datetime(end_year, 12, 31),
                    "operator": result["type"],
                    "description": result.get("description", "")
                }
        except Exception as e:
            # LLM extraction failed, will fall back to patterns
            print(f"[TEMPORAL] LLM extraction failed: {e}, falling back to patterns")
            pass

        return None

    def _extract_date_with_patterns(self, query: str) -> Optional[Dict]:
        """Pattern-based date extraction - fast and reliable."""
        # Strategy 1: Check for relative dates first (highest priority)
        relative_result = self._extract_relative_dates(query)
        if relative_result:
            return relative_result

        # Strategy 2: Check for date ranges
        range_result = self._extract_date_range(query)
        if range_result:
            return range_result

        # Strategy 3: Greek date patterns
        greek_patterns = {
            "after": r"(?:μετά|μετα)\s+(?:το|από|απο)\s+(\d{4})",
            "before": r"(?:πριν|προ)\s+(?:το|από|απο)\s+(\d{4})",
            "in_year": r"(?:το|στο|τον)\s+(\d{4})",
            "in_year_simple": r"\b(\d{4})\b",  # Year as standalone word
        }

        # Strategy 4: English patterns
        english_patterns = {
            "after": r"after\s+(\d{4})",
            "before": r"before\s+(\d{4})",
            "in_year": r"in\s+(\d{4})",
        }

        all_patterns = {**greek_patterns, **english_patterns}

        for pattern_type, pattern in all_patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                try:
                    year = int(match.group(1))

                    # Validate year range (1900-2100)
                    if year < 1900 or year > 2100:
                        continue

                    if pattern_type == "after":
                        return {
                            "start_date": datetime(year, 1, 1),
                            "end_date": datetime.now(),
                            "operator": "after",
                            "description": f"after {year}"
                        }
                    elif pattern_type == "before":
                        return {
                            "start_date": datetime(1900, 1, 1),
                            "end_date": datetime(year, 12, 31),
                            "operator": "before",
                            "description": f"before {year}"
                        }
                    elif pattern_type in ["in_year", "in_year_simple"]:
                        return {
                            "start_date": datetime(year, 1, 1),
                            "end_date": datetime(year, 12, 31),
                            "operator": "in",
                            "description": f"in {year}"
                        }
                except:
                    continue

        return None

    def _extract_relative_dates(self, query: str) -> Optional[Dict]:
        """Extract relative date expressions like 'last year', 'recently', etc."""
        now = datetime.now()
        current_year = now.year

        # Greek and English relative date patterns
        relative_patterns = {
            # Last year / πέρσι
            "last_year": [r"\b(πέρσι|περσι|πέρυσι|περυσι)\b", r"\blast\s+year\b"],
            # This year / φέτος
            "this_year": [r"\b(φέτος|φετος)\b", r"\bthis\s+year\b"],
            # Recent / πρόσφατα (last 2 years)
            "recent": [r"\b(πρόσφατ|προσφατ|recent)\w*\b"],
            # Last N years
            "last_n_years": [r"(?:τελευταί|τελευται|τελευταια|last)\s+(\d+)\s+(?:χρόνι|χρονι|years?)"],
        }

        for pattern_type, patterns in relative_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query, re.IGNORECASE)
                if match:
                    if pattern_type == "last_year":
                        return {
                            "start_date": datetime(current_year - 1, 1, 1),
                            "end_date": datetime(current_year - 1, 12, 31),
                            "operator": "in",
                            "description": f"last year ({current_year - 1})"
                        }
                    elif pattern_type == "this_year":
                        return {
                            "start_date": datetime(current_year, 1, 1),
                            "end_date": now,
                            "operator": "in",
                            "description": f"this year ({current_year})"
                        }
                    elif pattern_type == "recent":
                        # Last 2 years
                        return {
                            "start_date": datetime(current_year - 2, 1, 1),
                            "end_date": now,
                            "operator": "recent",
                            "description": "recent (last 2 years)"
                        }
                    elif pattern_type == "last_n_years":
                        n = int(match.group(1))
                        return {
                            "start_date": datetime(current_year - n, 1, 1),
                            "end_date": now,
                            "operator": "recent",
                            "description": f"last {n} years"
                        }

        return None

    def _extract_date_range(self, query: str) -> Optional[Dict]:
        """Extract date ranges like 'between 2020 and 2023' or '2020-2023'."""
        # Pattern: between X and Y / από X έως Y
        range_patterns = [
            r"(?:between|μεταξύ|μεταξυ)\s+(\d{4})\s+(?:and|και|έως|εως)\s+(\d{4})",
            r"(\d{4})\s*[-–—]\s*(\d{4})",  # 2020-2023 or 2020–2023
            r"(?:από|απο)\s+(\d{4})\s+(?:έως|εως|μέχρι|μεχρι)\s+(\d{4})",
        ]

        for pattern in range_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                try:
                    year1 = int(match.group(1))
                    year2 = int(match.group(2))

                    # Ensure valid range
                    if year1 > year2:
                        year1, year2 = year2, year1

                    # Validate years
                    if 1900 <= year1 <= 2100 and 1900 <= year2 <= 2100:
                        return {
                            "start_date": datetime(year1, 1, 1),
                            "end_date": datetime(year2, 12, 31),
                            "operator": "range",
                            "description": f"{year1}-{year2}"
                        }
                except:
                    continue

        return None

    def filter_by_date(self, query: str, date_info: Dict) -> List[Document]:
        """
        Filter documents by publication date.

        Args:
            query: User query (for semantic search)
            date_info: Date filter info

        Returns:
            List[Document]: Filtered documents
        """
        # Create date filter for FAISS metadata filtering
        start_date_str = date_info["start_date"].isoformat()
        end_date_str = date_info["end_date"].isoformat()

        # Metadata filter (FAISS applies post-retrieval)
        filters = {
            "publication_date": {
                "$gte": start_date_str,
                "$lte": end_date_str
            }
        }

        # Search with date filter
        # Need to search through many more documents when filtering by date
        # since temporal filtering drastically reduces the result set
        docs = similarity_search(
            query,
            vectorstore=self.vectorstore,
            k=500,  # Search through more documents to find date matches
            filters=filters
        )

        return docs

    def chronological_search(self, query: str, documents: List[Document]) -> List[Document]:
        """
        Sort documents chronologically based on query intent.

        Args:
            query: User query
            documents: Documents to sort

        Returns:
            List[Document]: Sorted documents
        """
        # Detect sort preference from query
        sort_order = self._detect_sort_preference(query)

        # Sort by publication date
        def get_date(doc):
            date_str = doc.metadata.get("publication_date")
            if date_str:
                try:
                    return datetime.fromisoformat(date_str)
                except:
                    return datetime.min
            return datetime.min

        # Apply sort order
        if sort_order == "oldest":
            sorted_docs = sorted(documents, key=get_date, reverse=False)
        else:  # newest (default)
            sorted_docs = sorted(documents, key=get_date, reverse=True)

        return sorted_docs

    def _detect_sort_preference(self, query: str) -> str:
        """
        Detect sort preference from query: 'oldest' or 'newest'.

        Args:
            query: User query

        Returns:
            str: "oldest" for ascending, "newest" for descending
        """
        # Explicit oldest-first indicators
        oldest_patterns = [
            r"\b(πρώτ|παλ|αρχ)\w*\b",  # πρώτος, παλιός, αρχικός
            r"\b(oldest|earliest|first|chronological)\b",
            r"\b(χρονολογικ)\w*\b",  # chronologically
        ]

        # Explicit newest-first indicators
        newest_patterns = [
            r"\b(τελευταί|νε[όω]τερ|πρόσφατ)\w*\b",  # τελευταίος, νεότερος, πρόσφατος
            r"\b(latest|newest|recent|modern)\b",
            r"\b(σύγχρον)\w*\b",  # σύγχρονος (modern)
        ]

        for pattern in oldest_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return "oldest"

        for pattern in newest_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return "newest"

        # Default: newest first (most common for legal queries)
        return "newest"

    def generate_temporal_summary(self, query: str, documents: List[Document], date_info: Dict) -> str:
        """
        Generate chronological summary using LLM.

        Args:
            query: User query
            documents: Sorted documents
            date_info: Date filter info

        Returns:
            str: Generated summary
        """
        if not documents:
            return "No documents found for the specified date range."

        # Format documents with dates
        doc_summaries = []
        for i, doc in enumerate(documents[:5], 1):  # Top 5
            metadata = doc.metadata
            date = metadata.get("publication_date", "N/A")
            fek_number = metadata.get("fek_number", "N/A")
            doc_type = metadata.get("doc_type", "N/A")

            doc_summaries.append(
                f"[{i}] Ημερομηνία: {date}, ΦΕΚ: {fek_number}, Τύπος: {doc_type}\n"
                f"{doc.page_content[:300]}..."
            )

        context = "\n\n".join(doc_summaries)

        prompt = f"""Ταξινόμησε και περίγραψε χρονολογικά τα ακόλουθα ΦΕΚ που σχετίζονται με την ερώτηση.

Ερώτηση: {query}
Φίλτρο Ημερομηνίας: {date_info.get('operator')} {date_info.get('start_date').year}

Έγγραφα:
{context}

ΣΗΜΑΝΤΙΚΟ:
- Χρησιμοποίησε ΜΟΝΟ τα παραπάνω έγγραφα ΦΕΚ
- ΜΗΝ προσθέσεις πληροφορίες από τη γενική σου γνώση
- Δώσε μια χρονολογική περίληψη ΜΟΝΟ των εγγράφων που παρουσιάζονται

Περίληψη:"""

        response = self.llm.invoke(prompt)
        return response.content

    def calculate_confidence(self, date_info: Dict, docs: List[Document]) -> float:
        """
        Calculate confidence based on query type AND result quality.

        Args:
            date_info: Date filter info
            docs: Retrieved documents

        Returns:
            float: Confidence score (0.0 - 1.0)
        """
        if not docs:
            return 0.0

        operator = date_info.get("operator", "in")
        num_docs = len(docs)

        # Base confidence by operator precision
        base_confidence = {
            "in": 1.0,           # Exact year: highest precision
            "exact_year": 1.0,   # Same as "in"
            "range": 0.9,        # Date range: very good
            "year_range": 0.9,   # Same as "range"
            "recent": 0.75,      # Relative dates: good but fuzzy
            "after": 0.7,        # Open-ended: moderate precision
            "before": 0.7,       # Open-ended: moderate precision
        }.get(operator, 0.5)

        # Adjust based on result count
        if num_docs == 0:
            return 0.0
        elif num_docs >= 10:
            # Many results: high confidence in temporal filtering
            count_multiplier = 1.0
        elif num_docs >= 5:
            # Decent results
            count_multiplier = 0.95
        elif num_docs >= 2:
            # Few results: slightly lower confidence
            count_multiplier = 0.85
        else:
            # Only 1 result: lower confidence
            count_multiplier = 0.7

        final_confidence = base_confidence * count_multiplier
        return round(min(final_confidence, 1.0), 2)


# Global instance
temporal_agent = TemporalAgent()
