"""
Supervisor agent for orchestrating and synthesizing multi-agent responses.
"""

from typing import Dict, List, Any
from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent
from .state import MultiAgentState
from ..config import settings


class SupervisorAgent(BaseAgent):
    """Agent for combining and synthesizing responses from all agents."""

    def __init__(self):
        super().__init__("SupervisorAgent")
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.2,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    def execute(self, state: MultiAgentState) -> Dict[str, Any]:
        """
        Execute supervisor: combine all agent responses into final answer.

        Args:
            state: Current multi-agent state with all agent responses

        Returns:
            Dict: Partial state update with supervisor-specific fields only
        """
        query = state["query"]

        print(f"\n[SUPERVISOR] Executing")
        print(f"[SUPERVISOR] RAG confidence: {state.get('rag_confidence', 'N/A')}")
        print(f"[SUPERVISOR] Temporal confidence: {state.get('temporal_confidence', 'N/A')}")

        # Display RAG source metadata if available
        rag_metadata = state.get("rag_source_metadata")
        if rag_metadata:
            print(f"[SUPERVISOR] RAG source mix: {rag_metadata.get('source_mix', 'N/A')}")

        # Collect responses from all agents
        responses = self.combine_responses(state)
        print(f"[SUPERVISOR] Collected {len(responses)} responses")

        if not responses:
            # Return only supervisor fields
            return {
                "final_answer": "No responses available from agents.",
                "confidence_score": 0.0,
                "primary_source": "none",
                "citations": []
            }

        # Apply weighted prioritization
        primary_source = self.prioritize_local_context(state)

        # Check for conflicts (optional - basic implementation)
        # In production, could add conflict detection logic here

        # Synthesize final answer
        final_answer = self.synthesize_answer(query, responses, primary_source)

        # Format citations
        citations = self.format_citations(state)

        # Calculate final confidence
        confidence = self.calculate_final_confidence(state)

        # Return only supervisor fields
        return {
            "final_answer": final_answer,
            "confidence_score": confidence,
            "primary_source": primary_source,
            "citations": citations
        }

    def combine_responses(self, state: MultiAgentState) -> List[Dict]:
        """
        Collect and filter responses from all agents.

        Args:
            state: Multi-agent state

        Returns:
            List[Dict]: List of non-empty responses
        """
        responses = []

        # RAG agent response
        if state.get("rag_response"):
            responses.append({
                "agent": "RAG",
                "response": state["rag_response"],
                "confidence": state.get("rag_confidence", 0.0),
                "type": "local"
            })

        # Temporal agent response
        if state.get("temporal_response"):
            responses.append({
                "agent": "Temporal",
                "response": state["temporal_response"],
                "confidence": state.get("temporal_confidence", 0.0),
                "type": "local"
            })

        return responses

    def prioritize_local_context(self, state: MultiAgentState) -> str:
        """Determine primary source based on confidence weights."""
        rag_conf = state.get("rag_confidence", 0.0)
        temporal_conf = state.get("temporal_confidence", 0.0)

        # Determine primary source based on higher confidence
        if rag_conf >= temporal_conf:
            return "rag"
        elif temporal_conf > 0:
            return "temporal"
        else:
            return "rag"  # Default to RAG

    def synthesize_answer(self, query: str, responses: List[Dict], primary_source: str) -> str:
        """Synthesize final answer from all responses using LLM."""
        # All responses are now local (no web separation)
        local_responses = responses

        # Format responses
        local_text = "\n\n".join([
            f"[{r['agent']}]\n{r['response']}"
            for r in local_responses
        ]) if local_responses else "Δεν βρέθηκαν αποτελέσματα."

        # Create synthesis prompt
        priority_instruction = (
            "Δώσε προτεραιότητα στο RAG agent."
            if primary_source == "rag"
            else "Δώσε προτεραιότητα στο Temporal agent."
        )

        prompt = f"""Ερώτηση: {query}

Απαντήσεις από Agents:
{local_text}

{priority_instruction}

Συνδύασε τις απαντήσεις σε μία ολοκληρωμένη απάντηση που:
1. Απαντά στην ερώτηση με σαφήνεια
2. Διατηρεί τις αναφορές σε ΦΕΚ και τις σημειώσεις για γενικές γνώσεις
3. Διατηρεί τη διάκριση μεταξύ πληροφοριών από ΦΕΚ και γενικών γνώσεων
4. Είναι συνοπτική αλλά πλήρης

Απάντηση:"""

        response = self.llm.invoke(prompt)
        return response.content

    def format_citations(self, state: MultiAgentState) -> List[Dict]:
        """
        Format all citations from all sources.

        Args:
            state: Multi-agent state

        Returns:
            List[Dict]: Formatted citations
        """
        citations = []

        # Local sources (RAG and Temporal)
        all_local_docs = []

        if state.get("rag_sources"):
            all_local_docs.extend(state["rag_sources"])

        if state.get("temporal_sources"):
            all_local_docs.extend(state["temporal_sources"])

        # Deduplicate by source name
        seen_sources = set()
        for doc in all_local_docs:
            source = doc.metadata.get("source")
            if source and source not in seen_sources:
                seen_sources.add(source)

                fek_number = doc.metadata.get("fek_number", "N/A")
                date = doc.metadata.get("publication_date", "N/A")

                citation = {
                    "type": "local",
                    "source": source,
                    "fek_number": fek_number,
                    "date": date,
                    "text": f"ΦΕΚ {fek_number}, Πηγή: {source}, Ημερομηνία: {date}"
                }
                citations.append(citation)

        return citations

    def calculate_final_confidence(self, state: MultiAgentState) -> float:
        """
        Calculate weighted final confidence with bonuses and penalties.

        Strategy:
        1. Use confidence-weighted average (higher confidence = more influence)
        2. Agreement boost: Both agents highly confident → increase confidence
        3. Disagreement penalty: Large confidence gap → decrease confidence
        4. Multi-source bonus: Having multiple perspectives is valuable

        Args:
            state: Multi-agent state with confidence scores

        Returns:
            float: Final confidence score (0.0 - 1.0)
        """
        rag_conf = state.get("rag_confidence", 0.0)
        temporal_conf = state.get("temporal_confidence", 0.0)

        # Case 1: Only one agent responded
        if temporal_conf == 0.0 and rag_conf > 0.0:
            return round(rag_conf, 2)
        elif rag_conf == 0.0 and temporal_conf > 0.0:
            return round(temporal_conf, 2)
        elif rag_conf == 0.0 and temporal_conf == 0.0:
            return 0.0

        # Case 2: Both agents responded
        # Use confidence-weighted average (not simple average)
        # This gives more influence to the more confident agent
        weights = [rag_conf, temporal_conf]
        total_weight = sum(weights)

        if total_weight > 0:
            # Weighted average: higher confidence agents have more influence
            weighted_avg = (rag_conf * rag_conf + temporal_conf * temporal_conf) / total_weight
        else:
            weighted_avg = 0.0

        # Agreement boost: If both agents highly confident (>=0.7), boost final score
        # This reflects that having two independent sources agree increases reliability
        if rag_conf >= 0.7 and temporal_conf >= 0.7:
            agreement_boost = 0.1
            weighted_avg = min(1.0, weighted_avg + agreement_boost)

        # Disagreement penalty: If confidences differ significantly (>0.5), reduce confidence
        # Large disagreement suggests uncertainty or conflicting information
        elif abs(rag_conf - temporal_conf) > 0.5:
            disagreement_penalty = 0.1
            weighted_avg = max(0.0, weighted_avg - disagreement_penalty)

        # Multi-source diversity bonus: Having 2 independent agents is inherently valuable
        # Small boost for having multiple perspectives (even if confidences differ)
        if rag_conf > 0.3 and temporal_conf > 0.3:
            diversity_bonus = 0.05
            weighted_avg = min(1.0, weighted_avg + diversity_bonus)

        return round(max(0.0, min(1.0, weighted_avg)), 2)


# Global instance
supervisor_agent = SupervisorAgent()
