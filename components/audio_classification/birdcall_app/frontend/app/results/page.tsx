"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/components/session";
import PredictionResult from "@/components/prediction-result";

export default function Results() {
  const { result, file, setResult } = useSession();
  const router = useRouter();
  useEffect(() => {
    if (!result || !file) router.replace("/#listen");
    else window.scrollTo({ top: 0, behavior: "instant" });
  }, [result, file, router]);
  if (!result || !file) return null;
  return (
    <main className="discovery-page">
      <PredictionResult result={result} file={file} onAnother={() => {
        setResult(null);
        router.push("/#listen");
      }} />
    </main>
  );
}
