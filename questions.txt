1. Sentence Piece tokenizer for regional languages
Are you using it ?
The multilingual embedding model that we use, BAAI/bge-m3, internally utilizes a pre-trained XLM-RoBERTa-based tokenizer that uses SentencePiece. We use this out-of-the-box.

2. How is hallucination take care of?
Hallucination is managed strictly via prompting and hyperparameter tuning(temperature set to 0.1 to ensure deterministic, repeatable outputs) during the generation phase. There are no automated secondary verification loops or hallucination classifiers as of now.
The plan is to add an LLM guardrail post the generation step to act as a check.

3. I hope human annotators will not be required ?
Yes, no human annotation is required. The pipeline works as a zero-shot retrieval and generation flow. However, human effort will be required in the process of specifying page ranges (to select chapters) if adding large books to the sources for RAG to selectively use relevant content but it is not a mandatory step.

4. How are you taking care of fine tuning ?
No fine-tuning currently. This can be done once enough real usage data exists or I can generate synthetic data on questions and fine-tune the model on the good samples identified from it by a team of medical professionals (The data would need to be substantial so it may require substantial manual effort). Alternatively, I can fine-tune on some of the patient help handbook data we have which contains ques/ans pairs.

5. Did you spend enough time in comparing which models work well and did you document those findings or observations?
Given the time-constraint, this was not feasible as the primary goal was to get a RAG system working. Now with the pipeline in place, we can experiment with different embedding models, different llm's for semantic chunking and then the least time consuming step would be comparing different llm's for generation.

6. How do you safeguard from model drift?
Vendor-side updates which change model behaviour are guarded against by using a static open source local model. Content drift(if safe ranges or terminology changes) can be tackled by simply re-running pipeline on updated data. I can make a plan for deleting data that gets irrelevant over time.