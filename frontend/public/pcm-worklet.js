/* AudioContext requests the negotiated sampling rate; reject mismatches in UI. */
class PCMProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.size = options.processorOptions.frameSamples;
    this.buffer = new Float32Array(this.size);
    this.offset = 0;
    this.port.onmessage = (e) => {
      if (e.data === "flush") {
        if (this.offset) {
          const pcm = new Int16Array(this.offset);
          for (let j = 0; j < this.offset; j++)
            pcm[j] = Math.max(-1, Math.min(1, this.buffer[j])) * 32767;
          this.port.postMessage(pcm.buffer, [pcm.buffer]);
          this.offset = 0;
        }
        this.port.postMessage("flushed");
      }
    };
  }
  process(inputs) {
    const input = inputs[0]?.[0];
    if (input) {
      for (let i = 0; i < input.length; i++) {
        this.buffer[this.offset++] = input[i];
        if (this.offset === this.size) {
          const pcm = new Int16Array(this.size);
          for (let j = 0; j < this.size; j++)
            pcm[j] = Math.max(-1, Math.min(1, this.buffer[j])) * 32767;
          this.port.postMessage(pcm.buffer, [pcm.buffer]);
          this.offset = 0;
        }
      }
    }
    return true;
  }
}
registerProcessor("avrt-pcm", PCMProcessor);
