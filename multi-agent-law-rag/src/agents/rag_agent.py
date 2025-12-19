"""
RAG agent using hybrid retrieval (semantic + BM25) and LLM generation.
"""

from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain.schema import Document

from .base_agent import BaseAgent
from .state import MultiAgentState
from ..config import settings
from ..vectorstore.vector_store import get_or_create_collection, get_hybrid_retriever


class RAGAgent(BaseAgent):
    """Agent for retrieving and answering from local document store."""

    def __init__(self):
        super().__init__("RAGAgent")
        self.vectorstore = None
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    def execute(self, state: MultiAgentState) -> Dict[str, Any]:
        """
        Execute RAG agent: retrieve documents and generate answer.

        Args:
            state: Current multi-agent state

        Returns:
            Dict: Partial state update with RAG-specific fields only
        """
        query = state["query"]
        print(f"\n[RAG AGENT] Executing with query: {query}")

        # Initialize vectorstore if needed
        if self.vectorstore is None:
            self.vectorstore = get_or_create_collection()

        # Retrieve relevant documents using hybrid search
        retrieved_docs = self.retrieve_context(query)

        if not retrieved_docs:
            # Return only RAG-specific fields
            return {
                "rag_response": "No relevant documents found in local database.",
                "rag_sources": [],
                "rag_confidence": 0.0
            }

        # Generate answer using LLM
        answer = self.generate_answer(query, retrieved_docs)

        # Extract source metadata
        source_metadata = self.extract_source_metadata(answer)

        # Calculate confidence based on retrieval quality
        confidence = self.calculate_confidence(retrieved_docs)

        # Return only RAG-specific fields
        return {
            "rag_response": answer,
            "rag_sources": retrieved_docs,
            "rag_confidence": confidence,
            "rag_source_metadata": source_metadata
        }

    def retrieve_context(self, query: str, k: int = None) -> List[Document]:
        """
        Retrieve relevant documents using hybrid search (semantic + BM25).

        Args:
            query: Query text
            k: Number of documents (uses config if None)

        Returns:
            List[Document]: Retrieved documents with similarity scores
        """
        if k is None:
            k = settings.RETRIEVAL_TOP_K

        # Get all documents for BM25 retriever
        # Note: For large collections, consider caching or separate BM25 index
        all_docs = self.vectorstore.similarity_search("", k=1000)

        # Create hybrid retriever
        hybrid_retriever = get_hybrid_retriever(
            vectorstore=self.vectorstore,
            documents=all_docs,
            k=k
        )

        # Retrieve documents
        docs = hybrid_retriever.invoke(query)

        # Also get similarity scores for confidence calculation
        docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=k)

        # Attach scores to documents for confidence calculation
        for doc, (scored_doc, score) in zip(docs[:k], docs_with_scores):
            doc.metadata['similarity_score'] = float(score)

        return docs[:k]  # Ensure we don't exceed k

    def generate_answer(self, query: str, context_docs: List[Document]) -> str:
        """
        Generate answer using LLM with retrieved context.

        Args:
            query: User query
            context_docs: Retrieved documents

        Returns:
            str: Generated answer
        """
        # Format context from documents
        context_parts = []
        for i, doc in enumerate(context_docs, 1):
            metadata = doc.metadata
            source = metadata.get("source", "Unknown")
            fek_number = metadata.get("fek_number", "N/A")
            doc_type = metadata.get("doc_type", "N/A")

            context_parts.append(
                f"[Έγγραφο {i}] ΦΕΚ: {fek_number}, Τύπος: {doc_type}, Πηγή: {source}\n"
                f"{doc.page_content[:500]}...\n"
            )

        context = "\n\n".join(context_parts)

        # Create prompt
        prompt = f"""Απάντησε στην ερώτηση βασιζόμενος ΚΥΡΙΩΣ στα ακόλουθα έγγραφα ΦΕΚ.

Έγγραφα:
{context}

Ερώτηση: {query}

ΟΔΗΓΙΕΣ:
1. Χρησιμοποίησε ΠΡΩΤΙΣΤΩΣ τις πληροφορίες από τα παραπάνω έγγραφα ΦΕΚ
2. Αν τα έγγραφα δεν καλύπτουν πλήρως την ερώτηση, ΜΠΟΡΕΙΣ να συμπληρώσεις με γενικές γνώσεις
3. Όταν χρησιμοποιείς πληροφορίες από ΦΕΚ, αναφέρε το ΦΕΚ
4. Όταν χρησιμοποιείς γενικές γνώσεις, ΠΡΕΠΕΙ να το δηλώσεις με φράσεις όπως:
   - "Βάσει γενικών γνώσεων..."
   - "Σημειώνεται (εκτός ΦΕΚ) ότι..."
   - "Επιπλέον (από γενική γνώση)..."
5. Ξεχώρισε ΣΑΦΩΣ τις πληροφορίες από ΦΕΚ από τις γενικές γνώσεις

Απάντηση:"""

        # Generate answer
        response = self.llm.invoke(prompt)
        return response.content

    def extract_source_metadata(self, response_text: str) -> Dict[str, Any]:
        """
        Extract metadata about information sources from the response.

        Returns:
            Dict: Metadata with keys: has_rag_info, has_pretrained_info, source_mix
        """
        pretrained_indicators = [
            "βάσει γενικών γνώσεων",
            "εκτός φεκ",
            "από γενική γνώση",
            "επιπλέον"
        ]

        has_pretrained = any(
            indicator in response_text.lower()
            for indicator in pretrained_indicators
        )

        has_rag = "ΦΕΚ" in response_text or "φεκ" in response_text.lower()

        return {
            "has_rag_info": has_rag,
            "has_pretrained_info": has_pretrained,
            "source_mix": "hybrid" if (has_rag and has_pretrained) else (
                "rag_only" if has_rag else "pretrained_only"
            )
        }

    def calculate_confidence(self, docs: List[Document]) -> float:
        """
        Calculate confidence based on retrieval quality using similarity scores.

        Args:
            docs: Retrieved documents (with similarity_score in metadata)

        Returns:
            float: Confidence score (0.0 - 1.0)
        """
        if not docs:
            return 0.0

        # Extract similarity scores from metadata
        scores = []
        for doc in docs:
            score = doc.metadata.get('similarity_score')
            if score is not None:
                # FAISS L2 distance: lower is better, convert to similarity
                # Typical range: 0-2, with <0.5 being very similar
                similarity = max(0.0, 1.0 - (score / 2.0))
                scores.append(similarity)

        if not scores:
            # Fallback: count-based confidence
            return min(len(docs) / settings.RETRIEVAL_TOP_K, 1.0)

        # Weighted average: first doc matters most
        weights = [1.0 / (i + 1) for i in range(len(scores))]  # 1.0, 0.5, 0.33, 0.25, 0.2
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        total_weight = sum(weights)

        confidence = weighted_sum / total_weight

        # Boost if we have multiple good matches
        if len(scores) >= settings.RETRIEVAL_TOP_K and scores[0] > 0.7:
            confidence = min(confidence * 1.1, 1.0)

        return round(confidence, 2)


# Global instance
rag_agent = RAGAgent()
