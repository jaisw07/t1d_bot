import streamlit as st
import os
from src.generation.generate import MedicalRAGGenerator

# =========================================================
# CONFIG & SETUP
# =========================================================

CORPUS_PATH = "dataset/master/ISPAD-English-2022/master_corpus.jsonl"
ST_PORT = 8501

st.set_page_config(
    page_title="T1D RAG Bot - ISPAD Guidelines",
    page_icon="🩺",
    layout="wide"
)

# Initialize generator in session state
if "generator" not in st.session_state:
    with st.spinner("Initializing Medical RAG Engine..."):
        st.session_state.generator = MedicalRAGGenerator(
            corpus_path=CORPUS_PATH,
            model_name="gemma4:e4b"
        )

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🩺 T1D RAG Settings")
st.sidebar.markdown("---")

top_k = st.sidebar.slider(
    "Retrieval Top-K",
    min_value=1,
    max_value=10,
    value=5,
    help="Number of semantic chunks to retrieve from the knowledge base."
)

st.sidebar.info(
    """
    **Note:** This bot is grounded in the ISPAD 2022 Guidelines. 
    It will only answer based on retrieved evidence.
    """
)

if st.sidebar.button("Clear Chat History"):
    st.session_state.messages = []
    st.rerun()

# =========================================================
# CHAT INTERFACE
# =========================================================

st.title("Pediatric Diabetes Assistant")
st.caption("Grounded in ISPAD 2022 Guidelines")

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # If there are sources or transparency info, display them
        if "sources" in message and message["sources"]:
            st.markdown(f"**Sources:** {', '.join(message['sources'])}")
        
        if "retrieval_package" in message and message["retrieval_package"]:
            with st.expander("🔍 Source Context (Transparency)"):
                for idx, r in enumerate(message["retrieval_package"]["retrievals"]):
                    st.markdown(f"### {idx+1}. {r['l2_chunk']['chapter_title']}")
                    st.markdown(f"**Score:** `{r['score']:.4f}`")
                    st.markdown("**Semantic Context (L2):**")
                    st.write(r['l2_chunk']['text'])
                    
                    if r.get("l3_facts"):
                        st.markdown("**Atomic Facts (L3):**")
                        for fact in r["l3_facts"]:
                            st.markdown(f"- {fact['content']['text']}")
                    st.divider()

# React to user input
if prompt := st.chat_input("Ask a question about pediatric diabetes..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Searching guidelines and generating answer..."):
            try:
                result = st.session_state.generator.generate(
                    query=prompt,
                    top_k=top_k
                )
                
                answer = result["answer"]
                sources = result["sources"]
                retrieval_package = result["retrieval_package"]

                # Display answer
                st.markdown(answer)
                
                # Display sources footer
                if sources:
                    st.markdown(f"**Sources:** {', '.join(sources)}")
                
                # Display Transparency Expander
                with st.expander("🔍 Source Context (Transparency)"):
                    for idx, r in enumerate(retrieval_package["retrievals"]):
                        st.markdown(f"### {idx+1}. {r['l2_chunk']['chapter_title']}")
                        st.markdown(f"**Score:** `{r['score']:.4f}`")
                        st.markdown("**Semantic Context (L2):**")
                        st.write(r['l2_chunk']['text'])
                        
                        if r.get("l3_facts"):
                            st.markdown("**Atomic Facts (L3):**")
                            for fact in r["l3_facts"]:
                                st.markdown(f"- {fact['content']['text']}")
                        st.divider()

                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "retrieval_package": retrieval_package
                })
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                if "Failed to connect to Ollama" in str(e):
                    st.warning("Please ensure Ollama is running locally with the `gemma4:e4b` model.")
