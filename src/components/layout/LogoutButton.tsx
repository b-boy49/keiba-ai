"use client";

import { useState } from "react";

export function LogoutButton() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function logout() {
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/auth/logout", { method: "POST", cache: "no-store" });
      if (!response.ok) throw new Error("logout failed");
      window.location.replace("/access");
    } catch {
      setError("ログアウトできませんでした。もう一度お試しください。");
      setBusy(false);
    }
  }
  return <div className="logout-control"><button type="button" className="logout-button" disabled={busy} onClick={logout}>{busy ? "ログアウト中…" : "ログアウト"}</button>{error && <p className="logout-error" role="alert">{error}</p>}</div>;
}
