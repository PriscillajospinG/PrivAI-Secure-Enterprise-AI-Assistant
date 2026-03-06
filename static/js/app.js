document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadStatus = document.getElementById('uploadStatus');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatMessages = document.getElementById('chatMessages');
    const typingIndicator = document.getElementById('typingIndicator');
    const approvalModal = document.getElementById('approvalModal');
    const reviewContent = document.getElementById('reviewContent');
    const approveBtn = document.getElementById('approveBtn');
    const rejectBtn = document.getElementById('rejectBtn');

    let currentPendingResponse = null;

    // Handle File Upload
    uploadBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', async (e) => {
        const files = e.target.files;
        if (files.length === 0) return;

        uploadStatus.textContent = 'Uploading and indexing...';
        uploadStatus.className = 'status-msg';

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                uploadStatus.textContent = `Success: ${result.file_count} files indexed.`;
                uploadStatus.classList.add('success');
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            uploadStatus.textContent = 'Error: ' + error.message;
            uploadStatus.classList.add('error');
        }
    });

    // Handle Chat
    const addMessage = (content, sender) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`;
        msgDiv.innerHTML = `<div class="message-content">${content}</div>`;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    const handleQuery = async () => {
        const query = userInput.value.trim();
        if (!query) return;

        addMessage(query, 'user');
        userInput.value = '';
        typingIndicator.classList.remove('hidden');

        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });

            if (response.ok) {
                const result = await response.json();
                currentPendingResponse = result;
                
                // Show human approval modal
                reviewContent.textContent = result.response;
                approvalModal.classList.remove('hidden');
            } else {
                throw new Error('Failed to get response');
            }
        } catch (error) {
            addMessage('Error: ' + error.message, 'assistant');
        } finally {
            typingIndicator.classList.add('hidden');
        }
    };

    sendBtn.addEventListener('click', handleQuery);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleQuery();
        }
    });

    // Human Approval Modal
    approveBtn.addEventListener('click', () => {
        if (currentPendingResponse) {
            addMessage(currentPendingResponse.response, 'assistant');
            approvalModal.classList.add('hidden');
            currentPendingResponse = null;
        }
    });

    rejectBtn.addEventListener('click', () => {
        approvalModal.classList.add('hidden');
        addMessage('Response rejected by user. Please try rephrasing your query.', 'assistant');
        currentPendingResponse = null;
    });

    // Auto-resize textarea
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
});
