/**
 * RAG Threads - Main JavaScript
 */

// ========================================
// Global State
// ========================================
const state = {
    currentThread: null,
    currentDocument: null,
    threads: [],
    documents: []
};

// ========================================
// Utility Functions
// ========================================
function showError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.classList.add('show');
    }
}

function hideError(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.classList.remove('show');
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ========================================
// Auth Page Functions
// ========================================
function initAuthPage() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');

    if (!tabBtns.length) return;

    // Tab switching
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;

            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            if (tab === 'login') {
                loginForm.classList.add('active');
                signupForm.classList.remove('active');
            } else {
                loginForm.classList.remove('active');
                signupForm.classList.add('active');
            }
        });
    });

    // Login form submission
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideError('loginError');

            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;

            try {
                const response = await fetch('/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                const data = await response.json();

                if (response.ok) {
                    window.location.href = '/chat';
                } else {
                    showError('loginError', data.error || 'Login failed');
                }
            } catch (err) {
                showError('loginError', 'Connection error. Please try again.');
            }
        });
    }

    // Signup form submission
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            hideError('signupError');

            const email = document.getElementById('signupEmail').value;
            const password = document.getElementById('signupPassword').value;
            const confirm = document.getElementById('signupConfirm').value;

            if (password !== confirm) {
                showError('signupError', 'Passwords do not match');
                return;
            }

            try {
                const response = await fetch('/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                const data = await response.json();

                if (response.ok) {
                    window.location.href = '/chat';
                } else {
                    showError('signupError', data.error || 'Registration failed');
                }
            } catch (err) {
                showError('signupError', 'Connection error. Please try again.');
            }
        });
    }

    // Image carousel
    initCarousel();
}

function initCarousel() {
    const images = document.querySelectorAll('.carousel-image');
    if (images.length < 2) return;

    let current = 0;
    setInterval(() => {
        images[current].classList.remove('active');
        current = (current + 1) % images.length;
        images[current].classList.add('active');
    }, 4000);
}

// ========================================
// Chat Page Functions
// ========================================
function initChatPage() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const profileBtn = document.getElementById('profileBtn');
    const dropdownMenu = document.getElementById('dropdownMenu');
    const logoutBtn = document.getElementById('logoutBtn');
    const uploadBtn = document.getElementById('uploadBtn');
    const welcomeUploadBtn = document.getElementById('welcomeUploadBtn');
    const newChatBtn = document.getElementById('newChatBtn');
    const chatForm = document.getElementById('chatForm');
    const metricsCloseBtn = document.getElementById('metricsCloseBtn');

    if (!sidebar) return;

    // Sidebar toggle (mobile)
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // Profile dropdown
    if (profileBtn) {
        profileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.toggle('show');
        });

        document.addEventListener('click', () => {
            dropdownMenu.classList.remove('show');
        });
    }

    // Logout
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            await fetch('/auth/logout', { method: 'POST' });
            window.location.href = '/login';
        });
    }

    // Upload buttons
    if (uploadBtn) {
        uploadBtn.addEventListener('click', () => openUploadModal());
    }
    if (welcomeUploadBtn) {
        welcomeUploadBtn.addEventListener('click', () => openUploadModal());
    }

    // New chat button
    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => openNewChatModal());
    }

    // Chat form
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            sendMessage();
        });
    }

    if (metricsCloseBtn) {
        metricsCloseBtn.addEventListener('click', () => {
            const panel = document.getElementById('metricsPanel');
            if (panel) panel.hidden = true;
        });
    }

    // Message input auto-resize
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });

        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // Initialize modals
    initUploadModal();
    initNewChatModal();

    // Load initial data
    loadDocuments();
    loadThreads();
}

// Upload Modal
function initUploadModal() {
    const modal = document.getElementById('uploadModal');
    const closeBtn = document.getElementById('closeUploadModal');
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    if (!modal) return;

    closeBtn.addEventListener('click', () => closeModal('uploadModal'));
    modal.querySelector('.modal-overlay').addEventListener('click', () => closeModal('uploadModal'));

    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');

        const file = e.dataTransfer.files[0];
        if (file && file.type === 'application/pdf') {
            const scopeSelect = document.getElementById('scopeSelect');
            const scope = scopeSelect ? scopeSelect.value : 'USER_PRIVATE';
            uploadFile(file, scope);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files[0]) {
            const scopeSelect = document.getElementById('scopeSelect');
            const scope = scopeSelect ? scopeSelect.value : 'USER_PRIVATE';
            uploadFile(fileInput.files[0], scope);
        }
    });
}

