"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bird,
  Upload,
  ArrowRight,
  AudioLines,
  Leaf,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import { api, useSession } from "@/components/session";
import AudioPreview from "@/components/audio-preview";
import ModelReport from "@/components/model-report";
type Species = { id: number; label: string; name: string };
type Health = { demo_mode: boolean; ready: boolean; message: string };
export default function Home() {
  const { file, setFile, setResult } = useSession();
  const router = useRouter();
  const [species, setSpecies] = useState<Species[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [drag, setDrag] = useState(false);
  function connect() {
    setConnectionError("");
    Promise.all([
      api<{ species: Species[] }>("/species"),
      api<Health>("/health"),
    ])
      .then(([s, h]) => {
        setSpecies(s.species);
        setHealth(h);
      })
      .catch(() => {
        setHealth(null);
        setConnectionError(
          "Cannot reach the research server. Start FastAPI on port 8000, then retry.",
        );
      });
  }
  useEffect(() => {
    connect();
    const refresh = window.setInterval(connect, 15000);
    window.addEventListener("focus", connect);
    return () => {
      window.clearInterval(refresh);
      window.removeEventListener("focus", connect);
    };
  }, []);
  function select(f?: File) {
    if (!f) return;
    setError("");
    setFile(null);
    setResult(null);
    if (!/\.(wav|mp3|m4a)$/i.test(f.name)) {
      setError("Please select a WAV, MP3, or M4A recording.");
      return;
    }
    if (f.size === 0 || f.size > 20 * 1024 * 1024) {
      setError("Choose a non-empty recording up to 20 MB.");
      return;
    }
    setFile(f);
  }
  return (
    <main>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">
            <span /> BIOACOUSTICS · SRI LANKA
          </p>
          <h1>
            Every call tells
            <br />a <em>wild story.</em>
          </h1>
          <p className="intro">
            Listen beyond the noise. Explore ten Sri Lankan bird species with
            your trained Wav2Vec2 model, and discover the validation results behind it.
          </p>
          <a className="button gold" href="#listen">
            Explore your recording <ArrowRight size={18} />
          </a>
          <div className="hero-stats">
            <div>
              <strong>10</strong>
              <span>dataset species</span>
            </div>
            <div>
              <strong>16 kHz</strong>
              <span>audio processing</span>
            </div>
            <div>
              <strong>02</strong>
              <span>research component</span>
            </div>
          </div>
        </div>
        <div className="forest-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="moon" />
          <Leaf className="leaf leaf-one" />
          <Leaf className="leaf leaf-two" />
          <Bird className="hero-bird" strokeWidth={0.7} />
          <div className="art-caption">
            <AudioLines size={25} />
            <span>
              THE FOREST HAS A VOICE<small>A closer listen begins here.</small>
            </span>
          </div>
          <span className="art-coordinate">
            7° N / 81° E &nbsp; • &nbsp; SRI LANKA
          </span>
        </div>
      </section>
      <section id="listen" className="listen-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">01 / LISTEN & DISCOVER</p>
            <h2>Bring the forest into focus.</h2>
          </div>
          <p>
            Upload a short field recording.
            <br />
            We’ll take it from sound to species.
          </p>
        </div>
        <div className="workspace">
          <div className="upload-card">
            <div className="card-heading">
              <h3>Your recording</h3>
              <span className="pill">WAV · MP3 · M4A</span>
            </div>
            <label
              className={`dropzone ${drag ? "dragging" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDrag(false);
                select(e.dataTransfer.files[0]);
              }}
            >
              <input
                type="file"
                accept=".wav,.mp3,.m4a"
                onChange={(e) => select(e.target.files?.[0])}
              />
              <span className="upload-icon">
                <Upload size={25} />
              </span>
              <strong>
                {file
                  ? "Choose a different recording"
                  : "Drop your bird recording here"}
              </strong>
              <span>
                or <u>browse files</u> on your device
              </span>
              <small>Up to 20 MB · 0.1–60 seconds</small>
            </label>
            {file && <AudioPreview file={file} />}{" "}
            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}
            <button
              className="button primary full"
              disabled={!file || !health?.ready}
              aria-describedby="analysis-readiness"
              onClick={() => router.push("/analysis")}
            >
              {health?.demo_mode ? "Run demo analysis" : "Analyze recording"}
              <ArrowRight size={18} />
            </button>
            <p id="analysis-readiness" className="readiness-note" role="status">
              {!health ? "Waiting for the backend. Start FastAPI and use Check readiness below."
                : !health.ready ? "Analysis is unavailable until the model loads. See the server message and check readiness again."
                : !file ? "Model ready. Choose a recording to enable analysis."
                : health.demo_mode ? "Demo mode is active: results will be examples, not trained-model predictions."
                : "Trained model ready. Your recording will use real inference."}
            </p>
            <p className="privacy">
              <ShieldCheck size={14} /> Recordings are not retained after
              processing.
            </p>
          </div>
          <aside className="guide-card">
            <p className="eyebrow">RESEARCH, WITH TRANSPARENCY</p>
            <h3>
              A small recording.
              <br />A deeper understanding.
            </h3>
            <div
              className={`mode ${health?.demo_mode ? "demo" : ""}`}
              role="status"
            >
              <span className="status-dot" />
              {health
                ? health.demo_mode
                  ? "DEMO MODE ENABLED"
                  : health.ready
                    ? "TRAINED MODEL READY"
                    : "MODEL NOT READY"
                : "SERVER NOT CONNECTED"}
            </div>
            <p>
              {health?.message ||
                "Connect to the backend to check model availability."}
            </p>
            {connectionError && (
              <div role="alert">
                <p className="error">{connectionError}</p>
                <button className="text-button" onClick={connect}>
                  <RefreshCw size={14} /> Retry connection
                </button>
              </div>
            )}
            {!connectionError && <button className="text-button" onClick={connect}>
              <RefreshCw size={14} /> Check readiness
            </button>}
            <div className="guide-step">
              <span>01</span>
              <div>
                <strong>Upload & listen</strong>
                <p>Preview your recording and its waveform.</p>
              </div>
            </div>
            <div className="guide-step">
              <span>02</span>
              <div>
                <strong>Prepare the audio</strong>
                <p>Decode, mix to mono, and resample to 16 kHz.</p>
              </div>
            </div>
            <div className="guide-step">
              <span>03</span>
              <div>
                <strong>Explore the result</strong>
                <p>Compare three ranked species and their scores.</p>
              </div>
            </div>
            <p className="research-note">
              Wav2Vec2 training results are available below. Validation performance
              does not establish robustness to every recording condition.
            </p>
          </aside>
        </div>
      </section>
      <section id="species" className="species-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">02 / THE DATASET</p>
            <h2>Ten voices. One island.</h2>
          </div>
          <p>
            Species names read directly from
            <br />
            the Component 02 label mapping.
          </p>
        </div>
        <div className="species-grid">
          {species.map((s) => (
            <article className="species-card" key={s.id}>
              <div>
                <Bird size={25} strokeWidth={1.3} />
                <span>{String(s.id + 1).padStart(2, "0")}</span>
              </div>
              <h3>{s.name}</h3>
              <p>Component 02 dataset</p>
            </article>
          ))}
        </div>
        {!species.length && (
          <p className="muted">
            {connectionError || "Loading the dataset species…"}
          </p>
        )}
      </section>
      <ModelReport />
      <section className="project-note">
        <Leaf size={28} />
        <div>
          <p className="eyebrow">ABOUT THE RESEARCH</p>
          <h3>
            Noise-Robust Bioacoustic Bird Call Recognition for Sri Lankan
            Endemic Birds
          </h3>
          <p>
            Component 02 investigates recognition of bird vocalizations in noisy
            recordings. This interface connects the finalized Wav2Vec2 checkpoint
            and its saved validation report. AST remains a separate research run.
            Demo scores, when explicitly enabled, are not research findings.
          </p>
        </div>
      </section>
    </main>
  );
}
