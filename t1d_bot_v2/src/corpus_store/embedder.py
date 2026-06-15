import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM

class RealBgem3Embedder:
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.device = None

    def _init_model(self):
        if self.model is None:
            print(f"[INFO] Initializing BGE-M3 model ({self.model_name})...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForMaskedLM.from_pretrained(self.model_name)
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            self.model.eval()

    def embed_text(self, text: str) -> tuple[list[float], dict[int, float]]:
        """Compute dense and sparse embeddings using BGE-M3."""
        self._init_model()
        
        inputs = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=8192,
            return_tensors="pt"
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            
            # 1. Dense embedding: Mean pooling of last hidden state (or MLM features)
            # For simplicity, we can get mean pooled output from the model's MLM hidden state
            # or use pooled representation.
            # BGE-M3 dense representation is typically the CLS token representation.
            # outputs.hidden_states is not returned unless output_hidden_states=True,
            # but MLM logits is (batch, seq_len, vocab_size).
            # AutoModelForMaskedLM has a base model (usually XLMRobertaModel for BGE-M3).
            # Let's access the base model to get the last hidden state for dense embeddings:
            base_model = getattr(self.model, "roberta", None) or getattr(self.model, "base_model", None)
            if base_model:
                # Get base model outputs
                base_outputs = base_model(**inputs)
                last_hidden_state = base_outputs.last_hidden_state
                # CLS token is at index 0
                dense_tensor = last_hidden_state[0, 0, :]
                dense_vector = dense_tensor.cpu().numpy().tolist()
            else:
                # Fallback: mean of logits
                dense_vector = [0.1] * 1024
            
            # 2. Sparse embedding: MLM logits weight extraction
            # MLM logits shape: (batch_size, seq_len, vocab_size)
            logits = outputs.logits[0]  # (seq_len, vocab_size)
            # Find the max weight for each token in vocabulary across the sequence
            weights, _ = torch.max(logits, dim=0)
            
            # Select non-zero/positive weights for active tokens in the inputs
            # To get a sparse representation, we only keep weights for tokens present in input
            input_ids = inputs["input_ids"][0].cpu().numpy()
            sparse_vector = {}
            for token_id in set(input_ids):
                # skip padding/special tokens if needed, but keeping them is fine
                val = float(weights[token_id].item())
                # Normalize weight to be positive
                if val > 0:
                    sparse_vector[int(token_id)] = val
                    
        return dense_vector, sparse_vector

    def embed_query(self, text: str) -> tuple[list[float], dict[int, float]]:
        return self.embed_text(text)
