"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AudioLines,
  ArrowRight,
  CheckCircle,
  TriangleAlert,
} from "lucide-react";
import { api, Result, useSession } from "@/components/session";
export default function Analysis() {
  const { file, result, setResult } = useSession();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const router = useRouter();
  useEffect(() => {
    if (!file) return;
    const controller = new AbortController();
    setError("");
    setResult(null);
    const form = new FormData();
    form.append("file", file);
    const timeout = setTimeout(() => controller.abort("timeout"), 120000);
    api<Result>("/predict", {
      method: "POST",
      body: form,
      signal: controller.signal,
    })
      .then(setResult)
      .catch((e) => {
        if (controller.signal.reason !== "unmount")
          setError(
            controller.signal.aborted
              ? "The server took too long. Please retry."
              : e.message || "Unable to connect to the backend.",
          );
      })
      .finally(() => clearTimeout(timeout));
    return () => {
      clearTimeout(timeout);
      controller.abort("unmount");
    };
  }, [file, attempt, setResult]);
  return (
    <main className="state-page">
      <p className="eyebrow">YOUR RECORDING / ANALYSIS</p>
      <section className="state-card" aria-live="polite">
        {!file ? (
          <>
            <AudioLines size={40} />
            <h1>A recording comes first.</h1>
            <p>
              Choose an audio file to begin. Recordings are cleared when this
              page is refreshed.
            </p>
            <Link className="button primary" href="/#listen">
              Choose a recording
            </Link>
          </>
        ) : error ? (
          <>
            <TriangleAlert size={40} />
            <h1>Let’s try that again.</h1>
            <p className="error" role="alert">
              {error}
            </p>
            <button
              className="button primary"
              onClick={() => setAttempt((v) => v + 1)}
            >
              Retry analysis
            </button>
            <Link className="text-button" href="/#listen">
              Choose another file
            </Link>
          </>
        ) : result ? (
          <>
            <CheckCircle size={44} />
            <p className="pill">
              {result.demo_mode
                ? "DEMO COMPLETE · NOT AI INFERENCE"
                : "ANALYSIS COMPLETE"}
            </p>
            <h1>Your result is ready.</h1>
            <p>{result.notice}</p>
            <button
              className="button primary"
              onClick={() => router.push("/results")}
            >
              Explore results <ArrowRight size={18} />
            </button>
          </>
        ) : (
          <>
            <div className="loading-ring">
              <AudioLines size={40} />
            </div>
            <h1>Listening closer…</h1>
            <p>
              Uploading, validating, and processing your recording.
              <br />
              If demo mode is enabled, only example scores are returned.
            </p>
            <p className="pill">{file.name}</p>
            <Link className="text-button" href="/#listen">
              Cancel and return
            </Link>
          </>
        )}
      </section>
    </main>
  );
}
