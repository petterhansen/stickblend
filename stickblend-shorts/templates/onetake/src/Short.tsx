// One-Take-Short in Remotion: Blender-Clip + Untertitel (Safe-Zone) + Zaehler + Karten + Ton-Cues.
// Alle Zeiten haengen an Woertern (wt) wie in blender/shots.py. Vollstaendiges Vorbild: examples/aufzug/src/Short.tsx
// (Freeze, Rueckspulen, Nebel-/Staub-Uebergaenge, mehrere Zaehler-Modi).
import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, interpolate, OffthreadVideo } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import tl from "./timeline.json";
const { fontFamily } = loadFont("normal", { weights: ["700", "900"], subsets: ["latin", "latin-ext"] });

const FPS = 30;
type W = { w: string; s: number; e: number; line: string };
const WORDS: W[] = tl.lines.flatMap((l) => l.words.map((w) => ({ ...w, line: l.id })));
const norm = (s: string) => s.toLowerCase().replace(/[^a-zäöüß0-9]/g, "");
const wt = (needle: string, nth = 0, line?: string, end = false) => {
  const m = WORDS.filter((w) => norm(w.w).startsWith(norm(needle)) && (!line || w.line === line));
  return m[nth] ? (end ? m[nth].e : m[nth].s) : 0;
};
export const END_T = WORDS[WORDS.length - 1].e + 0.22;   // harter Schnitt -> Loop
export const NFR = Math.round(END_T * FPS);
const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

// ---- Zeitmarken (wie shots.py)
const T_B = wt("dann") - 0.1;

// ---- Untertitel (SHORTS-REGELN.md): 2-4 Woerter, Satzzeichen bleiben, Zahlen als Ziffern, ẞ gross, in der Safe-Zone
// CAP: plattformuebergreifend (YouTube + Reels + TikTok) Unterkante <= 1240; nur TikTok: yc 1290 / Unterkante <= 1500.
const CAP = { x0: 70, x1: 860, yc: 1120 };
const NUM: [RegExp, string][] = [[/^zwei$/i, "2"], [/^drei$/i, "3"], [/^zehn$/i, "10"]];   // eigene Zahlwoerter ergaenzen
const disp = (w: string) => { let x = w.replace(/–/g, "").trim(); for (const [re, d] of NUM) x = x.replace(re, d); return x; };
const up = (s: string) => s.replace(/ß/g, "ẞ").toUpperCase();
type Grp = { txt: string; s: number; e: number; line: string };
const noBreak = (a: string) => /^(new|empire|state)$/i.test(a);   // Namen nicht trennen
const GROUPS: Grp[] = (() => {
  const out: Grp[] = []; const ws = WORDS.filter((w) => norm(w.w)); let cur: W[] = [];
  const flush = () => { if (cur.length) out.push({ txt: cur.map((w) => disp(w.w)).join(" "), s: cur[0].s, e: cur[cur.length - 1].e, line: cur[0].line }); cur = []; };
  ws.forEach((w, i) => {
    const nx = ws[i + 1]; cur.push(w);
    const len = cur.map((x) => disp(x.w)).join(" ").length;
    const hard = !nx || nx.line !== w.line || /[.,:;!?“]$/.test(w.w) || nx.s - w.e > 0.32;
    if (hard || (!noBreak(w.w) && (cur.length >= 4 || len + 1 + disp(nx.w).length > 22))) flush();
  });
  flush(); return out;
})();
const wrap = (s: string, max = 13) => { const L: string[] = []; let l = ""; for (const w of s.split(" ")) { if (l && (l + " " + w).length > max) { L.push(l); l = w; } else l = l ? l + " " + w : w; } if (l) L.push(l); return L; };
const Caption: React.FC<{ t: number }> = ({ t }) => {
  let g = -1; GROUPS.forEach((x, k) => { if (t >= x.s - 0.03) g = k; });
  if (g < 0) return null;
  const G = GROUPS[g]; const next = GROUPS[g + 1];
  if (t > G.e + 0.5 && (!next || t < next.s - 0.03)) return null;
  const k = Math.min(1, (t - G.s + 0.03) / 0.08); const lines = wrap(up(G.txt));
  const size = Math.min(92, (CAP.x1 - CAP.x0) / (0.74 * Math.max(8, ...lines.map((l) => l.length))));
  return (
    <div style={{ position: "absolute", left: CAP.x0, width: CAP.x1 - CAP.x0, top: CAP.yc - size * 0.54 * lines.length, textAlign: "center", fontFamily, fontWeight: 900,
      fontSize: size, color: "#fff", WebkitTextStroke: `${size * 0.16}px #000`, paintOrder: "stroke fill", transform: `scale(${0.92 + 0.08 * k})`,
      textShadow: "0 6px 0 rgba(0,0,0,0.35)", lineHeight: 1.08 }}>{lines.map((l, i) => <div key={i}>{l}</div>)}</div>
  );
};

// ---- Zaehler oben links (ab 0,0 s: erzeugt Druck). Position: unter der Notch-Hoehe, links der Mitte.
const hudAt = (t: number): { label: string; value: string; color: string } | null =>
  t < T_B ? { label: "NOCH", value: `${Math.max(0, T_B - t).toFixed(1).replace(".", ",")} s`, color: "#ff3b30" } : null;
