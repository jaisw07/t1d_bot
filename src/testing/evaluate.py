import json
import os
from pathlib import Path
from tqdm import tqdm
from typing import List, Dict

def load_questions(file_path: str) -> List[Dict[str, str]]:
    """
    Parses the question bank file.
    Format:
    Type: ---
    Question 1
    Question 2
    
    Type: ---
    Question 3
    """
    questions = []
    current_type = None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("Type:"):
                current_type = line.replace("Type:", "").strip()
            else:
                if current_type:
                    questions.append({
                        "question": line,
                        "type": current_type
                    })
    return questions

def run_evaluation(questions_file: str, output_file: str, generator):
    """
    Runs evaluation on a question bank and saves results to JSON.
    """
    questions = load_questions(questions_file)
    results = []
    
    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[INFO] Starting evaluation on {len(questions)} questions")
    
    for item in tqdm(questions, desc="Evaluating"):
        question = item["question"]
        q_type = item["type"]
        
        try:
            # Generate answer
            response = generator.generate(question)
            answer = response["answer"]
            
            results.append({
                "question": question,
                "answer": answer,
                "type": q_type
            })
        except Exception as e:
            print(f"[ERROR] Failed to generate answer for: {question}")
            print(f"Details: {e}")
            results.append({
                "question": question,
                "answer": f"ERROR: {str(e)}",
                "type": q_type
            })
            
        # Save intermediate results to avoid data loss
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
    print(f"[INFO] Evaluation complete. Results saved to {output_file}")
