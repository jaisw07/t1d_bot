from src.generation.generate import MedicalRAGGenerator

def test_generator():
    CORPUS_PATH = "dataset/master/ISPAD-English-2022/master_corpus.jsonl"
    
    generator = MedicalRAGGenerator(corpus_path=CORPUS_PATH)
    
    query = "What are the guidelines for insulin dosage in children?"
    
    print(f"Testing query: {query}")
    result = generator.generate(query, top_k=3)
    
    print("\n[ANSWER]")
    print(result["answer"])
    
    print("\n[SOURCES]")
    print(result["sources"])
    
    assert "sources" in result
    assert isinstance(result["sources"], list)
    print("\nTest passed!")

if __name__ == "__main__":
    test_generator()
