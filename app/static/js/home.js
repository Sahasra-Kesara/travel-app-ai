// Home page JS extracted from home.html
// NOTE: This file expects a global `suggestUrl` variable to be defined by the template

const input = document.getElementById("searchInput");
const suggestionBox = document.getElementById("suggestions");
const form = document.getElementById("searchForm");

let debounceTimer;
let selectedIndex = -1;
let currentSuggestions = [];

// ============================
// Submit on Enter (when no suggestion selected)
// ============================
if (input) {
    input.addEventListener("keydown", function(event) {
        const items = suggestionBox ? suggestionBox.querySelectorAll("li") : [];

        if (event.key === "ArrowDown") {
            event.preventDefault();
            selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
            highlightItem(items);
        }
        else if (event.key === "ArrowUp") {
            event.preventDefault();
            selectedIndex = Math.max(selectedIndex - 1, 0);
            highlightItem(items);
        }
        else if (event.key === "Enter") {
            event.preventDefault();

            if (selectedIndex >= 0 && items[selectedIndex]) {
                input.value = items[selectedIndex].textContent;
            }

            if (suggestionBox) suggestionBox.classList.add("hidden");
            if (form) form.submit();
        }
    });
}

function highlightItem(items){
    items.forEach(item => item.classList.remove("bg-blue-100"));
    if(items[selectedIndex]){
        items[selectedIndex].classList.add("bg-blue-100");
    }
}

function setExample(text){
    if(!input) return;
    input.value = text;
    input.focus();
    if (suggestionBox) suggestionBox.classList.add("hidden");
}

// ============================
// AI Auto Suggestions (Debounced)
// ============================
if (input) {
    input.addEventListener("input", function(){
        const query = input.value.trim();

        selectedIndex = -1;

        if(query.length < 2){
            if (suggestionBox) suggestionBox.classList.add("hidden");
            return;
        }

        // Debounce (300ms)
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => fetchSuggestions(query), 300);
    });
}

async function fetchSuggestions(query){
    if (!window.suggestUrl) {
        console.warn('suggestUrl not provided');
        return;
    }
    try{
        const res = await fetch(`${window.suggestUrl}?q=${encodeURIComponent(query)}`);
        const data = await res.json();

        currentSuggestions = data;
        if (suggestionBox) suggestionBox.innerHTML = "";

        if(data.length === 0){
            if (suggestionBox) suggestionBox.classList.add("hidden");
            return;
        }

        data.forEach((item) => {
            const li = document.createElement("li");
            li.className = "px-4 py-2 hover:bg-blue-50 cursor-pointer text-sm";
            li.textContent = item;

            li.onclick = () => {
                if (input) input.value = item;
                if (suggestionBox) suggestionBox.classList.add("hidden");
                if (form) form.submit();
            };

            if (suggestionBox) suggestionBox.appendChild(li);
        });

        if (suggestionBox) suggestionBox.classList.remove("hidden");

    }catch(error){
        console.error("Suggestion error:", error);
        if (suggestionBox) suggestionBox.classList.add("hidden");
    }
}

// ============================
// Hide when clicking outside & Escape
// ============================
document.addEventListener("click", function(e){
    if (suggestionBox && !suggestionBox.contains(e.target) && e.target !== input){
        suggestionBox.classList.add("hidden");
    }
});

if (input) {
    input.addEventListener("keydown", function(event){
        if(event.key === "Escape"){
            if (suggestionBox) suggestionBox.classList.add("hidden");
        }
    });
}

// Inline suggestion / ghost text utilities
const ghostText = document.getElementById("ghostText");
let inlineSuggestion = "";

function showInlineSuggestion(query, suggestions) {
    if (!suggestions.length) {
        if (ghostText) ghostText.textContent = "";
        inlineSuggestion = "";
        return;
    }

    const first = suggestions[0];

    if (first.toLowerCase().startsWith(query.toLowerCase())) {
        inlineSuggestion = first;
        if (ghostText) ghostText.textContent = first;
    } else {
        inlineSuggestion = "";
        if (ghostText) ghostText.textContent = "";
    }
}

