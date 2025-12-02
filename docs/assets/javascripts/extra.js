// Custom JavaScript for Selfhosted documentation

document.addEventListener('DOMContentLoaded', function() {
    // Add copy button functionality for code blocks
    const codeBlocks = document.querySelectorAll('pre code');
    codeBlocks.forEach(function(block) {
        const pre = block.parentElement;
        if (pre.classList.contains('highlight')) {
            const button = document.createElement('button');
            button.className = 'md-clipboard md-icon';
            button.title = 'Copy to clipboard';
            button.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z" /></svg>';

            button.addEventListener('click', function() {
                navigator.clipboard.writeText(block.textContent).then(function() {
                    button.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z" /></svg>';
                    setTimeout(function() {
                        button.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z" /></svg>';
                    }, 2000);
                });
            });

            pre.appendChild(button);
        }
    });

    // Add smooth scrolling to anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add external link indicators
    // Only apply to links that are truly external (not to this site or GitHub repo)
    const siteUrl = window.location.hostname;
    const repoUrl = 'github.com/chutch3/selfhosted.sh';

    const externalLinks = document.querySelectorAll('a[href^="http"]');
    externalLinks.forEach(function(link) {
        const href = link.getAttribute('href');
        // Skip if link is to the current site or the GitHub repo
        if (href.includes(siteUrl) || href.includes(repoUrl)) {
            return;
        }

        if (!link.querySelector('svg')) {
            link.innerHTML += ' <svg class="external-link-icon" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15,3 21,3 21,9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>';
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');
        }
    });
});

// Add dark mode detection for Mermaid
if (typeof mermaid !== 'undefined') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDarkMode = document.body.getAttribute('data-md-color-scheme') === 'slate';

    mermaid.initialize({
        startOnLoad: true,
        theme: (isDarkMode || prefersDark) ? 'dark' : 'default',
        themeVariables: {
            primaryColor: '#2196F3',
            primaryTextColor: isDarkMode ? '#ffffff' : '#000000',
            background: isDarkMode ? '#1e1e1e' : '#ffffff'
        }
    });
}
