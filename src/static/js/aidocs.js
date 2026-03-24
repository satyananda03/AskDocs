(() => {
    'use strict';
    const API_BASE = 'http://localhost:8000';
    const UPLOAD_URL        = `${API_BASE}/upload`;
    const CHAT_URL          = `${API_BASE}/chat/stream`;
    const DELETE_URL = (sid) => `${API_BASE}/sessions/${sid}`;
    const UPLOAD_STREAM_URL = `${API_BASE}/upload/stream`; 
    const VERIFY_URL        = `${API_BASE}/sessions`; // ✅ Endpoint baru untuk verify session
    
    // ✅ Sekarang kita HANYA menyimpan session_id di localStorage
    const LS_SESSION  = 'aidocs_session_id';

    let isDocumentReady = false;
    let sessionId       = localStorage.getItem(LS_SESSION) || null;
    let docName         = null;
    let selectedFile    = null;

    const $ = (id) => document.getElementById(id);
    const uploadBtn      = $('uploadBtn');
    const sendBtn        = $('sendBtn');
    const msgInput       = $('msgInput');
    const chatMessages   = $('chatMessages');
    const emptyState     = $('emptyState');
    const docChipArea    = $('docChipArea');
    const docChipName    = $('docChipName');
    const docChipRemove  = $('docChipRemove');
    const uploadModal    = $('uploadModal');
    const modalClose     = $('modalClose');
    const dropZone       = $('dropZone');
    const fileInput      = $('fileInput');
    const browseLink     = $('browseLink');
    const selectedFileEl = $('selectedFile');
    const modalFileName  = $('modalFileName');
    const modalFileSize  = $('modalFileSize');
    const progressBar    = $('progressBar');
    const progressFill   = $('progressFill');
    const progressLabel  = $('progressLabel');
    const progressFileName = $('progressFileName');
    const modalUploadBtn = $('modalUploadBtn');
    const toast          = $('toast');
    const modalSub = $('modalSub');

    async function init() {
        attachListeners(); // Pasang event listeners segera agar tombol bisa diklik
        
        // ✅ Cek apakah user punya sessionId saat reload page
        if (sessionId) {
            await verifySession(sessionId);
        } else {
            // Jika tidak ada session, langsung set ke state default
            applyState(false, null);
        }
    }

    // ✅ Fungsi baru untuk memverifikasi session_id ke backend
    async function verifySession(sid) {
        // Beri indikator visual selagi mengecek ke backend
        msgInput.disabled = true;
        msgInput.placeholder = 'Memeriksa sesi dokumen...';

        try {
            const res = await fetch(`${VERIFY_URL}?session_id=${sid}`);
            if (!res.ok) throw new Error('HTTP ' + res.status);
            
            const data = await res.json();
            
            if (data.is_valid) {
                // Sesi valid, render state success
                applyState(true, data.docs_name);
            } else {
                // Sesi tidak valid (mungkin sudah expire di Redis)
                throw new Error('Sesi tidak valid / expired');
            }
        } catch (err) {
            console.warn('Verifikasi gagal:', err.message);
            // Sesi invalid/error -> Hapus session dan kembali ke state awal
            clearSession();
            applyState(false, null);
        }
    }

    // ✅ Fungsi state manager yang baru (hanya dipicu dari response verifikasi / hasil upload)
    function applyState(isValid, name) {
        if (isValid && name) {
            isDocumentReady = true;
            docName = name;
            enableChat();
            showDocChip(name);
            // Disable upload btn
            uploadBtn.disabled = true; 
            uploadBtn.style.pointerEvents = 'none';
        } else {
            isDocumentReady = false;
            docName = null;
            disableChat();
            hideDocChip();
            showEmptyState();
            // Aktifkan kembali tombol upload saat dokumen kosong (Document not ready)
            uploadBtn.disabled = false; 
            uploadBtn.style.pointerEvents = 'auto';
        }
    }

    function clearSession() {
        sessionId = null;
        docName = null;
        isDocumentReady = false;
        localStorage.removeItem(LS_SESSION);
    }

    function enableChat() {
        msgInput.disabled = false;
        msgInput.placeholder = 'Tanya apa saja tentang dokumen ini...';
        sendBtn.disabled = false;
    }

    function disableChat() {
        msgInput.disabled = true;
        msgInput.placeholder = 'Silahkan upload dokumen...';
        sendBtn.disabled = true;
    }

    function showDocChip(name) {
        docChipName.textContent = name;
        docChipArea.classList.add('visible');
        hideEmptyState();
    }

    function hideDocChip() {
        docChipArea.classList.remove('visible');
    }

    function hideEmptyState() {
        emptyState.style.display = 'none';
    }

    function showEmptyState() {
        emptyState.style.display = 'flex';
    }

    let toastTimer;
    function showToast(msg, type = 'success') {
        clearTimeout(toastTimer);
        toast.textContent = msg;
        toast.className = `${type} show`;
        toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
    }

    function addMessage(content, role = 'bot') {
        hideEmptyState();
        const msg = document.createElement('div');
        msg.className = `msg ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'msg-avatar';
        avatar.innerHTML = role === 'bot'
            ? `<svg viewBox="0 0 24 24" width="14" height="14" fill="#FF1C00"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 1.5L18.5 9H13V3.5z"/></svg>`
            : `<svg viewBox="0 0 24 24" width="14" height="14" fill="#FF1C00"><path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/></svg>`;

        const bubble = document.createElement('div');
        bubble.className = 'msg-bubble';
        bubble.innerHTML = content;

        msg.appendChild(avatar);
        msg.appendChild(bubble);
        chatMessages.appendChild(msg);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        return bubble;
    }

    function parseBold(text) {
        return text
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    }

    async function sendMessage() {
        if (!isDocumentReady) return;
        const text = msgInput.value.trim();
        if (!text) return;

        msgInput.value = '';
        msgInput.style.height = 'auto';
        msgInput.disabled = true;
        sendBtn.disabled = true;

        addMessage(text, 'user');

        const botBubble = addMessage('<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>', 'bot');
        let fullResponse = '';

        try {
            const res = await fetch(CHAT_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, session_id: sessionId })
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buf = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buf += decoder.decode(value, { stream: true });
                const lines = buf.split('\n');
                buf = lines.pop() || '';

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.error) {
                            botBubble.innerHTML = `<span style="color:#cf6f6f">Error: ${data.error}</span>`;
                            break;
                        }
                        if (!data.done) {
                            if (Array.isArray(data.content)) fullResponse += data.content.map(c => c.text || '').join('');
                            else if (typeof data.content === 'string') fullResponse += data.content;
                            botBubble.innerHTML = parseBold(fullResponse);
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }
                    } catch { /* incomplete chunk */ }
                }
            }
        } catch (err) {
            botBubble.innerHTML = `<span style="color:#cf6f6f">Koneksi gagal. Coba lagi.</span>`;
        } finally {
            msgInput.disabled = false;
            sendBtn.disabled = false;
            msgInput.focus();
        }
    }

    async function doUpload() {
        if (!selectedFile) return;

        selectedFileEl.style.display = 'none';
        modalUploadBtn.style.display = 'none';
        modalSub.style.display = 'none';

        progressFileName.textContent = selectedFile.name;
        progressLabel.textContent = 'Mengunggah file...';
        progressFill.style.width = '0%';
        progressBar.classList.add('visible');

        try {
            const formData = new FormData();
            formData.append('file', selectedFile);
            if (sessionId) formData.append('session_id', sessionId);

            const res = await fetch(UPLOAD_URL, { method: 'POST', body: formData });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const data = await res.json();
            sessionId = data.session_id || sessionId;
            if (sessionId) localStorage.setItem(LS_SESSION, sessionId);

            progressLabel.textContent = 'Memproses dokumen...';
            await waitForProcessing(sessionId);

            closeModal();
            // ✅ Ubah state secara langsung jika berhasil
            applyState(true, selectedFile.name); 
            
            showToast('Dokumen siap!');
            addMessage(`Dokumen <strong>${selectedFile.name}</strong> berhasil dimuat 🎉. Silahkan bertanya!`, 'bot');
            selectedFile = null;

        } catch (err) {
            showToast('Gagal upload: ' + err.message, 'error');
            progressBar.classList.remove('visible');
            modalUploadBtn.disabled = false;
            modalUploadBtn.textContent = 'Upload Dokumen';
        }
    }

    async function waitForProcessing(sid) {
        return new Promise((resolve, reject) => {
            const evtSource = new EventSource(`${UPLOAD_STREAM_URL}?session_id=${sid}`);
            
            let fakeProgressInterval = null;
            let currentFakeProgress = 0;

            function startFakeProgress() {
                if (fakeProgressInterval) return;
                fakeProgressInterval = setInterval(() => {
                    if (currentFakeProgress < 85) {
                        let increment = currentFakeProgress < 50 ? 2 : 0.5;
                        currentFakeProgress += increment;
                        progressFill.style.width = currentFakeProgress + '%';                        
                    }
                }, 1000); 
            }

            function stopFakeProgress() {
                clearInterval(fakeProgressInterval);
                fakeProgressInterval = null;
            }

            const warningElement = document.getElementById('upload-warning');
            if (warningElement) warningElement.style.display = 'block';

            evtSource.onmessage = (e) => {
                try {
                    const d = JSON.parse(e.data);

                    if (d.status === 'extracting') {
                        startFakeProgress(); 
                        if (d.message) progressLabel.textContent = d.message; 
                        return; 
                    }

                    stopFakeProgress();
                    
                    if (d.status === 'indexing') {
                        progressFill.style.width = '95%';
                        progressLabel.textContent = d.message;
                    }

                    if (d.status === 'completed') {
                        progressFill.style.width = '100%';
                        if (warningElement) warningElement.style.display = 'none'; 
                        evtSource.close(); 
                        resolve(); 
                    }

                    if (d.status === 'error') {
                        stopFakeProgress();
                        if (warningElement) warningElement.style.display = 'none';
                        evtSource.close(); 
                        reject(new Error(d.message || 'Proses gagal')); 
                    }
                } catch { }
            };
            evtSource.onerror = () => { stopFakeProgress(); evtSource.close(); reject(new Error('Koneksi SSE terputus')); };
            setTimeout(() => { stopFakeProgress(); evtSource.close(); reject(new Error('Timeout 5 menit')); }, 300_000);
        });
    }

    // ── Delete document ───────────────────────────────────────────────────────────
    async function deleteDocument() {
        try {
            if (sessionId) {
                await fetch(DELETE_URL(sessionId), { method: 'DELETE' });
            }
        } catch { /* silent */ }

        // ✅ Gunakan reset method yang baru
        clearSession();
        applyState(false, null);
        chatMessages.innerHTML = '';
        chatMessages.appendChild(emptyState);
        showToast('Dokumen dihapus.', 'success');
    }

    // ── Modal ────────────────────────────────────────────────────────────────────
    function openModal() {
        resetModalForm();
        uploadModal.style.display = 'flex';
        requestAnimationFrame(() => uploadModal.classList.add('visible'));
    }

    function closeModal() {
        uploadModal.classList.remove('visible');
        setTimeout(() => { uploadModal.style.display = 'none'; }, 270);
    }

    function resetModalForm() {
        selectedFile = null;
        fileInput.value = '';
        selectedFileEl.classList.remove('visible');
        selectedFileEl.style.display = '';
        progressBar.classList.remove('visible');
        progressFill.style.width = '0%';
        modalUploadBtn.disabled = true;
        modalUploadBtn.textContent = 'Upload Dokumen';
        modalUploadBtn.style.display = '';
        modalSub.style.display = '';
        dropZone.style.display = '';
    }

    const SUPPORTED_TYPES = {
    'application/pdf': { ext: 'pdf', maxMB: 10 },
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { ext: 'docx', maxMB: 10 },
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': { ext: 'pptx', maxMB: 10 }
    };

    function handleFileSelected(file) {
        if (!file || !SUPPORTED_TYPES[file.type]) {
            showToast('Format tidak didukung. Gunakan PDF, DOCX, PPTX, atau XLSX.', 'error');
            return;
        }

        const { maxMB } = SUPPORTED_TYPES[file.type];
        if (file.size > maxMB * 1024 * 1024) {
            showToast(`File terlalu besar. Maks. ${maxMB} MB untuk format ini.`, 'error');
            return;
        }

        selectedFile = file;

        dropZone.style.display = 'none';
        modalFileName.textContent = file.name;
        modalFileSize.textContent = formatSize(file.size);
        selectedFileEl.classList.add('visible');

        modalUploadBtn.disabled = false;
        modalUploadBtn.style.display = '';
    }
    
    // function handleFileSelected(file) {
    //     if (!file || file.type !== 'application/pdf') {
    //         showToast('Hanya file PDF yang didukung.', 'error');
    //         return;
    //     }
    //     if (file.size > 10 * 1024 * 1024) { 
    //         showToast('File terlalu besar. Maks. 10 MB.', 'error');
    //         return;
    //     }
    //     selectedFile = file;

    //     dropZone.style.display = 'none';
    //     modalFileName.textContent = file.name;
    //     modalFileSize.textContent = formatSize(file.size);
    //     selectedFileEl.classList.add('visible');

    //     modalUploadBtn.disabled = false;
    //     modalUploadBtn.style.display = '';
    // }

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    // ── Event listeners ──────────────────────────────────────────────────────────
    function attachListeners() {
        uploadBtn.addEventListener('click', openModal);

        sendBtn.addEventListener('click', sendMessage);
        msgInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        msgInput.addEventListener('input', () => {
            msgInput.style.height = 'auto';
            msgInput.style.height = Math.min(msgInput.scrollHeight, 120) + 'px';
        });

        modalClose.addEventListener('click', closeModal);
        uploadModal.addEventListener('click', (e) => { if (e.target === uploadModal) closeModal(); });
        document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

        browseLink.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('click', (e) => { if (e.target !== browseLink) fileInput.click(); });
        fileInput.addEventListener('change', () => { if (fileInput.files[0]) handleFileSelected(fileInput.files[0]); });

        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragging'); });
        dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragging'));
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragging');
            handleFileSelected(e.dataTransfer.files[0]);
        });

        $('selectedFileRemove').addEventListener('click', () => {
            selectedFile = null;
            fileInput.value = '';
            selectedFileEl.classList.remove('visible');
            dropZone.style.display = '';
            modalUploadBtn.disabled = true;
        });
        
        modalUploadBtn.addEventListener('click', doUpload);
        docChipRemove.addEventListener('click', deleteDocument);
    }

    init();
})();