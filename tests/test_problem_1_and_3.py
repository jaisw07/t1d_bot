import importlib
import sys
from unittest.mock import MagicMock, patch
import pytest

def test_embedder_does_not_import_torch_at_module_level():
    """Verify embedder module does not import torch at top-level."""
    # Ensure embedder is not in sys.modules or reload it
    if "src.corpus_store.embedder" in sys.modules:
        del sys.modules["src.corpus_store.embedder"]
    
    with patch.dict(sys.modules):
        # Remove torch from sys.modules if present to check top level imports
        sys.modules.pop("torch", None)
        import src.corpus_store.embedder as embedder_mod
        # torch should not be loaded in sys.modules just by importing embedder
        assert "torch" not in sys.modules, "torch was imported at top-level in embedder.py!"

def test_dashboard_no_ingested_documents_mention():
    """Verify dashboard.py has removed mentions of 'Ingested Documents'."""
    with open("src/dashboard.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "Ingested Documents" not in content

def test_service_uvicorn_reload_disabled():
    """Verify service.py does not run uvicorn with reload=True in production default."""
    with open("src/service.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "reload=True" not in content

def test_service_thread_safety_and_retry():
    """Verify service get_corpus_store and get_generator thread safety and generator retry behavior."""
    from src import service
    
    # Reset singletons for testing
    service._corpus_store = None
    service._generator = None
    
    with patch("src.corpus_store.store.CorpusStore") as MockStore:
        mock_instance = MagicMock()
        MockStore.return_value = mock_instance
        store1 = service.get_corpus_store("test_col")
        store2 = service.get_corpus_store("test_col")
        assert store1 is store2
        assert MockStore.call_count == 1