function openUploadModal() {
    document.getElementById('uploadModal').classList.add('show');
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('uploadProgress').style.display = 'none';
}

async function uploadFile(file, scope = 'USER_PRIVATE') {
    const uploadArea = document.getElementById('uploadArea');
    const progressDiv = document.getElementById('uploadProgress');
    const filename = document.getElementById('uploadFilename');
    const status = document.getElementById('uploadStatus');
    const progressBar = document.getElementById('progressBar');

    uploadArea.style.display = 'none';
    progressDiv.style.display = 'block';
    filename.textContent = file.name;
    status.textContent = 'Getting upload URL...';
    status.style.color = '';  // Reset color
    progressBar.style.width = '10%';

    try {
        // Get presigned URL
        const presignResponse = await fetch('/api/uploads/presign', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: file.name,
                content_type: 'application/pdf',
                size_bytes: file.size
            })
        });

        if (!presignResponse.ok) {
            const err = await presignResponse.json();
            throw new Error(err.error || 'Failed to get upload URL');
        }

        const presignData = await presignResponse.json();
        progressBar.style.width = '30%';
        status.textContent = 'Uploading to storage...';

        // Upload to B2
        const uploadResponse = await fetch(presignData.upload_url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/pdf',
                'Content-Length': file.size.toString()
            },
            body: file
        });

        if (!uploadResponse.ok) {
            // Try to get more details about the error
            let errorDetail = `Status: ${uploadResponse.status}`;
            try {
                const errorText = await uploadResponse.text();
                if (errorText) {
                    errorDetail += ` - ${errorText}`;
                }
            } catch (e) {
                // Ignore error reading response
            }
            throw new Error(`Upload to storage failed (${errorDetail})`);
        }

        progressBar.style.width = '70%';
        status.textContent = 'Confirming upload...';

        // Confirm upload - use object_key from presign response
        const confirmResponse = await fetch('/api/documents/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                object_key: presignData.object_key,
                title: file.name.replace('.pdf', ''),
                size_bytes: file.size,
                scope: scope
            })
        });

        if (!confirmResponse.ok) {
            const err = await confirmResponse.json();
            throw new Error(err.error || 'Confirmation failed');
        }

        const confirmData = await confirmResponse.json();

        progressBar.style.width = '100%';
        status.textContent = 'Processing document...';

        // Create a new thread immediately so the user can chat
        if (confirmData?.document_id) {
            try {
                const threadResponse = await fetch('/api/threads', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        document_id: confirmData.document_id,
                        title: `New Chat - ${file.name.replace('.pdf', '')}`
                    })
                });

                if (threadResponse.ok) {
                    const thread = await threadResponse.json();
                    await loadDocuments();
                    await loadThreads();
                    selectThread(thread);
                } else {
                    await loadDocuments();
                    await loadThreads();
                }
            } catch (err) {
                await loadDocuments();
                await loadThreads();
            }
        } else {
            await loadDocuments();
            await loadThreads();
        }

        // Close modal after delay
        setTimeout(() => {
            closeModal('uploadModal');
        }, 1000);

    } catch (err) {
        status.textContent = 'Error: ' + err.message;
        status.style.color = 'var(--danger)';
    }
}

// New Chat Modal
function initNewChatModal() {
    const modal = document.getElementById('newChatModal');
    const closeBtn = document.getElementById('closeNewChatModal');

    if (!modal) return;

    closeBtn.addEventListener('click', () => closeModal('newChatModal'));
    modal.querySelector('.modal-overlay').addEventListener('click', () => closeModal('newChatModal'));
}

function openNewChatModal() {
    const modal = document.getElementById('newChatModal');
    const docList = document.getElementById('documentList');

    // Populate document list
    docList.innerHTML = state.documents.length ? '' : '<p class="empty-state">No documents available</p>';

    state.documents.forEach(doc => {
        if (doc.ingestion_status !== 'DONE') return;

        const item = document.createElement('div');
        item.className = 'document-item';
        item.innerHTML = `
            <div class="doc-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
            </div>
            <div class="doc-info">
                <div class="doc-title">${doc.title}</div>
                <div class="doc-meta">${formatSize(doc.size_bytes)} • ${formatDate(doc.created_at)}</div>
            </div>
        `;
        item.addEventListener('click', () => createNewThread(doc));
        docList.appendChild(item);
    });

    modal.classList.add('show');
}

