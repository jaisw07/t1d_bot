import os

class RealBgem3Embedder:
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        self.model = None
        self.device = None

    def _init_model(self):
        if self.model is None:
            from FlagEmbedding import BGEM3FlagModel
            requested_device = os.getenv("EMBEDDER_DEVICE", "cpu")
            try:
                self.device = requested_device
                use_fp16 = (self.device == "cuda")
                print(f"[INFO] Initializing BGE-M3 model ({self.model_name}) on {self.device.upper()}...")
                self.model = BGEM3FlagModel(
                    self.model_name,
                    use_fp16=use_fp16,
                    device=self.device
                )
                print(f"[INFO] BGE-M3 model loaded successfully on {self.device.upper()}.")
            except Exception as e:
                if requested_device == "cuda":
                    print(f"[WARNING] CUDA initialization failed for BGE-M3 ({e}). Falling back to CPU.")
                    self.device = "cpu"
                    self.model = BGEM3FlagModel(
                        self.model_name,
                        use_fp16=False,
                        device="cpu"
                    )
                    print(f"[INFO] BGE-M3 model loaded successfully on CPU fallback.")
                else:
                    raise e

    def embed_text(self, text: str) -> tuple[list[float], dict[int, float]]:
        """Compute dense and sparse embeddings using BGE-M3."""
        self._init_model()
        output = self.model.encode(
            [text],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False
        )
        dense_vector = output["dense_vecs"][0].tolist()
        sparse_vector = {int(k): float(v) for k, v in output["lexical_weights"][0].items()}
        return dense_vector, sparse_vector

    def embed_query(self, text: str) -> tuple[list[float], dict[int, float]]:
        return self.embed_text(text)