// ============================
// FLOATING SEARCH BAR AT BOTTOM - ENHANCED
// ============================
const floatingSearchWrapper = document.getElementById('floatingSearchWrapper');
const floatingSearchInput = document.getElementById('floatingSearchInput');
const floatingSearchBtn = document.getElementById('floatingSearchBtn');
const floatingSearchSuggestions = document.getElementById('floatingSearchSuggestions');
const floatingGhostText = document.getElementById('floatingGhostText');

let floatingSelectedIndex = -1;
let floatingInlineSuggestion = "";
let floatingSuggestionsList = [];
let floatingDebounceFTimer;
let isFloatingSearchHidden = false;

document.addEventListener('DOMContentLoaded', () => {
    const floatingSearch = document.getElementById('floatingSearchWrapper');
    const closeBtn = document.getElementById('closeFloatingSearch');
    const footer = document.querySelector('footer');

    // Show search bar after scrolling past hero section
    window.addEventListener('scroll', () => {
        const scrollY = window.scrollY;
        const hero = document.querySelector('section.relative');
        const heroHeight = hero ? hero.offsetHeight : 0;

        // Show floating search if past hero but before footer
        if (scrollY > heroHeight && !isFooterVisible()) {
            if (floatingSearch) {
                floatingSearch.classList.remove('hidden');
                floatingSearch.classList.add('visible');
            }
        } else {
            if (floatingSearch) {
                floatingSearch.classList.remove('visible');
                floatingSearch.classList.add('hidden');
            }
        }
    });

    // Close button
    if (closeBtn) closeBtn.addEventListener('click', () => {
        if (floatingSearch) {
            floatingSearch.classList.remove('visible');
            floatingSearch.classList.add('hidden');
        }
    });

    // Detect if footer is visible
    function isFooterVisible() {
        if (!footer) return false;
        const footerTop = footer.getBoundingClientRect().top;
        const windowHeight = window.innerHeight;
        return footerTop <= windowHeight;
    }

    // Optional: Auto-focus input when search bar appears
    const searchInput = document.getElementById('floatingSearchInput');
    if (floatingSearch) {
        floatingSearch.addEventListener('transitionend', () => {
            if (floatingSearch.classList.contains('visible') && searchInput) {
                searchInput.focus();
            }
        });
    }
});

// Show/hide floating search when scrolled (additional guard)
window.addEventListener('scroll', function() {
    const scrollY = window.scrollY;
    if (scrollY > 400) {
        if (floatingSearchWrapper && !floatingSearchWrapper.classList.contains('visible') && !isFloatingSearchHidden) {
            floatingSearchWrapper.classList.remove('hidden');
            floatingSearchWrapper.classList.add('visible');
        }
    } else {
        if (floatingSearchWrapper && floatingSearchWrapper.classList.contains('visible') && !isFloatingSearchHidden) {
            floatingSearchWrapper.classList.remove('visible');
            if (floatingSearchSuggestions) floatingSearchSuggestions.classList.remove('visible');
        }
    }
});

// Handle hidden state and animation completion
if (floatingSearchWrapper) {
    floatingSearchWrapper.addEventListener('animationend', function(e) {
        if (e.animationName === 'slideDownFinal' && floatingSearchWrapper.classList.contains('hidden')) {
            floatingSearchWrapper.classList.remove('visible');
            isFloatingSearchHidden = true;
        }
    });
}

// Sync floating input with main input
if (input && floatingSearchInput) {
    input.addEventListener('input', function() {
        floatingSearchInput.value = this.value;
    });

    floatingSearchInput.addEventListener('input', function() {
        input.value = this.value;
        const query = this.value.trim();
        floatingSelectedIndex = -1;

        if (query.length < 2) {
            if (floatingSearchSuggestions) floatingSearchSuggestions.classList.remove('visible');
            if (floatingGhostText) floatingGhostText.textContent = '';
            return;
        }

        clearTimeout(floatingDebounceFTimer);
        floatingDebounceFTimer = setTimeout(() => fetchFloatingSuggestions(query), 300);
    });
}

// Focus on floating input should reset hidden state
if (floatingSearchInput) {
    floatingSearchInput.addEventListener('focus', function() {
        if (isFloatingSearchHidden && window.scrollY > 400) {
            floatingSearchWrapper.classList.remove('hidden');
            isFloatingSearchHidden = false;
        }
    });
}