async function createNewThread(doc) {
    try {
        const response = await fetch('/api/threads', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                document_id: doc.id,
                title: 'New Chat - ' + doc.title
            })
        });

        if (response.ok) {
            const thread = await response.json();
            closeModal('newChatModal');
            loadThreads();
            selectThread(thread);
        }
    } catch (err) {
        console.error('Failed to create thread:', err);
    }
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

// Data Loading
async function loadDocuments() {
    try {
        const response = await fetch('/api/documents');
        if (response.ok) {
            const data = await response.json();
            state.documents = data.documents || [];
        }
    } catch (err) {
        console.error('Failed to load documents:', err);
    }
}

async function loadThreads() {
    try {
        const response = await fetch('/api/threads');
        if (response.ok) {
            const data = await response.json();
            state.threads = data.threads || [];
            renderThreadList();
        }
    } catch (err) {
        console.error('Failed to load threads:', err);
    }
}

function renderThreadList() {
    const threadList = document.getElementById('threadList');
    if (!threadList) return;

    if (state.threads.length === 0) {
        threadList.innerHTML = `
            <div class="empty-state">
                <p>No conversations yet</p>
                <p class="hint">Upload a document to start</p>
            </div>
        `;
        return;
    }

    threadList.innerHTML = '';

    // Group by document
    const grouped = {};
    state.threads.forEach(thread => {
        const docId = thread.document_id;
        if (!grouped[docId]) {
            grouped[docId] = { doc: thread.document_title, threads: [] };
        }
        grouped[docId].threads.push(thread);
    });

    Object.values(grouped).forEach(group => {
        const docHeader = document.createElement('div');
        docHeader.className = 'thread-doc-header';
        docHeader.textContent = group.doc;
        docHeader.style.cssText = 'font-size: 0.75rem; color: var(--text-muted); padding: 0.5rem; text-transform: uppercase;';
        threadList.appendChild(docHeader);

        group.threads.forEach(thread => {
            const item = document.createElement('div');
            item.className = 'thread-item' + (state.currentThread?.id === thread.id ? ' active' : '');
            item.innerHTML = `
                <span class="thread-title">${thread.title || 'Untitled'}</span>
                <span class="thread-doc">${formatDate(thread.created_at)}</span>
            `;
            item.addEventListener('click', () => selectThread(thread));
            threadList.appendChild(item);
        });
    });
}

async function selectThread(thread) {
    state.currentThread = thread;
    state.currentDocument = state.documents.find(d => d.id === thread.document_id);

    // Update UI
    document.getElementById('chatTitle').textContent = thread.title || 'Chat';
    document.getElementById('messageInput').disabled = false;
    document.getElementById('sendBtn').disabled = false;

    // Remove welcome message
    const welcome = document.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    renderThreadList();

    // Load messages
    await loadMessages(thread.id);
}

async function loadMessages(threadId) {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

    try {
        const response = await fetch(`/api/threads/${threadId}`);
        if (response.ok) {
            const data = await response.json();
            renderMessages(data.messages || []);
            updateMetricsPanel(null);
        }
    } catch (err) {
        console.error('Failed to load messages:', err);
    }
}

function updateMetricsPanel(metrics) {
    const panel = document.getElementById('metricsPanel');
    if (!panel) return;

    if (!metrics) {
        panel.hidden = true;
        return;
    }

    const textChunks = document.getElementById('metricTextChunks');
    const images = document.getElementById('metricImages');
    const faithfulness = document.getElementById('metricFaithfulness');
    const citationPrecision = document.getElementById('metricCitationPrecision');
    const groundedness = document.getElementById('metricGroundedness');

    if (textChunks) {
        textChunks.textContent = metrics.retrieved_text_chunks ?? 0;
    }
    if (images) {
        images.textContent = metrics.retrieved_images ?? 0;
    }
    if (faithfulness) {
        const value = metrics.faithfulness_score ?? 0;
        faithfulness.textContent = Math.round(value * 100);
    }
    if (citationPrecision) {
        const value = metrics.citation_precision_score ?? 0;
        citationPrecision.textContent = Math.round(value * 100);
    }
    if (groundedness) {
        const value = metrics.groundedness_score ?? 0;
        groundedness.textContent = Math.round(value * 100);
    }

    panel.hidden = false;
}

