/* Desktop audio for the standalone KasmVNC sidebar. No credentials in JavaScript. */
(() => {
    'use strict';
    const anchor = document.querySelector('#noVNC_disconnect_button')?.closest('.noVNC_button_div');
    if (!anchor || document.querySelector('#homelab_audio_button')) return;
    const row = document.createElement('div');
    row.className = 'noVNC_button_div noVNC_hide_on_disconnect';
    row.innerHTML = `<button type="button" id="homelab_audio_button" class="noVNC_button"
        aria-pressed="false" title="Play desktop audio" style="color:inherit;background:transparent;border:0;font:inherit;cursor:pointer">
        <svg width="25" height="25" viewBox="0 0 24 24" aria-hidden="true" style="vertical-align:middle;margin-right:8px">
        <path fill="currentColor" d="M3 9v6h4l5 4V5L7 9H3zm12-1v8a5 5 0 0 0 0-8zm0-4v2a7 7 0 0 1 0 12v2a9 9 0 0 0 0-16z"/></svg>
        <span>Enable audio</span></button>
        <div role="status" id="homelab_audio_status" style="max-width:180px;font-size:11px;padding:0 4px 6px" hidden></div>`;
    anchor.before(row);
    const button = row.querySelector('button');
    const label = row.querySelector('span');
    const status = row.querySelector('[role=status]');
    let session = null;
    const connected = () => document.documentElement.classList.contains('noVNC_connected');

    function stop(message = '') {
        const previous = session;
        session = null;
        if (previous) {
            clearTimeout(previous.timer);
            if (previous.socket) {
                previous.socket.onopen = previous.socket.onmessage = null;
                previous.socket.onerror = previous.socket.onclose = null;
                previous.socket.close();
            }
            if (previous.output) {
                previous.output.context.onstatechange = null;
                previous.output.destroy();
            }
        }
        button.disabled = !connected();
        button.setAttribute('aria-pressed', 'false');
        button.classList.remove('noVNC_selected');
        button.dataset.state = 'off';
        button.title = 'Play desktop audio';
        label.textContent = 'Enable audio';
        status.textContent = message;
        status.hidden = !message;
    }

    button.addEventListener('click', async () => {
        if (session) { stop(); return; }
        if (!connected()) return;
        const current = { socket: null, output: null, timer: null };
        session = current;
        button.disabled = true;
        button.dataset.state = 'connecting';
        label.textContent = 'Connecting audio…';
        status.hidden = true;
        current.timer = setTimeout(() => {
            if (session === current) stop('Audio timed out. Click to retry.');
        }, 12000);
        try {
            current.output = new JSMpeg.AudioOutput.WebAudio({});
            await current.output.context.resume();
            if (session !== current) return;
            current.output.unlocked = true;
            current.output.volume = 1;
            const decoder = new JSMpeg.Decoder.MP2Audio({ streaming: true });
            decoder.connect({
                get enqueuedTime() { return current.output.enqueuedTime; },
                play(rate, left, right) {
                    // Drop stale samples if a stalled/background tab builds a queue.
                    if (current.output.enqueuedTime < 0.25) current.output.play(rate, left, right);
                },
            });
            const demuxer = new JSMpeg.Demuxer.TS({});
            demuxer.connect(JSMpeg.Demuxer.TS.STREAM.AUDIO_1, decoder);
            const url = new URL('/kasm-audio', location.href);
            url.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            // Same-origin WebSocket uses the browser's existing Kasm HTTP auth.
            const socket = current.socket = new WebSocket(url);
            socket.binaryType = 'arraybuffer';
            socket.onopen = () => {
                if (session !== current) return;
                clearTimeout(current.timer);
                button.disabled = false;
                button.setAttribute('aria-pressed', 'true');
                button.classList.add('noVNC_selected');
                button.dataset.state = 'on';
                button.title = 'Stop desktop audio';
                label.textContent = 'Disable audio';
            };
            socket.onmessage = ({ data }) => {
                if (session !== current) return;
                try {
                    demuxer.write(data);
                    while (decoder.decode()) { /* Drain complete MP2 frames. */ }
                } catch { stop('Audio decoding failed. Click to retry.'); }
            };
            socket.onerror = () => {
                if (session === current) stop('Audio connection failed. Reload the desktop and retry.');
            };
            socket.onclose = () => {
                if (session === current) stop('Audio disconnected. Click to retry.');
            };
            current.output.context.onstatechange = () => {
                if (session === current && current.output.context.state !== 'running') {
                    stop('Audio paused by your browser. Click to resume.');
                }
            };
        } catch {
            if (session === current) stop('Could not start audio. Click to retry.');
        }
    });
    new MutationObserver(() => {
        if (!connected()) stop();
        else if (!session) button.disabled = false;
    }).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    document.querySelector('#noVNC_disconnect_button').addEventListener('click', () => stop());
    window.addEventListener('pagehide', () => stop());
    stop();
})();