// Stil: kein Kasten, keine Flaeche -- dieselbe fette Schrift wie die Untertitel, nur schwarze Kontur + harter Schlagschatten.
const ink = (px: number) => ({ WebkitTextStroke: `${px}px #000`, paintOrder: "stroke fill" as const, textShadow: `${px * 0.7}px ${px * 0.7}px 0 #000` });
const Hud: React.FC<{ t: number }> = ({ t }) => {
  const h = hudAt(t); if (!h) return null;
  return (
    <div style={{ position: "absolute", left: 66, top: 236, fontFamily, fontWeight: 900, lineHeight: 1 }}>
      <div style={{ fontSize: 36, letterSpacing: 3, color: "#fff", ...ink(9) }}>{h.label}</div>
      <div style={{ fontSize: 132, color: h.color, marginTop: 4, fontVariantNumeric: "tabular-nums", letterSpacing: -1, ...ink(18) }}>{h.value}</div>
    </div>
  );
};

// ---- Doku-Bauchbinde (Datum/Ort/Person): scharfkantiger gelber Balken + weisser Balken darunter, leicht versetzt.
// Bewusst anders als der Zaehler, damit es nicht nach UI/KI-Badge aussieht. Nie gleichzeitig mit dem Zaehler zeigen (gleiche Ecke).
const ss = (k: number) => { const x = clamp(k, 0, 1); return x * x * (3 - 2 * x); };
const LOWER: { a: string; b: string; t0: number; t1: number }[] = [
  { a: "RAUM 2", b: "HINTER DER TÜR", t0: T_B + 0.2, t1: END_T - 0.3 },   // Beispiel: eigene Eintraege an Woerter binden
];
const LowerThird: React.FC<{ t: number }> = ({ t }) => {
  const c = LOWER.find((x) => t >= x.t0 && t < x.t1); if (!c) return null;
  const wipe = (d: number) => ss((t - c.t0 - d) / 0.22) * ss((c.t1 - t) / 0.15);   // von links herein, am Ende schnell raus
  const bar = { position: "relative" as const, display: "inline-block", fontFamily, fontWeight: 900, lineHeight: 1, boxShadow: "8px 8px 0 rgba(0,0,0,0.85)" };
  return (
    <div style={{ position: "absolute", left: 62, top: 250 }}>
      <div style={{ ...bar, background: "#ffd60a", color: "#000", fontSize: 72, letterSpacing: 1, padding: "16px 26px 14px", clipPath: `inset(-20px ${100 - 100 * wipe(0)}% -20px -20px)` }}>{c.a}</div>
      <div style={{ height: 0 }} />
      <div style={{ ...bar, left: 46, marginTop: -4, background: "#fff", color: "#000", fontSize: 38, fontWeight: 800, letterSpacing: 4, padding: "12px 22px 11px", clipPath: `inset(-20px ${100 - 100 * wipe(0.12)}% -20px -20px)` }}>{c.b}</div>
    </div>
  );
};

// ---- Ton-Cues (an Woerter gebunden). Dateien: python scripts/audio.py
type Cue = { s: string; at: number; v: number; dur?: number; fin?: number; fout?: number };
const CUES: Cue[] = [
  { s: "sfx/impact", at: 0, v: 0.7 },                                     // Ton-Treffer auf Frame 1
  { s: "sfx/whoosh", at: T_B - 0.4, v: 0.4 },
  { s: "audio/music_tension", at: 0, v: 0.12, dur: T_B, fout: 0.05 },    // harter Drop am Wendepunkt
  { s: "audio/music_calm", at: T_B, v: 0.12, dur: END_T - T_B, fin: 0.3, fout: 0.3 },
];
const CueAudio: React.FC<{ c: Cue }> = ({ c }) => {
  const dur = c.dur ?? 30;
  return (
    <Sequence from={Math.max(0, Math.round(c.at * FPS))} durationInFrames={Math.max(1, Math.round(dur * FPS))}>
      <Audio src={staticFile(`${c.s}.wav`)} volume={(f) => { const t = f / FPS; const fi = c.fin ? Math.min(1, t / c.fin) : 1; const fo = c.fout && c.dur ? clamp((dur - t) / c.fout, 0, 1) : 1; return c.v * fi * fo; }} />
    </Sequence>
  );
};

export const Short: React.FC = () => {
  const f = useCurrentFrame(); const t = f / FPS;
  const flash = t >= T_B ? interpolate(t, [T_B, T_B + 0.15], [0.5, 0], { extrapolateRight: "clamp" }) : 0;
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <OffthreadVideo src={staticFile("bl/onetake.mp4")} muted />
      <AbsoluteFill>
        <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute" }}>
          <image href={staticFile("img/grain.png")} x={-((f * 137) % 400)} y={-((f * 71) % 400)} width={2160} height={2160} opacity={0.05} style={{ mixBlendMode: "overlay" }} />
        </svg>
        {flash > 0 && <AbsoluteFill style={{ background: "#fff", opacity: flash }} />}
        <Hud t={t} />
        <LowerThird t={t} />
        <Caption t={t} />
      </AbsoluteFill>
      <Audio src={staticFile("audio/voice.wav")} />
      {CUES.map((c, i) => <CueAudio key={i} c={c} />)}
    </AbsoluteFill>
  );
};