function renderMessages(messages) {
    const chatMessages = document.getElementById('chatMessages');

    if (messages.length === 0) {
        chatMessages.innerHTML = `
            <div class="welcome-message">
                <h2>Start a conversation</h2>
                <p>Ask questions about your document</p>
            </div>
        `;
        return;
    }

    chatMessages.innerHTML = '';

    messages.forEach(msg => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${msg.role}`;

        const avatar = msg.role === 'user' ? 'U' : 'AI';

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">${formatMessageContent(msg.content)}</div>
        `;

        chatMessages.appendChild(messageDiv);
    });

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatMessageContent(content) {
    // Simple markdown-like formatting
    return content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>')
        .replace(/`(.*?)`/g, '<code>$1</code>');
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();

    if (!message || !state.currentThread) return;

    input.value = '';
    input.style.height = 'auto';

    // Add user message to UI
    const chatMessages = document.getElementById('chatMessages');
    const userMsg = document.createElement('div');
    userMsg.className = 'message message-user';
    userMsg.innerHTML = `
        <div class="message-avatar">U</div>
        <div class="message-content">${formatMessageContent(message)}</div>
    `;
    chatMessages.appendChild(userMsg);

    // Add typing indicator
    const typing = document.createElement('div');
    typing.className = 'message message-assistant';
    typing.innerHTML = `
        <div class="message-avatar">AI</div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(typing);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`/api/threads/${state.currentThread.id}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, stream: true })
        });

        if (!response.ok) {
            typing.querySelector('.message-content').innerHTML = 'Error getting response';
            return;
        }

        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('text/event-stream')) {
            const data = await response.json();
            typing.remove();

            const assistantMsg = document.createElement('div');
            assistantMsg.className = 'message message-assistant';
            assistantMsg.innerHTML = `
                <div class="message-avatar">AI</div>
                <div class="message-content">${formatMessageContent(data.response)}</div>
            `;
            chatMessages.appendChild(assistantMsg);
            chatMessages.scrollTop = chatMessages.scrollHeight;
            updateMetricsPanel(data.metrics || null);
            return;
        }

        typing.remove();
        const assistantMsg = document.createElement('div');
        assistantMsg.className = 'message message-assistant';
        assistantMsg.innerHTML = `
            <div class="message-avatar">AI</div>
            <div class="message-content"></div>
        `;
        const assistantContent = assistantMsg.querySelector('.message-content');
        chatMessages.appendChild(assistantMsg);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            const parts = buffer.split('\n\n');
            buffer = parts.pop() || '';

            for (const part of parts) {
                const line = part.split('\n').find(l => l.startsWith('data: '));
                if (!line) continue;
                const payload = line.replace('data: ', '').trim();
                if (!payload) continue;

                const event = JSON.parse(payload);
                if (event.type === 'chunk') {
                    assistantContent.textContent += event.content;
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
                if (event.type === 'context') {
                    updateMetricsPanel({
                        retrieved_text_chunks: (event.context?.text_chunks || []).length,
                        retrieved_images: (event.context?.images || []).length
                    });
                }
                if (event.type === 'metrics') {
                    updateMetricsPanel(event.metrics || null);
                }
                if (event.type === 'error') {
                    assistantContent.textContent = event.error || 'Error streaming response';
                }
            }
        }
    } catch (err) {
        typing.querySelector('.message-content').innerHTML = 'Error: ' + err.message;
    }
}

// ========================================
// Admin Page Functions
// ========================================
function initAdminPage() {
    const tabs = document.querySelectorAll('.admin-tab');

    if (!tabs.length) return;

    // Tab switching
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;

            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            document.getElementById(tabName + 'Panel').classList.add('active');

            if (tabName === 'users') loadUsers();
            if (tabName === 'documents') loadAdminDocuments();
            if (tabName === 'activity') loadActivityLog();
        });
    });

    // Refresh buttons
    document.getElementById('refreshUsers')?.addEventListener('click', loadUsers);
    document.getElementById('refreshDocs')?.addEventListener('click', loadAdminDocuments);
    document.getElementById('refreshActivity')?.addEventListener('click', loadActivityLog);

    // Confirmation modal
    initConfirmModal();

    // Load initial data
    loadUsers();
}

function initConfirmModal() {
    const modal = document.getElementById('confirmModal');
    if (!modal) return;

    document.getElementById('confirmCancel').addEventListener('click', () => {
        modal.classList.remove('show');
    });

    modal.querySelector('.modal-overlay').addEventListener('click', () => {
        modal.classList.remove('show');
    });
}

