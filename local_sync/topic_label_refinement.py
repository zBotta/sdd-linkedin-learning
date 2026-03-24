from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path


@dataclass(slots=True)
class RefinementConfig:
    use_keybert_inspired: bool = True
    use_mmr: bool = True
    use_llama_cpp: bool = False
    llama_cpp_model_path: Path | None = None


def build_representation_model(config: RefinementConfig) -> object | None:
    """Build BERTopic representation stack: KeyBERTInspired, MMR, optional LlamaCPP."""
    if find_spec("bertopic") is None:
        return None

    from bertopic.representation import KeyBERTInspired, MaximalMarginalRelevance

    models: dict[str, object] = {}
    if config.use_keybert_inspired:
        models["KeyBERTInspired"] = KeyBERTInspired()
    if config.use_mmr:
        models["MMR"] = MaximalMarginalRelevance(diversity=0.3)

    if config.use_llama_cpp and config.llama_cpp_model_path and config.llama_cpp_model_path.exists():
        if find_spec("llama_cpp") is not None:
            try:
                from bertopic.representation import LlamaCPP

                models["LlamaCPP"] = LlamaCPP(str(config.llama_cpp_model_path))
            except Exception:
                pass

    if not models:
        return None

    if len(models) == 1:
        return next(iter(models.values()))
    return models
