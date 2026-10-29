// --- DOM Elements ---
const textInput = document.getElementById('text-input');
const fileInput = document.getElementById('file-input');
const fileNameDisplay = document.getElementById('file-name');
const generateBtn = document.getElementById('generate-btn');
const errorBanner = document.getElementById('error-banner');

const progressSection = document.getElementById('progress-section');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');

const outputSection = document.getElementById('output-section');
const flashcardGrid = document.getElementById('flashcard-grid');
const warningsContainer = document.getElementById('warnings-container');
const exportCsvBtn = document.getElementById('export-csv-btn');
const exportAnkiBtn = document.getElementById('export-anki-btn');

// --- State ---
let currentCards = [];
let pollingInterval = null;

// --- File Upload Logic ---
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    fileNameDisplay.textContent = file.name;
    
    // Create form data to send to backend
    const formData = new FormData();
    formData.append('file', file);

    try {
        showError(null); // Clear previous errors
        textInput.value = "Extracting text...";
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail?.detail || data.detail || "Failed to upload file");
        }

        textInput.value = data.text;
    } catch (err) {
        textInput.value = "";
        showError(err.message);
        fileNameDisplay.textContent = "No file selected";
    }
});

// --- Generate Logic ---
generateBtn.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) {
        showError("Please paste some text or upload a file first.");
        return;
    }

    // Reset UI
    showError(null);
    outputSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    generateBtn.disabled = true;
    progressBar.style.width = '0%';
    progressText.textContent = "Starting job...";

    try {
        // 1. Send text to backend
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail?.detail || data.detail || "Generation failed");
        }

        // 2. Start Polling
        pollJobStatus(data.job_id);

    } catch (err) {
        generateBtn.disabled = false;
        progressSection.classList.add('hidden');
        showError(err.message);
    }
});

// --- Polling Logic ---
function pollJobStatus(jobId) {
    pollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/jobs/${jobId}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail?.detail || data.detail || "Error checking job status");
            }

            if (data.status === "done") {
                // Finished!
                clearInterval(pollingInterval);
                progressSection.classList.add('hidden');
                generateBtn.disabled = false;
                
                currentCards = data.cards;
                renderCards(data.cards, data.warnings);
                
            } else {
                // Still processing
                const percent = data.total > 0 ? (data.done / data.total) * 100 : 0;
                progressBar.style.width = `${percent}%`;
                progressText.textContent = `Processing chunk ${data.done} of ${data.total}...`;
            }
        } catch (err) {
            clearInterval(pollingInterval);
            generateBtn.disabled = false;
            progressSection.classList.add('hidden');
            showError(err.message);
        }
    }, 1000); // Check every 1 second
}

// --- Render Cards ---
function renderCards(cards, warnings) {
    flashcardGrid.innerHTML = "";
    
    // Warnings
    if (warnings && warnings.length > 0) {
        warningsContainer.classList.remove('hidden');
        warningsContainer.innerHTML = `<strong>Notes:</strong><br>` + warnings.join('<br>');
    } else {
        warningsContainer.classList.add('hidden');
    }

    if (cards.length === 0) {
        flashcardGrid.innerHTML = "<p>No cards could be generated from this text.</p>";
        outputSection.classList.remove('hidden');
        return;
    }

    // Cards
    cards.forEach(card => {
        const cardEl = document.createElement('div');
        cardEl.className = 'flashcard';
        cardEl.innerHTML = `
            <div>
                <div class="flashcard-question">${card.question}</div>
                <div class="flashcard-answer">${card.answer}</div>
            </div>
            <div class="card-actions">
                <span style="color: #64748b; font-size: 0.8rem;">Click to flip</span>
                <button class="regenerate-btn" data-id="${card.id}" data-chunk="${card.chunk_index}" data-question="${card.question}">↻ Regenerate</button>
            </div>
        `;

        // Flip logic
        cardEl.addEventListener('click', (e) => {
            // Don't flip if they clicked the regenerate button
            if (e.target.classList.contains('regenerate-btn')) return;
            cardEl.classList.toggle('flipped');
        });

        flashcardGrid.appendChild(cardEl);
    });

    // Attach regenerate events
    document.querySelectorAll('.regenerate-btn').forEach(btn => {
        btn.addEventListener('click', handleRegenerate);
    });

    outputSection.classList.remove('hidden');
}

// --- Regenerate Logic ---
async function handleRegenerate(e) {
    const btn = e.target;
    const chunkIndex = parseInt(btn.dataset.chunk);
    const question = btn.dataset.question;
    const cardEl = btn.closest('.flashcard');

    const originalText = btn.textContent;
    btn.textContent = "Generating...";
    btn.disabled = true;

    try {
        const response = await fetch('/api/regenerate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chunk_index: chunkIndex, question: question })
        });
        const data = await response.json();

        if (!response.ok) throw new Error(data.detail?.detail || "Failed to regenerate");

        // Update the DOM with the new card
        cardEl.querySelector('.flashcard-question').textContent = data.card.question;
        cardEl.querySelector('.flashcard-answer').textContent = data.card.answer;
        cardEl.classList.remove('flipped');

    } catch (err) {
        alert(err.message); // Simple alert for regen failure
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// --- Export Logic ---
async function handleExport(endpoint, filename) {
    if (currentCards.length === 0) return;

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentCards)
        });
        
        if (!response.ok) throw new Error("Export failed");

        // Create a blob and download it
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

    } catch (err) {
        showError(err.message);
    }
}

exportCsvBtn.addEventListener('click', () => handleExport('/api/export/csv', 'flashcards.csv'));
exportAnkiBtn.addEventListener('click', () => handleExport('/api/export/anki', 'flashcards.apkg'));

// --- Helpers ---
function showError(message) {
    if (!message) {
        errorBanner.classList.add('hidden');
        return;
    }
    errorBanner.textContent = message;
    errorBanner.classList.remove('hidden');
}