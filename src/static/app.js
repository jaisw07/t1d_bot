/**
 * T1D RAGbot - Static SPA Frontend Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const statusIndicator = document.getElementById('status-indicator');
    const statusLabel = document.getElementById('status-label');
    
    const ragToggle = document.getElementById('rag-toggle');
    const topKSlider = document.getElementById('top-k-slider');
    const topKVal = document.getElementById('top-k-val');
    
    const filterLanguage = document.getElementById('filter-language');
    const resetControlsBtn = document.getElementById('reset-controls-btn');
    
    const searchForm = document.getElementById('search-form');
    const queryInput = document.getElementById('query-input');
    const clearQueryBtn = document.getElementById('clear-query-btn');
    const searchBtn = document.getElementById('search-btn');
    
    const loadingSpinner = document.getElementById('loading-spinner');
    const loadingText = document.getElementById('loading-text');
    
    const ragResponseSection = document.getElementById('rag-response-section');
    const ragLangTag = document.getElementById('rag-lang-tag');
    const ragAnswerContent = document.getElementById('rag-answer-content');
    const ragCitationsContent = document.getElementById('rag-citations-content');
    
    const resultsSection = document.getElementById('results-section');
    const resultsCountTitle = document.getElementById('results-count-title');
    const chunksContainer = document.getElementById('chunks-container');

    // Sync Slider Value
    topKSlider.addEventListener('input', (e) => {
        topKVal.textContent = e.target.value;
    });

    // Clear Query
    clearQueryBtn.addEventListener('click', () => {
        queryInput.value = '';
        queryInput.focus();
        resetResultsView();
    });

    // Reset Controls
    resetControlsBtn.addEventListener('click', () => {
        filterLanguage.value = 'All';
        topKSlider.value = 5;
        topKVal.textContent = '5';
        ragToggle.checked = true;
    });

    // Check System Health Status
    async function initSystem() {
        try {
            const healthResp = await fetch('/health');
            if (healthResp.ok) {
                const healthData = await healthResp.json();
                statusIndicator.className = 'status-indicator ready';
                statusLabel.textContent = `Connected (${healthData.collection || 't1d_corpus'})`;
            } else {
                throw new Error('Health check non-200');
            }
        } catch (err) {
            statusIndicator.className = 'status-indicator error';
            statusLabel.textContent = 'Service Offline / Error';
        }
    }

    // Helper: Reset Results View
    function resetResultsView() {
        ragResponseSection.classList.add('hidden');
        resultsSection.classList.add('hidden');
        loadingSpinner.classList.add('hidden');
    }

    // Lightweight Markdown Renderer (Bold, Italics, Headings, Lists, Paragraphs)
    function renderMarkdown(text) {
        if (!text) return '';

        // 1. Escape unsafe HTML
        let escaped = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");

        // 2. Format Headings
        escaped = escaped.replace(/^### (.*$)/gim, '<h4 class="md-heading">$1</h4>');
        escaped = escaped.replace(/^## (.*$)/gim, '<h3 class="md-heading">$1</h3>');
        escaped = escaped.replace(/^# (.*$)/gim, '<h2 class="md-heading">$1</h2>');

        // 3. Format Bold (**text**)
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // 4. Format Italics (*text* or _text_)
        escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');
        escaped = escaped.replace(/_(.*?)_/g, '<em>$1</em>');

        // 5. Line by line processing for Lists & Paragraphs
        const lines = escaped.split(/\r?\n/);
        const result = [];
        let inList = false;

        for (let line of lines) {
            const trimmed = line.trim();

            if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                if (!inList) {
                    inList = true;
                    result.push('<ul class="md-list">');
                }
                result.push(`<li>${trimmed.substring(2)}</li>`);
            } else {
                if (inList) {
                    inList = false;
                    result.push('</ul>');
                }
                if (trimmed.length > 0) {
                    if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || trimmed.startsWith('</ul')) {
                        result.push(trimmed);
                    } else {
                        result.push(`<p class="md-paragraph">${trimmed}</p>`);
                    }
                }
            }
        }

        if (inList) {
            result.push('</ul>');
        }

        return result.join('');
    }

    // Handle Form Submit
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (!query) return;

        // Collect Filter Values
        const selectedLang = filterLanguage.value !== 'All' ? filterLanguage.value : null;
        const topK = parseInt(topKSlider.value, 10);
        const isRagEnabled = ragToggle.checked;

        const payload = {
            query: query,
            language: selectedLang ? selectedLang.toLowerCase() : 'english',
            top_k: topK,
            language_filter: selectedLang
        };

        // UI State: Loading (only activated when query is submitted)
        ragResponseSection.classList.add('hidden');
        resultsSection.classList.add('hidden');
        loadingSpinner.classList.remove('hidden');
        searchBtn.disabled = true;
        
        if (isRagEnabled) {
            loadingText.textContent = 'Thinking...';
        } else {
            loadingText.textContent = 'Searching database...';
        }

        try {
            const endpoint = isRagEnabled ? '/query' : '/search';
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || `Server returned status ${response.status}`);
            }

            const data = await response.json();
            renderSearchResults(data, isRagEnabled);

        } catch (err) {
            alert(`Search Failed: ${err.message}`);
            resetResultsView();
        } finally {
            loadingSpinner.classList.add('hidden');
            searchBtn.disabled = false;
        }
    });

    // Render Search & RAG Results
    function renderSearchResults(data, isRagEnabled) {
        // 1. Render RAG Clinical Answer if available
        if (isRagEnabled && data.answer) {
            ragLangTag.textContent = (data.language || 'English').toUpperCase();
            ragAnswerContent.innerHTML = renderMarkdown(data.answer);
            
            if (data.citations && data.citations.length > 0) {
                ragCitationsContent.textContent = data.citations.join(' | ');
            } else {
                ragCitationsContent.textContent = 'None';
            }
            ragResponseSection.classList.remove('hidden');
        }

        // 2. Render Retrieved Chunks
        const chunks = data.retrieved_chunks || [];
        chunksContainer.innerHTML = '';

        if (chunks.length > 0) {
            resultsCountTitle.textContent = `Retrieved Context Chunks (${chunks.length})`;
            
            chunks.forEach((chunk) => {
                const card = document.createElement('div');
                card.className = 'chunk-card';

                const score = chunk.score ? chunk.score.toFixed(4) : '0.0000';
                const sourceDoc = chunk.source_document || 'Unknown Document';
                const page = chunk.start_page !== undefined ? chunk.start_page : 0;
                const section = chunk.section_title || 'General Content';
                const text = chunk.text || '';

                let badgesHtml = `
                    <span class="badge badge-score">Score: ${score}</span>
                    <span class="badge badge-col">${chunk.collection || 'corpus'}</span>
                    <span class="badge badge-type">${chunk.content_type || 'general'}</span>
                    <span class="badge badge-lang">${chunk.language || 'english'}</span>
                `;

                if (chunk.topic) {
                    badgesHtml += `<span class="badge badge-flag">${chunk.topic}</span>`;
                }
                if (chunk.contains_dosage) {
                    badgesHtml += `<span class="badge badge-flag">Dosage</span>`;
                }
                if (chunk.contains_recommendation) {
                    badgesHtml += `<span class="badge badge-flag">Recommendation</span>`;
                }

                card.innerHTML = `
                    <div class="chunk-meta-header">
                        <span class="chunk-doc-title">${escapeHtml(sourceDoc)}</span>
                        <span>&bull;</span>
                        <span>Page ${page}</span>
                        <span>&bull;</span>
                        <span>Section: <em>${escapeHtml(section)}</em></span>
                    </div>
                    <div class="chunk-body">${escapeHtml(text)}</div>
                    <div class="badge-list">${badgesHtml}</div>
                `;
                chunksContainer.appendChild(card);
            });

            resultsSection.classList.remove('hidden');
        } else if (!isRagEnabled || !data.answer) {
            resultsCountTitle.textContent = 'Retrieved Context Chunks (0)';
            chunksContainer.innerHTML = '<p class="loading-text">No matching chunks found for the specified query and filters.</p>';
            resultsSection.classList.remove('hidden');
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Initialize System
    initSystem();
});
