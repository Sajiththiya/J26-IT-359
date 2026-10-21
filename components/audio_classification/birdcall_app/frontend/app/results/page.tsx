"use client";
import Link from "next/link";
import { ArrowLeft, Bird, ArrowRight } from "lucide-react";
import { useSession } from "@/components/session";
import AudioPreview from "@/components/audio-preview";
export default function Results() {
  const { result: r, file } = useSession();
  if (!r)
    return (
      <main className="state-page">
        <section className="state-card">
          <Bird size={40} />
          <h1>No result yet.</h1>
          <p>
            Analyze a recording to see its result. Results are kept only for
            this browser session and cleared on refresh.
          </p>
          <Link href="/#listen" className="button primary">
            Choose a recording
          </Link>
        </section>
      </main>
    );
  return (
    <main className="results-page">
      <Link className="text-button" href="/#listen">
        <ArrowLeft size={16} /> Back to recordings
      </Link>
      <div className="section-heading">
        <div>
          <p className="eyebrow">03 / YOUR DISCOVERY</p>
          <h1>
            {r.demo_mode
              ? "An example, clearly labeled."
              : "A closer look at the call."}
          </h1>
        </div>
      </div>
      {!r.demo_mode && <p className="evaluation-note">These scores describe this recording, not overall model accuracy. <Link className="text-button" href="/#model">View saved validation results <ArrowRight size={14}/></Link></p>}
      <div
        className={`result-notice ${r.demo_mode ? "demo" : ""}`}
        role="status"
      >
        <strong>
          {r.demo_mode
            ? "DEMO RESULT — NOT AN AI PREDICTION"
            : "MODEL INFERENCE"}
        </strong>
        <p>{r.notice}</p>
      </div>
      <div className="results-grid">
        <section className="prediction-card">
          <Bird size={76} strokeWidth={1} />
          <p className="eyebrow">
            {r.demo_mode ? "EXAMPLE SPECIES" : "PREDICTED SPECIES"}
          </p>
          <h2>{r.prediction.species}</h2>
          <div className="big-score">
            {(r.prediction.confidence * 100).toFixed(1)}
            <span>%</span>
          </div>
          <p>
            {r.demo_mode
              ? "Illustrative confidence · not measured"
              : "Model confidence score"}
          </p>
        </section>
        <section className="ranking-card">
          <h3>
            {r.demo_mode ? "Top three example scores" : "Top three predictions"}
          </h3>
          {r.top_three.map((p, i) => (
            <div className="ranking" key={p.label}>
              <div>
                <span>
                  {String(i + 1).padStart(2, "0")} &nbsp; {p.species}
                </span>
                <strong>{(p.confidence * 100).toFixed(1)}%</strong>
              </div>
              <div className="bar">
                <span style={{ width: `${p.confidence * 100}%` }} />
              </div>
            </div>
          ))}
          <dl>
            <div>
              <dt>Model</dt>
              <dd>{r.model_name}</dd>
            </div>
            <div>
              <dt>Processed audio</dt>
              <dd>16 kHz · Mono · {r.audio.duration_seconds.toFixed(2)} s</dd>
            </div>
            <div>
              <dt>Mode</dt>
              <dd>
                {r.demo_mode
                  ? "Deterministic demo"
                  : "Local checkpoint inference"}
              </dd>
            </div>
          </dl>
        </section>
      </div>
      {file && <AudioPreview file={file} />}
      <Link className="button primary" href="/#listen">
        Explore another recording <ArrowRight size={18} />
      </Link>
    </main>
  );
}