// Fetch suggestions for floating search
async function fetchFloatingSuggestions(query) {
    if (!window.suggestUrl) return;
    try {
        const res = await fetch(`${window.suggestUrl}?q=${encodeURIComponent(query)}`);
        const data = await res.json();

        floatingSuggestionsList = data;
        if (floatingSearchSuggestions) floatingSearchSuggestions.innerHTML = '';

        // Show inline suggestion
        if (data.length > 0) {
            const first = data[0];
            if (first.toLowerCase().startsWith(query.toLowerCase())) {
                floatingInlineSuggestion = first;
                if (floatingGhostText) floatingGhostText.textContent = first;
            } else {
                floatingInlineSuggestion = '';
                if (floatingGhostText) floatingGhostText.textContent = '';
            }
        }

        if (data.length === 0) {
            if (floatingSearchSuggestions) floatingSearchSuggestions.classList.remove('visible');
            return;
        }

        data.forEach((item) => {
            const li = document.createElement('li');
            li.textContent = item;
            li.addEventListener('click', () => {
                if (floatingSearchInput) floatingSearchInput.value = item;
                if (input) input.value = item;
                if (floatingGhostText) floatingGhostText.textContent = '';
                if (floatingSearchSuggestions) floatingSearchSuggestions.classList.remove('visible');
                if (form) form.submit();
            });

            if (floatingSearchSuggestions) floatingSearchSuggestions.appendChild(li);
        });

        if (floatingSearchSuggestions) floatingSearchSuggestions.classList.add('visible');

    } catch (error) {
        console.error('Floating search error:', error);
        if (floatingSearchSuggestions) floatingSearchSuggestions.classList.remove('visible');
    }
}

// Keyboard navigation for floating search
if (floatingSearchInput) {
    floatingSearchInput.addEventListener('keydown', function(e) {
        const items = floatingSearchSuggestions ? floatingSearchSuggestions.querySelectorAll('li') : [];

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            floatingSelectedIndex = Math.min(floatingSelectedIndex + 1, items.length - 1);
            highlightFloatingItem(items);
        }
        else if (e.key === 'ArrowUp') {
            e.preventDefault();
            floatingSelectedIndex = Math.max(floatingSelectedIndex - 1, -1);
            highlightFloatingItem(items);
        }
        else if (e.key === 'Enter') {
            e.preventDefault();
            if (floatingSelectedIndex >= 0 && items[floatingSelectedIndex]) {
                floatingSearchInput.value = items[floatingSelectedIndex].textContent;
                if (input) input.value = items[floatingSelectedIndex].textContent;
            }
            if (floatingSearchSuggestions) floatingSearchSuggestions.classList.remove('visible');
            if (form) form.submit();
        }
        else if (e.key === 'Tab') {
            e.preventDefault();
            if (floatingInlineSuggestion) {
                floatingSearchInput.value = floatingInlineSuggestion;
                if (input) input.value = floatingInlineSuggestion;
                if (floatingGhostText) floatingGhostText.textContent = '';
                floatingInlineSuggestion = '';
                if (floatingSearchSuggestions) floatingSearchSuggestions.classList.remove('visible');
            }
        }
        else if (e.key === 'Escape') {
            if (floatingSearchSuggestions) floatingSearchSuggestions.classList.remove('visible');
        }
    });
}

function highlightFloatingItem(items) {
    items.forEach(item => item.classList.remove('selected'));
    if (floatingSelectedIndex >= 0 && items[floatingSelectedIndex]) {
        items[floatingSelectedIndex].classList.add('selected');
    }
}

// Submit floating search
if (floatingSearchBtn) {
    floatingSearchBtn.addEventListener('click', function() {
        if (form) form.submit();
    });
}

// Hide suggestions when clicking outside
document.addEventListener('click', function(e) {
    if (floatingSearchSuggestions && !floatingSearchSuggestions.contains(e.target) && e.target !== floatingSearchInput) {
        floatingSearchSuggestions.classList.remove('visible');
    }
});

// Functions for showing/hiding floating search (used by template inline helpers)
function showFloatingSearch() {
    if (floatingSearchWrapper) {
        floatingSearchWrapper.classList.remove('hidden');
        floatingSearchWrapper.classList.add('visible');
    }
}

function hideFloatingSearch() {
    if (floatingSearchWrapper) {
        floatingSearchWrapper.classList.remove('visible');
        floatingSearchWrapper.classList.add('hidden');
    }
}

// Optional: show on page load
window.addEventListener('load', () => {
});