function showConfirm(title, message, onConfirm) {
    const modal = document.getElementById('confirmModal');
    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmMessage').textContent = message;

    const confirmBtn = document.getElementById('confirmAction');
    confirmBtn.textContent = title || 'Confirm';
    confirmBtn.onclick = () => {
        modal.classList.remove('show');
        onConfirm();
    };

    modal.classList.add('show');
}

async function loadUsers() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="6" class="loading"><div class="spinner"></div></td></tr>';

    try {
        const response = await fetch('/api/admin/users');
        if (response.ok) {
            const data = await response.json();
            renderUsersTable(data.users || []);
        }
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="6">Error loading users</td></tr>';
    }
}

function renderUsersTable(users) {
    const tbody = document.getElementById('usersTableBody');

    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No users found</td></tr>';
        return;
    }

    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.email}</td>
            <td>${user.role}</td>
            <td>${formatDate(user.created_at)}</td>
            <td>${user.docs_count}</td>
            <td>${user.threads_count}</td>
            <td>
                ${user.role === 'admin'
                    ? '<span class="text-muted">Protected</span>'
                    : `<button class="action-btn delete" onclick="deleteUser('${user.id}', '${user.email}')">
                        Delete
                    </button>`}
            </td>
        </tr>
    `).join('');
}

async function deleteUser(userId, email) {
    showConfirm(
        'Delete User',
        `Are you sure you want to delete ${email}? This will also delete all their documents, threads, and messages.`,
        async () => {
            try {
                const response = await fetch(`/api/admin/users/${userId}`, {
                    method: 'DELETE'
                });
                if (response.ok) {
                    loadUsers();
                } else {
                    const err = await response.json();
                    alert(err.error || 'Delete failed');
                }
            } catch (err) {
                alert('Error deleting user');
            }
        }
    );
}

async function loadAdminDocuments() {
    const tbody = document.getElementById('docsTableBody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="7" class="loading"><div class="spinner"></div></td></tr>';

    try {
        const response = await fetch('/api/admin/documents');
        if (response.ok) {
            const data = await response.json();
            renderDocsTable(data.documents || []);
        }
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="7">Error loading documents</td></tr>';
    }
}

function renderDocsTable(docs) {
    const tbody = document.getElementById('docsTableBody');

    if (docs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7">No documents found</td></tr>';
        return;
    }

    tbody.innerHTML = docs.map(doc => {
        const scopeClass = doc.scope.toLowerCase().replace('_', '-');
        const statusClass = doc.ingestion_status.toLowerCase();

        return `
            <tr>
                <td>${doc.title}</td>
                <td>${doc.owner_email}</td>
                <td><span class="scope-badge ${scopeClass}">${doc.scope}</span></td>
                <td>${formatSize(doc.size_bytes)}</td>
                <td><span class="status-badge ${statusClass}">${doc.ingestion_status}</span></td>
                <td>${formatDate(doc.created_at)}</td>
                <td>
                    <button class="action-btn delete" onclick="deleteDocument('${doc.id}', '${doc.title}')">
                        Delete
                    </button>
                    <button class="action-btn" onclick="deleteChunks('${doc.id}', '${doc.title}')" style="background: var(--accent-muted); color: var(--accent-primary);">
                        Del Chunks
                    </button>
                    <button class="action-btn" onclick="recreateChunks('${doc.id}', '${doc.title}')" style="background: rgba(34,197,94,0.15); color: var(--success);">
                        Recreate Chunks
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

async function deleteDocument(docId, title) {
    showConfirm(
        'Delete Document',
        `Are you sure you want to delete "${title}"? This will also delete the file from storage and all embeddings.`,
        async () => {
            try {
                const response = await fetch(`/api/admin/documents/${docId}`, {
                    method: 'DELETE'
                });
                if (response.ok) {
                    loadAdminDocuments();
                } else {
                    const err = await response.json();
                    alert(err.error || 'Delete failed');
                }
            } catch (err) {
                alert('Error deleting document');
            }
        }
    );
}

async function deleteChunks(docId, title) {
    showConfirm(
        'Delete Chunks',
        `Are you sure you want to delete all embeddings for "${title}"? The document record will be kept.`,
        async () => {
            try {
                const response = await fetch(`/api/admin/documents/${docId}/chunks`, {
                    method: 'DELETE'
                });
                if (response.ok) {
                    alert('Chunks deleted successfully');
                } else {
                    const err = await response.json();
                    alert(err.error || 'Delete failed');
                }
            } catch (err) {
                alert('Error deleting chunks');
            }
        }
    );
}

