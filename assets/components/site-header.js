class SiteHeader extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        // Read prefix to ensure links work from subdirectories (e.g. /posts/tech/)
        const prefix = this.getAttribute('prefix') || '';
        
        // This is the rich MSN-style header extracted from the top page
        this.innerHTML = `
            <header class="site-header">
                <div class="header-top">
                    <a class="brand" href="${prefix}index.html">Humanoid <span>Media</span> Factory</a>
                    <div class="header-search-container">
                        <div class="search-input-wrapper">
                            <input class="search" id="searchInput" type="search" placeholder="Search the web" aria-label="Search">
                        </div>
                    </div>
                    <div class="header-auth" style="display:flex; gap:15px; align-items:center;">
                        <span style="font-size:0.85rem; color:#616161;">Tokyo, 12°C ☀️</span>
                        <button class="tab" style="background:#0078d4; color:#fff; border-radius:4px; padding:5px 15px; border:none; cursor:pointer; font-weight:600;">Personalize</button>
                    </div>
                </div>
                <nav class="header-nav">
                    <button class="tab is-active" data-filter="all">トップ</button>
                    <button class="tab" data-filter="humanoid">ロボット・AI</button>
                    <button class="tab" data-filter="tech">テクノロジー</button>
                    <button class="tab" data-filter="zatsuki">社会・コラム</button>
                    <a href="${prefix}about.html" class="tab">About</a>
                </nav>
            </header>
        `;

        // Initialize Search and Filter interactions
        this.initInteractions();
    }

    initInteractions() {
        const tabs = this.querySelectorAll('.tab[data-filter]');
        const searchInput = this.querySelector('#searchInput');
        
        // Filtering logic: this expects cards to exist on the page with data-category attributes.
        // It works natively on index.html. On other pages, we can just let it silently fail or redirect in the future.
        const getCards = () => document.querySelectorAll('.card[data-category]');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('is-active'));
                tab.classList.add('is-active');
                
                const filter = tab.dataset.filter;
                const cards = getCards();
                cards.forEach(card => {
                    const show = filter === 'all' || card.dataset.category === filter;
                    card.style.display = show ? '' : 'none';
                });
            });
        });

        if (searchInput) {
            searchInput.addEventListener('input', () => {
                const q = searchInput.value.toLowerCase();
                const cards = getCards();
                cards.forEach(card => {
                    // Try to match only the textual content of the article cards
                    const text = card.textContent.toLowerCase();
                    card.style.display = text.includes(q) ? '' : 'none';
                });
            });
        }
    }
}

// Define the custom element
customElements.define('site-header', SiteHeader);
