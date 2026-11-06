export async function mp3ToWav(file: File): Promise<File> {
  const context = new AudioContext();
  let audio: AudioBuffer;
  try {
    audio = await context.decodeAudioData(await file.arrayBuffer());
  } catch (cause) {
    throw new Error("Trình duyệt không giải mã được tệp MP3 này.", { cause });
  } finally {
    await context.close();
  }

  if (!audio.numberOfChannels || !audio.length) {
    throw new Error("Tệp MP3 không có dữ liệu âm thanh.");
  }
  if (audio.sampleRate < 8000 || audio.sampleRate > 48000) {
    throw new Error("Sample rate của MP3 phải nằm trong khoảng 8–48 kHz.");
  }

  const mono = new Float32Array(audio.length);
  const channels = Array.from({ length: audio.numberOfChannels }, (_, index) =>
    audio.getChannelData(index),
  );
  for (let frame = 0; frame < audio.length; frame += 1) {
    let sample = 0;
    for (const channel of channels) sample += channel[frame];
    mono[frame] = sample / channels.length;
  }

  const dataLength = mono.length * 2;
  const wav = new ArrayBuffer(44 + dataLength);
  const view = new DataView(wav);
  const writeText = (offset: number, value: string) => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  };

  writeText(0, "RIFF");
  view.setUint32(4, 36 + dataLength, true);
  writeText(8, "WAVE");
  writeText(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, audio.sampleRate, true);
  view.setUint32(28, audio.sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeText(36, "data");
  view.setUint32(40, dataLength, true);

  for (let frame = 0; frame < mono.length; frame += 1) {
    const sample = Math.max(-1, Math.min(1, mono[frame]));
    view.setInt16(
      44 + frame * 2,
      Math.round(sample * (sample < 0 ? 32768 : 32767)),
      true,
    );
  }

  const stem = file.name.replace(/\.[^.]+$/, "") || file.name;
  return new File([wav], `${stem}.wav`, { type: "audio/wav" });
}
