"use client";

import { useEffect, useState } from "react";
import { api, API } from "./session";
import { ArrowUpRight, RefreshCw } from "lucide-react";

type Report = {
  name: string;
  base_model: string;
  run_id: string;
  checkpoint_available: boolean;
  metrics: { accuracy: number; macro_f1: number; loss: number };
  validation_clips: number;
  best_epoch: number;
  source: string;
  notice: string;
  species: { name: string; precision: number; recall: number; f1: number; support: number }[];
  figures: { id: string; url: string }[];
};
const titles: Record<string, string> = {
  "learning-curves": "Training & validation learning curves",
  "confusion-matrix": "Validation confusion matrix",
  "precision-recall": "Per-species validation precision & recall",
};

export default function ModelReport() {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  function load() {
    setError("");
    api<Report>("/model-info").then(setReport).catch(() => setError("Cannot load the training report. Start or restart the updated FastAPI backend, then retry."));
  }
  useEffect(() => { load(); }, []);
  return <section id="model" className="model-section">
    <div className="section-heading">
      <div><p className="eyebrow">03 / THE TRAINED MODEL</p><h2>From field recordings to findings.</h2></div>
      <span className="pill">WAV2VEC2 · VALIDATION REPORT</span>
    </div>
    {!report ? <div className="report-empty" role="status"><p>{error || "Loading the saved research results…"}</p>{error && <button className="text-button" onClick={load}><RefreshCw size={14}/> Retry report</button>}</div> : <>
      <div className="model-summary"><div><p className="eyebrow">{report.base_model}</p><h3>Wav2Vec2, trained on your ten species.</h3><p>Finalized run <code>{report.run_id}</code></p></div><span className="pill">{report.checkpoint_available ? "TRAINED CHECKPOINT SAVED" : "CHECKPOINT FILE MISSING"}</span></div>
      <div className="metric-grid">
        <article><span>Validation accuracy</span><strong>{(report.metrics.accuracy * 100).toFixed(2)}<small>%</small></strong><p>Correct predictions on validation clips</p></article>
        <article><span>Validation macro F1</span><strong>{report.metrics.macro_f1.toFixed(4)}</strong><p>F1 averaged equally across ten species</p></article>
        <article><span>Validation clips</span><strong>{report.validation_clips.toLocaleString()}</strong><p>Evaluation split recorded in this run</p></article>
        <article><span>Selected epoch</span><strong>{String(report.best_epoch).padStart(2, "0")}</strong><p>Best saved checkpoint · loss {report.metrics.loss.toFixed(4)}</p></article>
      </div>
      <p className="evaluation-note">{report.notice} A saved checkpoint and a running inference server are separate states; check the upload panel for live readiness.</p>
      <details className="report-details"><summary>Explore performance by species <span>Precision, recall & F1</span></summary><div className="table-scroll"><table><caption>Saved validation classification report</caption><thead><tr><th scope="col">Species</th><th scope="col">Precision</th><th scope="col">Recall</th><th scope="col">F1</th><th scope="col">Clips</th></tr></thead><tbody>{report.species.map(s => <tr key={s.name}><th scope="row">{s.name}</th><td>{s.precision.toFixed(3)}</td><td>{s.recall.toFixed(3)}</td><td><span className="f1-value">{s.f1.toFixed(3)}</span></td><td>{s.support}</td></tr>)}</tbody></table></div></details>
      <div className="research-figures">{report.figures.map(f => <figure key={f.id}><a href={`${API}${f.url}`} target="_blank" rel="noreferrer"><img src={`${API}${f.url}`} alt={titles[f.id]} loading="lazy"/><figcaption>{titles[f.id]}<ArrowUpRight size={16}/></figcaption></a></figure>)}</div>
      <p className="report-source">Source: <code>{report.source}</code> · Read directly from your saved artifacts.</p>
    </>}
  </section>;
}
