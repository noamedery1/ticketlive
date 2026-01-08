document.addEventListener('DOMContentLoaded', () => {
    const targetInput = document.getElementById('targetUrl');
    const saveBtn = document.getElementById('saveBtn');
    const openBtn = document.getElementById('openBtn');

    // Load saved URL
    chrome.storage.local.get(['ticketManagerUrl'], (result) => {
        if (result.ticketManagerUrl) {
            targetInput.value = result.ticketManagerUrl;
        }
    });

    saveBtn.addEventListener('click', () => {
        const url = targetInput.value.replace(/\/$/, ''); // Remove trailing slash
        chrome.storage.local.set({ ticketManagerUrl: url }, () => {
            saveBtn.textContent = 'Saved!';
            setTimeout(() => saveBtn.textContent = 'Save URL', 1500);

            // Update background script logic? 
            // Background script needs to read from storage.
            // We'll rely on background script reading storage dynamically or just updating logic there.
            // Update: background.js defined TARGET_URL as const. We should change background.js to read storage.
            chrome.runtime.sendMessage({ type: 'UPDATE_URL', url: url });
        });
    });

    openBtn.addEventListener('click', () => {
        const url = targetInput.value || 'http://localhost:8000';
        chrome.tabs.create({ url: url });
    });
});