async function recreateChunks(docId, title) {
    showConfirm(
        'Recreate Chunks',
        `Recreate embeddings for "${title}"? This will only run if chunks are missing.`,
        async () => {
            try {
                const response = await fetch(`/api/admin/documents/${docId}/reingest`, {
                    method: 'POST'
                });
                if (response.ok) {
                    const data = await response.json();
                    alert(data.message || 'Reingestion queued');
                    loadAdminDocuments();
                } else {
                    const err = await response.json();
                    alert(err.error || 'Reingestion failed');
                }
            } catch (err) {
                alert('Error reingesting document');
            }
        }
    );
}

async function loadActivityLog() {
    const tbody = document.getElementById('activityTableBody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="5" class="loading"><div class="spinner"></div></td></tr>';

    try {
        const response = await fetch('/api/admin/activity-log');
        if (response.ok) {
            const data = await response.json();
            renderActivityTable(data.logs || []);
        }
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="5">Error loading activity log</td></tr>';
    }
}

function renderActivityTable(logs) {
    const tbody = document.getElementById('activityTableBody');

    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">No activity found</td></tr>';
        return;
    }

    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>${new Date(log.created_at).toLocaleString()}</td>
            <td>${log.user_email}</td>
            <td>${log.action}</td>
            <td>${log.resource_type} (${log.resource_id?.substring(0, 8) || '-'}...)</td>
            <td>${JSON.stringify(log.details || {})}</td>
        </tr>
    `).join('');
}

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    // Detect which page we're on and initialize
    if (document.querySelector('.auth-container')) {
        initAuthPage();
    } else if (document.querySelector('.chat-container')) {
        initChatPage();
    } else if (document.querySelector('.admin-container')) {
        initAdminPage();
    } else if (document.querySelector('.activity-container')) {
        initUserActivityPage();
    }
});

// ========================================
// User Activity Page Functions
// ========================================
function initUserActivityPage() {
    loadUserDocuments();
    loadUserActivityLog();

    document.getElementById('refreshUserDocs')?.addEventListener('click', loadUserDocuments);
    document.getElementById('refreshUserActivity')?.addEventListener('click', loadUserActivityLog);
}

async function loadUserDocuments() {
    const tbody = document.getElementById('userDocsTableBody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="5" class="loading"><div class="spinner"></div></td></tr>';

    try {
        const response = await fetch('/api/documents');
        if (response.ok) {
            const data = await response.json();
            renderUserDocsTable(data.documents || []);
        } else {
            tbody.innerHTML = '<tr><td colspan="5">Error loading documents</td></tr>';
        }
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="5">Error loading documents</td></tr>';
    }
}

function renderUserDocsTable(docs) {
    const tbody = document.getElementById('userDocsTableBody');
    if (!tbody) return;

    if (docs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">No documents found</td></tr>';
        return;
    }

    tbody.innerHTML = docs.map(doc => {
        const scopeClass = doc.scope.toLowerCase().replace('_', '-');
        const statusClass = doc.ingestion_status.toLowerCase();

        return `
            <tr>
                <td>${doc.title}</td>
                <td><span class="scope-badge ${scopeClass}">${doc.scope}</span></td>
                <td>${formatSize(doc.size_bytes)}</td>
                <td><span class="status-badge ${statusClass}">${doc.ingestion_status}</span></td>
                <td>${formatDate(doc.created_at || doc.uploaded_at)}</td>
            </tr>
        `;
    }).join('');
}

async function loadUserActivityLog() {
    const tbody = document.getElementById('userActivityTableBody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="4" class="loading"><div class="spinner"></div></td></tr>';

    try {
        const response = await fetch('/api/documents/activity-log');
        if (response.ok) {
            const data = await response.json();
            renderUserActivityTable(data.logs || []);
        } else {
            tbody.innerHTML = '<tr><td colspan="4">Error loading activity log</td></tr>';
        }
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="4">Error loading activity log</td></tr>';
    }
}

function renderUserActivityTable(logs) {
    const tbody = document.getElementById('userActivityTableBody');
    if (!tbody) return;

    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4">No activity found</td></tr>';
        return;
    }

    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>${new Date(log.created_at).toLocaleString()}</td>
            <td>${log.action}</td>
            <td>${log.resource_type || '-'} (${log.resource_id?.substring(0, 8) || '-'}...)</td>
            <td>${JSON.stringify(log.details || {})}</td>
        </tr>
    `).join('');
}
