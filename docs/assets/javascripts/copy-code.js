/**
 * A robust, cross-browser copy-to-clipboard function that handles modern API and fallback.
 * @param {string} text The text to be copied to the clipboard.
 * @returns {Promise<boolean>} A promise that resolves to true if successful, false otherwise.
 */
async function copyTextToClipboard(text) {
    // Try to use the modern Clipboard API first
    if (navigator.clipboard) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            console.error('Failed to copy with navigator.clipboard: ', err);
            // Fallback will be attempted below
        }
    }

    // Fallback to the deprecated `document.execCommand('copy')`
    const textArea = document.createElement("textarea");
    let success = false;

    try {
        // Make the textarea invisible and prevent scrolling
        textArea.style.position = 'fixed';
        textArea.style.top = '-9999px';
        textArea.style.left = '-9999px';
        textArea.value = text;

        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        success = document.execCommand('copy');
        if (!success) {
            console.error('Fallback copy command was unsuccessful.');
        }
    } catch (err) {
        console.error('Fallback copy method failed: ', err);
    } finally {
        document.body.removeChild(textArea);
    }

    return success;
}

document.addEventListener('DOMContentLoaded', (event) => {
    document.querySelectorAll('pre').forEach(function (pre) {
        var code = pre.querySelector('code');
        if (code) {
            var button = document.createElement('button');
            button.className = 'copy-button';
            button.textContent = 'Copy';

            var wrapper = document.createElement('div');
            wrapper.className = 'code-wrapper';

            pre.parentNode.insertBefore(wrapper, pre);
            wrapper.appendChild(pre);
            wrapper.appendChild(button);

            button.addEventListener('click', async function () {
                const textToCopy = code.innerText;
                const success = await copyTextToClipboard(textToCopy);

                if (success) {
                    button.textContent = 'Copied!';
                    button.classList.add('copied');
                } else {
                    button.textContent = 'Error';
                }

                setTimeout(function () {
                    button.textContent = 'Copy';
                    button.classList.remove('copied');
                }, 2000);
            });
        }
    });
});
