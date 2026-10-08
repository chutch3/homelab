import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { describe, expect, it } from 'vitest';

const library = readFileSync(new URL('../../vendor/jsmpeg/jsmpeg.min.js', import.meta.url), 'utf8');
const tone = readFileSync(new URL('../fixtures/tone.mpegts', import.meta.url));

describe('pinned JSMpeg compatibility with the Kasm audio format', () => {
  it.each([188, 701, 4096])('decodes non-silent 44.1 kHz MP2 from %i-byte chunks', size => {
    const sandbox = { window: {}, document: { readyState: 'loading', addEventListener() {} }, console };
    vm.runInNewContext(library, sandbox);
    const { JSMpeg } = sandbox;
    const decoder = new JSMpeg.Decoder.MP2Audio({ streaming: true });
    const demuxer = new JSMpeg.Demuxer.TS({});
    let samples = 0;
    let power = 0;
    const pcm = [];
    decoder.connect({
      enqueuedTime: 0,
      play(rate, left) {
        expect(rate).toBe(44100);
        for (const sample of left) {
          expect(Number.isFinite(sample)).toBe(true);
          pcm.push(sample);
          samples++;
          power += sample * sample;
        }
      },
    });
    demuxer.connect(JSMpeg.Demuxer.TS.STREAM.AUDIO_1, decoder);
    for (let offset = 0; offset < tone.length; offset += size) {
      const chunk = tone.subarray(offset, offset + size);
      demuxer.write(chunk.buffer.slice(chunk.byteOffset, chunk.byteOffset + chunk.byteLength));
      while (decoder.decode()) { /* Flush complete frames. */ }
    }
    expect(samples).toBeGreaterThan(40000);
    // This pinned fixture decodes at this level in JSMpeg; source amplitude is not output gain.
    expect(Math.sqrt(power / samples)).toBeCloseTo(0.04359445908, 4);
    // Find the dominant spectral component in a steady half-second window.
    // Counting zero crossings also counts MP2 ringing near zero amplitude.
    const steady = pcm.slice(4096, 4096 + 22050);
    let peakFrequency = 0;
    let peakPower = 0;
    for (let frequency = 50; frequency <= 1000; frequency += 2) {
      const coefficient = 2 * Math.cos(2 * Math.PI * frequency / 44100);
      let previous = 0;
      let beforePrevious = 0;
      for (const sample of steady) {
        const current = sample + coefficient * previous - beforePrevious;
        beforePrevious = previous;
        previous = current;
      }
      const binPower = previous * previous + beforePrevious * beforePrevious -
        coefficient * previous * beforePrevious;
      if (binPower > peakPower) { peakPower = binPower; peakFrequency = frequency; }
    }
    expect(peakFrequency).toBe(440);
  });
});
