// CONFIGURATION
const DEFAULT_URL = 'http://localhost:8000';

chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "parse-ticket",
        title: "⚡ Parse Ticket Offer",
        contexts: ["selection"]
    });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === "parse-ticket" && info.selectionText) {
        const rawText = info.selectionText;

        chrome.storage.local.get(['ticketManagerUrl'], (result) => {
            const baseUrl = result.ticketManagerUrl || DEFAULT_URL;
            // Construct the URL with query params
            const url = `${baseUrl}?raw=${encodeURIComponent(rawText)}&autoparse=true`;

            // Open in new tab
            chrome.tabs.create({ url: url });
        });
    }
});
