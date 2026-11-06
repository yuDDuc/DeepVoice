import assert from "node:assert/strict";
import { test } from "node:test";
import { mp3ToWav } from "./audio.ts";

test("mp3ToWav creates mono PCM16 WAV from decoded MP3", async () => {
  const originalAudioContext = globalThis.AudioContext;
  let contextClosed = false;
  const decodedChannels = [
    new Float32Array([-1, 0.5]),
    new Float32Array([1, 0.5]),
  ];

  class FakeAudioContext {
    async decodeAudioData() {
      return {
        numberOfChannels: decodedChannels.length,
        length: decodedChannels[0].length,
        sampleRate: 16000,
        getChannelData(channel) {
          return decodedChannels[channel];
        },
      };
    }

    async close() {
      contextClosed = true;
    }
  }

  Object.defineProperty(globalThis, "AudioContext", {
    configurable: true,
    value: FakeAudioContext,
  });

  try {
    const result = await mp3ToWav(
      new File([new Uint8Array([1])], "sample.mp3", { type: "audio/mpeg" }),
    );
    const bytes = await result.arrayBuffer();
    const view = new DataView(bytes);
    const readTag = (offset, length) =>
      String.fromCharCode(...new Uint8Array(bytes, offset, length));

    assert.equal(result.name, "sample.wav");
    assert.equal(result.type, "audio/wav");
    assert.equal(readTag(0, 4), "RIFF");
    assert.equal(readTag(8, 4), "WAVE");
    assert.equal(readTag(12, 4), "fmt ");
    assert.equal(view.getUint16(22, true), 1);
    assert.equal(view.getUint32(24, true), 16000);
    assert.equal(view.getUint16(34, true), 16);
    assert.equal(readTag(36, 4), "data");
    assert.equal(view.getInt16(44, true), 0);
    assert.equal(view.getInt16(46, true), 16384);
    assert.equal(contextClosed, true);
  } finally {
    Object.defineProperty(globalThis, "AudioContext", {
      configurable: true,
      value: originalAudioContext,
    });
  }
});
