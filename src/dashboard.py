import os
import sys

# Workaround for Milvus Lite Windows bug: os.rename fails if target exists
if os.name == "nt":
    os.rename = os.replace

# Add the project root to the Python path so imports like `src.*` work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="T1D Bot — Corpus Retrieval Dashboard",
    page_icon="🩸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium aesthetics
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background-color: #0f111a;
        color: #e6e8f0;
    }
    
    /* Header styling */
    .header-container {
        background: linear-gradient(135deg, #1e1e30 0%, #111122 100%);
        padding: 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        border: 1px solid #2e2e4a;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    .header-title {
        font-family: 'Outfit', 'Inter', sans-serif;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
        font-size: 2.5rem;
        letter-spacing: -0.5px;
    }
    .header-subtitle {
        color: #8f90a6;
        margin-top: 0.5rem;
        font-size: 1.1rem;
    }
    
    /* Card styling for search results */
    .result-card {
        background-color: #16162a;
        border: 1px solid #282846;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .result-card:hover {
        transform: translateY(-2px);
        border-color: #4a4ae2;
        box-shadow: 0 4px 20px rgba(74, 74, 226, 0.15);
    }
    
    /* Badge styling */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 6px;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-primary { background-color: #3b82f6; color: white; }
    .badge-secondary { background-color: #10b981; color: white; }
    .badge-accent { background-color: #8b5cf6; color: white; }
    .badge-warning { background-color: #f59e0b; color: #1f2937; }
    .badge-info { background-color: #06b6d4; color: white; }
    .badge-score { background-color: #ec4899; color: white; }
    
    /* Highlighted text */
    .source-info {
        font-size: 0.85rem;
        color: #a0aec0;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Metadata grid */
    .meta-grid {
        display: flex;
        flex-wrap: wrap;
        margin-top: 1rem;
        border-top: 1px solid #23233b;
        padding-top: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

# App Title & Header
st.markdown("""
<div class="header-container">
    <h1 class="header-title">🩸 T1D Bot Retrieval Explorer</h1>
    <p class="header-subtitle">Inspect, query, and verify the local Type 1 Diabetes corpus store (Milvus-lite + BGE-M3)</p>
</div>
""", unsafe_allow_html=True)

# Sidebar configuration
st.sidebar.markdown("### ⚙️ Database Configuration")

# Default to t1d_corpus.db if it exists locally, otherwise fall back to env
if os.path.exists("t1d_corpus.db"):
    default_db_path = "t1d_corpus.db"
else:
    default_db_path = os.getenv("MILVUS_HOST", "localhost")

db_path = st.sidebar.text_input("Milvus DB Path / URI", value=default_db_path)

# Set environment variable dynamically for the import
os.environ["MILVUS_HOST"] = db_path

# Import CorpusStore safely
@st.cache_resource
def get_corpus_store(collection_name):
    from src.corpus_store.store import CorpusStore
    return CorpusStore(collection_name=collection_name)

collection_name = os.getenv("MILVUS_COLLECTION", "t1d_corpus")

try:
    store = get_corpus_store(collection_name)
    st.sidebar.success("⚡ Connected to Local Corpus Store")
except Exception as e:
    st.sidebar.error(f"❌ Connection Failed: {e}")
    st.info("💡 Please make sure `t1d_corpus.db` is present in the workspace or specify the correct path in the sidebar.")
    st.stop()

# Filters in Sidebar
st.sidebar.markdown("### 🔍 Filters")

# Collection Filter
col_options = ["All", "clinical_guidelines", "patient_education", "faq"]
selected_col = st.sidebar.selectbox("Collection ID", col_options)

# Language Filter
lang_options = ["All", "english", "hindi"]
selected_lang = st.sidebar.selectbox("Language", lang_options)

# Content Type Filter
type_options = ["All", "guideline", "education", "faq"]
selected_type = st.sidebar.selectbox("Content Type", type_options)

# Feature Flags
st.sidebar.markdown("### 🏷️ Content Flags")
dosage_filter = st.sidebar.radio("Contains Dosage Information?", ["Any", "Yes", "No"])
rec_filter = st.sidebar.radio("Contains Recommendation?", ["Any", "Yes", "No"])

# Search Settings
st.sidebar.markdown("### 🎛️ Settings")
top_k = st.sidebar.slider("Number of Results (Top K)", min_value=1, max_value=20, value=5)

# Main Query Area
query = st.text_input("Enter search query (e.g., 'hypoglycemia treatment rule of 15', 'basal insulin dosing')", placeholder="Type here to search the corpus...")

if query:
    # Build filters dict
    filters = {}
    if selected_col != "All":
        filters["collection"] = selected_col
    if selected_lang != "All":
        filters["language"] = selected_lang
    if selected_type != "All":
        filters["content_type"] = selected_type
    
    if dosage_filter == "Yes":
        filters["contains_dosage"] = True
    elif dosage_filter == "No":
        filters["contains_dosage"] = False
        
    if rec_filter == "Yes":
        filters["contains_recommendation"] = True
    elif rec_filter == "No":
        filters["contains_recommendation"] = False

    st.markdown(f"### 🔎 Search Results for: *\"{query}\"*")
    
    with st.spinner("Embedding query and searching Milvus-lite..."):
        try:
            results = store.search(query=query, filters=filters, top_k=top_k)
            
            if not results:
                st.warning("No matching chunks found for this query and filter combination.")
            else:
                for idx, res in enumerate(results):
                    # Determine badges based on metadata
                    badge_html = f'<span class="badge badge-score">Score: {res.score:.4f}</span>'
                    badge_html += f'<span class="badge badge-primary">{res.collection}</span>'
                    badge_html += f'<span class="badge badge-secondary">{res.content_type}</span>'
                    badge_html += f'<span class="badge badge-info">{res.language}</span>'
                    
                    if res.topic:
                        badge_html += f'<span class="badge badge-accent">{res.topic}</span>'
                    
                    if res.contains_dosage:
                        badge_html += '<span class="badge badge-warning">💊 Dosage</span>'
                    if res.contains_recommendation:
                        badge_html += '<span class="badge badge-warning">📋 Rec</span>'

                    # Clean section title and text (applying decoding fallback if scrambled)
                    from src.ingestion.hindi_decoder import is_scrambled_hindi, decode_hindi_text
                    
                    section = res.section_title if res.section_title else "General Content"
                    if is_scrambled_hindi(section):
                        section = decode_hindi_text(section)
                        
                    display_text = res.text
                    if is_scrambled_hindi(display_text):
                        display_text = decode_hindi_text(display_text)
                    
                    st.markdown(f"""
                    <div class="result-card">
                        <div class="source-info">
                            <strong>📄 {res.source_document}</strong> 
                            • <span>Page {res.start_page}</span> 
                            • <span>Section: <em>{section}</em></span>
                        </div>
                        <div style="font-size: 1.05rem; line-height: 1.6; margin-bottom: 1rem;">
                            {display_text}
                        </div>
                        <div class="meta-grid">
                            {badge_html}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
        except Exception as e:
            st.error(f"Search failed: {e}")
            st.info("Make sure the embedding model BAAI/bge-m3 is downloaded or you have internet access to fetch it.")
else:
    # Empty State Dashboard Info
    st.info("👈 Use the sidebar to configure filters, then type a query above to explore the database.")
    
    # Show some statistics/metadata if possible
    st.markdown("### 📊 Database Overview")
    try:
        # Check collection info
        if store.client.has_collection(collection_name):
            col_info = store.client.describe_collection(collection_name)
            num_entities = store.client.get_collection_num_entities(collection_name)
            
            st.markdown(f"""
            - **Collection Name:** `{collection_name}`
            - **Total Chunks Ingested:** `{num_entities}`
            - **Vector Dimensions (Dense):** `1024` (BGE-M3)
            - **Index Type:** `HNSW` (Dense), `SPARSE_INVERTED_INDEX` (Sparse)
            """)
            
            # Show a sample of recent documents
            st.markdown("#### 📄 Ingested Documents")
            # Query some sample entities
            samples = store.client.query(
                collection_name=collection_name,
                filter="",
                limit=10,
                output_fields=["source_document", "collection", "language"]
            )
            if samples:
                df = pd.DataFrame(samples)
                if "source_document" in df.columns:
                    unique_docs = df["source_document"].unique()
                    for doc in unique_docs:
                        st.markdown(f"- {doc}")
            else:
                st.write("No documents found in the collection yet.")
        else:
            st.warning(f"Collection '{collection_name}' does not exist yet.")
    except Exception as e:
        st.write("Could not retrieve collection statistics.")
