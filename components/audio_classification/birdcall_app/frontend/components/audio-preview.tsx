"use client";
import { useEffect, useState } from "react";
export default function AudioPreview({ file }: { file: File }) {
  const [url, setUrl] = useState<string | undefined>(undefined);
  const [bars, setBars] = useState<number[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    setBars([]);
    setError("");
    const context = new AudioContext();
    file
      .arrayBuffer()
      .then((b) => context.decodeAudioData(b))
      .then((buffer) => {
        if (!active) return;
        const samples = buffer.getChannelData(0);
        const values = Array.from({ length: 90 }, (_, i) => {
          const start = Math.floor((i * samples.length) / 90),
            end = Math.floor(((i + 1) * samples.length) / 90);
          let peak = 0;
          for (let j = start; j < end; j++)
            peak = Math.max(peak, Math.abs(samples[j]));
          return peak;
        });
        const peak = Math.max(...values, 0.001);
        setBars(values.map((v) => v / peak));
      })
      .catch(() => {
        if (active)
          setError(
            "Waveform preview is unavailable in this browser. The server can still validate the audio.",
          );
      })
      .finally(() => context.close());
    return () => {
      active = false;
      URL.revokeObjectURL(objectUrl);
    };
  }, [file]);
  return (
    <div className="audio-preview">
      <div className="file-line">
        <strong>{file.name}</strong>
        <span>{(file.size / 1024 / 1024).toFixed(2)} MB</span>
      </div>
      {bars.length > 0 ? (
        <div
          className="waveform"
          role="img"
          aria-label="Waveform of your recording"
        >
          {bars.map((v, i) => (
            <span key={i} style={{ height: `${Math.max(3, v * 65)}px` }} />
          ))}
        </div>
      ) : (
        <p className="muted">{error || "Reading waveform…"}</p>
      )}
      <audio aria-label="Recording preview" controls src={url} />
    </div>
  );
}
