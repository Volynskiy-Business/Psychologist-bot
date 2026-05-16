"""TF-IDF vector store for sadness knowledge base.

Provides cosine similarity search over 15 conversation scenarios.
No external ML dependencies — uses only numpy (standard scientific library).

Usage:
    store = SadnessVectorStore()
    scenarios = store.search("мне грустно после ссоры", top_k=2)
"""

import re
from collections import defaultdict

import numpy as np

from app.knowledge.sadness_support import SCENARIOS, SadnessScenario

# Common Russian/English stopwords that add noise to TF-IDF
_STOPWORDS: frozenset[str] = frozenset({
    "и", "в", "на", "с", "по", "из", "для", "от", "до", "при", "за", "об",
    "не", "но", "а", "или", "как", "что", "это", "то", "так", "же", "уже",
    "он", "она", "оно", "они", "мы", "вы", "я", "его", "её", "их", "им",
    "ему", "ей", "мне", "тебе", "нам", "вам", "себя", "себе",
    "the", "a", "an", "in", "on", "at", "to", "of", "for", "with", "and",
    "or", "but", "is", "are", "was", "were", "be", "been", "have", "has",
    "it", "he", "she", "they", "we", "you", "i", "my", "your", "his", "her",
})


def _tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumeric (handles Cyrillic), filter stopwords."""
    tokens = re.split(r"[^\w]+", text.lower())
    return [t for t in tokens if len(t) > 2 and t not in _STOPWORDS]


def _doc_text(s: SadnessScenario) -> str:
    """Combine all textual fields of a scenario into one searchable document."""
    parts = [
        s.title_ru,
        s.context_description_ru,
        " ".join(s.context_signals),
        " ".join(s.helpful_phrases),
        s.conversation_approach,
    ]
    return " ".join(parts)


class SadnessVectorStore:
    """Lazy-initialized TF-IDF index over the 15 sadness scenarios."""

    def __init__(self) -> None:
        self._scenarios: list[SadnessScenario] = []
        self._vocab: dict[str, int] = {}
        self._idf: np.ndarray | None = None
        self._tfidf_matrix: np.ndarray | None = None
        self._built = False

    def _build(self) -> None:
        self._scenarios = list(SCENARIOS)
        docs = [_doc_text(s) for s in self._scenarios]
        tokenized = [_tokenize(d) for d in docs]

        # Build vocabulary
        all_terms = sorted({t for tokens in tokenized for t in tokens})
        self._vocab = {t: i for i, t in enumerate(all_terms)}
        V = len(self._vocab)
        N = len(docs)

        # TF matrix (term frequency, normalised by doc length)
        tf_matrix = np.zeros((N, V), dtype=np.float32)
        for i, tokens in enumerate(tokenized):
            if not tokens:
                continue
            raw: dict[int, int] = defaultdict(int)
            for t in tokens:
                if t in self._vocab:
                    raw[self._vocab[t]] += 1
            for idx, count in raw.items():
                tf_matrix[i, idx] = count / len(tokens)

        # IDF (smooth variant)
        df = np.sum(tf_matrix > 0, axis=0).astype(np.float32)
        self._idf = np.log((N + 1) / (df + 1)).astype(np.float32) + 1.0

        # TF-IDF + L2 row normalisation
        tfidf = tf_matrix * self._idf
        norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._tfidf_matrix = (tfidf / norms).astype(np.float32)
        self._built = True

    def _query_vector(self, query: str) -> np.ndarray:
        tokens = _tokenize(query)
        V = len(self._vocab)
        vec = np.zeros(V, dtype=np.float32)
        if not tokens:
            return vec
        raw: dict[int, int] = defaultdict(int)
        for t in tokens:
            if t in self._vocab:
                raw[self._vocab[t]] += 1
        for idx, count in raw.items():
            vec[idx] = count / len(tokens)
        vec = vec * self._idf  # type: ignore[operator]
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        return vec

    def search(self, query: str, top_k: int = 2) -> list[SadnessScenario]:
        """Return up to *top_k* scenarios most relevant to *query*."""
        if not self._built:
            self._build()
        q_vec = self._query_vector(query)
        scores: np.ndarray = self._tfidf_matrix @ q_vec  # type: ignore[operator]
        top_indices = int(min(top_k, len(self._scenarios)))
        ranked = np.argsort(scores)[::-1][:top_indices]
        return [self._scenarios[int(i)] for i in ranked]


# Module-level singleton — built lazily on first search call.
sadness_store = SadnessVectorStore()
