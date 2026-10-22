"use client";

import { ArrowLeft, ArrowRight, Bird } from "lucide-react";
import Link from "next/link";
import AudioPreview from "./audio-preview";
import type { Result } from "./session";

// Reuses the original result page's cards, colours, and responsive grid.
export default function PredictionResult({ result, file, onAnother }: {
  result: Result;
  file: File;
  onAnother: () => void;
}) {
  const topThree = [...(result.top_three ?? [])]
    .sort((a, b) => b.confidence - a.confidence).slice(0, 3);

  return (
    <section id="prediction-results" className="prediction-results discovery" aria-labelledby="result-title" tabIndex={-1}>
      <Link className="text-button" href="/#listen"><ArrowLeft size={14} /> Back to upload</Link>
      <div className="discovery-heading">
        <div>
          <p className="eyebrow">LISTENED. ANALYZED. DISCOVERED.</p>
          <h1 id="result-title">{result.demo_mode ? "An example, clearly labeled." : "Your forest discovery."}</h1>
          <p>{result.demo_mode ? "Example results only. No model inference was performed." : "We listened to your recording. Here’s what the model found."}</p>
        </div>
      </div>
      <div className={`result-notice ${result.demo_mode ? "demo" : ""}`} role="status">
        <strong>{result.demo_mode ? "DEMO RESULT — NOT AN AI PREDICTION" : "ANALYSIS COMPLETE"}</strong>
        <p>{result.notice}</p>
      </div>
      <div className="results-grid">
        <section className="prediction-card">
          <Bird size={44} strokeWidth={1} />
          <p className="eyebrow">{result.demo_mode ? "EXAMPLE SPECIES" : "PREDICTED SPECIES"}</p>
          <h2>{result.prediction.species}</h2>
          <div className="big-score">
            {(result.prediction.confidence * 100).toFixed(1)}<span>%</span>
          </div>
          <p>{result.demo_mode ? "Illustrative score · not model confidence" : "Model confidence"}</p>
          {!result.demo_mode && <small>Model confidence, not a guarantee of correctness.</small>}
        </section>
        <section className="ranking-card">
          {topThree.length > 0 && <>
            <h3>{result.demo_mode ? "Top example scores" : "Top three predictions"}</h3>
            {topThree.map((prediction, index) => (
              <div className="ranking" key={prediction.label}>
                <div>
                  <span>{String(index + 1).padStart(2, "0")} &nbsp; {prediction.species}</span>
                  <strong>{(prediction.confidence * 100).toFixed(1)}%</strong>
                </div>
                <div className="bar"><span style={{ width: `${prediction.confidence * 100}%` }} /></div>
              </div>
            ))}
          </>}
          </section>
      </div>
      <section className="discovery-audio" aria-label="Your recording">
        <h3>Your recording</h3>
        <AudioPreview file={file} />
          <dl>
            <div><dt>Model</dt><dd>{result.model_name}</dd></div>
            <div><dt>Processed audio</dt><dd>{result.audio.sample_rate / 1000} kHz · {result.audio.channels === 1 ? "Mono" : `${result.audio.channels} channels`} · {result.audio.duration_seconds.toFixed(2)} s</dd></div>
          </dl>
      </section>
      <button className="button primary" onClick={onAnother}>Analyze another recording <ArrowRight size={18} /></button>
    </section>
  );
}
