"use client";
import { createContext, useContext, useState } from "react";
export type Prediction = { species: string; label: string; confidence: number };
export type Result = {
  demo_mode: boolean;
  notice: string;
  prediction: Prediction;
  top_three: Prediction[];
  model_name: string;
  audio: { sample_rate: number; channels: number; duration_seconds: number };
};
type Session = {
  file: File | null;
  setFile: (v: File | null) => void;
  result: Result | null;
  setResult: (v: Result | null) => void;
};
const Context = createContext<Session | null>(null);
export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  return (
    <Context.Provider value={{ file, setFile, result, setResult }}>
      {children}
    </Context.Provider>
  );
}
export function useSession() {
  return useContext(Context)!;
}
export const API = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
).replace(/\/$/, "");
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    signal: init?.signal ?? AbortSignal.timeout(120000),
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "The request could not be processed.",
    );
  return data;
}
