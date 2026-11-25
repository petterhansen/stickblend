import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, interpolate, OffthreadVideo } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import tl from "./timeline.de.json";
const { fontFamily } = loadFont("normal", { weights: ["700", "900"], subsets: ["latin", "latin-ext"] });

const FPS = 30;
type W = { w: string; s: number; e: number; line: string };
const WORDS: W[] = tl.lines.flatMap((l) => l.words.map((w) => ({ ...w, line: l.id })));
const norm = (s: string) => s.toLowerCase().replace(/[^a-zäöüß0-9]/g, "");
const wt = (needle: string, nth = 0, line?: string, end = false) => {
  const m = WORDS.filter((w) => norm(w.w).startsWith(norm(needle)) && (!line || w.line === line));
  return m[nth] ? (end ? m[nth].e : m[nth].s) : 0;
};
export const END_T = WORDS[WORDS.length - 1].e + 0.22;
export const NFR = Math.round(END_T * FPS);
const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));
const lin = (t: number, a: number, b: number) => clamp((t - a) / (b - a), 0, 1);
const ss = (k: number) => { const x = clamp(k, 0, 1); return x * x * (3 - 2 * x); };

// ---- Zeitmarken (wie blender/shots.py)
const T_X = wt("kurz") - 0.25, T_FZ = wt("aber") - 0.05, T_RW0 = wt("passiert") - 0.5, T_RW1 = wt("über") - 0.12;
const K_REISS = wt("reißen"), T_TRIP = wt("fliehkraftregler") + 0.65, T_WEDGE = wt("rammt") + 0.1, T_STOP = wt("schienen") + 0.3;
const T_H = wt("nur", 0, "history") - 0.12, K_RAST = wt("rast"), T_IMP = wt("building") + 0.05, K_STURZ = wt("stürzt"), T_LAND = wt("überlebt") + 0.05;
const T_L = wt("also", 0, "loop") - 0.22, T_PRESS = wt("drückst") + 0.25;
const K275 = wt("zweihundertfünfundsiebzig"), K265 = wt("zweihundertfünfundsechzig"), K_FLACH = wt("flach"), K_METER = wt("einen", 0, "twist");
const Z80 = 79 * 3.6, ZP = -1.8 + 0.9 + 0.23;
const czH = (t: number) => Z80 + (ZP - Z80) * ss(Math.pow(lin(t, K_STURZ, T_LAND), 1.6));

// ---- Untertitel: 2-4 Woerter, Satzzeichen bleiben, Zahlen als Ziffern
const NUM: [RegExp, string][] = [[/^achtzigsten/i, "80."], [/^achtzig$/i, "80"], [/^acht$/i, "8"], [/^zweihundertfünfundsiebzig/i, "275"], [/^zweihundertfünfundsechzig/i, "265"],
  [/^fünfundsiebzig/i, "75"], [/^stundenkilometern/i, "km/h"]];
const disp = (w: string, next?: string) => {
  let x = w.replace(/–/g, "").trim();
  const lead = x.match(/^[„"]/)?.[0] ?? ""; let core = x.slice(lead.length);
  for (const [re, d] of NUM) core = core.replace(re, d);
  if (/^einen$/i.test(core) && next && /^meter/i.test(next)) core = "1";
  return lead + core;
};
const up = (s: string) => s.replace(/ß/g, "ẞ").toUpperCase();
type Grp = { txt: string; s: number; e: number; line: string };
const noBreak = (a: string, b: string) => /^(empire|state|betty|lou|achtzigsten|im)$/i.test(a) || (/^einen$/i.test(a) && /^meter/i.test(b));
const GROUPS: Grp[] = (() => {
  const out: Grp[] = [];
  const ws = WORDS.filter((w) => norm(w.w));
  let cur: W[] = [];
  const flush = () => { if (cur.length) out.push({ txt: cur.map((w) => disp(w.w, ws[ws.indexOf(w) + 1]?.w)).join(" "), s: cur[0].s, e: cur[cur.length - 1].e, line: cur[0].line }); cur = []; };
  ws.forEach((w, i) => {
    const nx = ws[i + 1];
    cur.push(w);
    const len = cur.map((x) => disp(x.w)).join(" ").length;
    const clause = /[.,:;!?“]$/.test(w.w);
    const gap = nx ? nx.s - w.e > 0.32 : true;
    const nlen = nx ? len + 1 + disp(nx.w).length : 99;
    const hard = !nx || nx.line !== w.line || clause || gap;
    if (hard || (!noBreak(w.w, nx.w) && (cur.length >= 4 || nlen > 22))) flush();
  });
  flush();
  const m: Grp[] = [];
  for (const g of out) {
    const p = m[m.length - 1];
    if (p && !g.txt.includes(" ") && g.txt.length <= 7 && /[.,:;!?“]$/.test(g.txt) && p.line === g.line && g.s - p.e < 0.32 && !/[.,:;!?“]$/.test(p.txt) && (p.txt + " " + g.txt).length <= 26)
      { p.txt += " " + g.txt; p.e = g.e; } else m.push({ ...g });
  }
  return m;
})();
const CAP = { x0: 70, x1: 860, yc: 1290 };   // Safe-Zone-Box (stickblend/assets/safezone.json)
const wrap = (s: string, max = 13) => {
  const words = s.split(" "); const lines: string[] = []; let l = "";
  for (const w of words) { if (l && (l + " " + w).length > max) { lines.push(l); l = w; } else l = l ? l + " " + w : w; }
  if (l) lines.push(l);
  return lines;
};
const Caption: React.FC<{ t: number }> = ({ t }) => {
  let g = -1; GROUPS.forEach((x, k) => { if (t >= x.s - 0.03) g = k; });
  if (g < 0) return null;
  const G = GROUPS[g]; const next = GROUPS[g + 1];
  if (t > G.e + 0.5 && (!next || t < next.s - 0.03)) return null;
  const k = Math.min(1, (t - G.s + 0.03) / 0.08);
  const lines = wrap(up(G.txt));
  const longest = Math.max(...lines.map((l) => l.length));
  const size = Math.min(92, (CAP.x1 - CAP.x0) / (0.74 * Math.max(8, longest)));
  const top = CAP.yc - size * 0.54 * lines.length;
  return (
    <div style={{ position: "absolute", left: CAP.x0, width: CAP.x1 - CAP.x0, top, textAlign: "center", fontFamily, fontWeight: 900, fontSize: size, color: "#FFFFFF",
      WebkitTextStroke: `${size * 0.16}px #000`, paintOrder: "stroke fill", letterSpacing: 1, transform: `scale(${0.92 + 0.08 * k})`,
      textShadow: "0 6px 0 rgba(0,0,0,0.35)", lineHeight: 1.08 }}>{lines.map((l, i) => <div key={i}>{l}</div>)}</div>
  );
};

// ---- Zaehler oben links (Safe-Zone: unter der Notch-Hoehe, links der Mitte)
const fmt1 = (x: number) => x.toFixed(1).replace(".", ",");
type Hud = { label: string; value: string; color: string; strike?: string } | null;
const hudAt = (t: number): Hud => {
  const remain = (u: number) => Math.max(0, 8 * (1 - u / (T_FZ + 0.95)));
  if (t < K275 - 0.1) return { label: "BIS ZUM AUFPRALL", value: `${fmt1(remain(t))} s`, color: "#ff3b30" };
  if (t < K_FLACH - 0.2) return t < K265 ? { label: "AUFPRALL", value: "275 km/h", color: "#ff3b30" } : { label: "MIT SPRUNG", value: "265 km/h", color: "#ff3b30", strike: "275" };
  if (t < T_FZ) return { label: "BIS ZUM AUFPRALL", value: `${fmt1(remain(t))} s`, color: "#ff3b30" };
  if (t < T_RW0) return { label: "BIS ZUM AUFPRALL", value: `${fmt1(remain(T_FZ))} s`, color: "#ffffff" };
  if (t < T_RW1) return { label: "◀◀ ZURÜCK", value: `${fmt1(remain(T_FZ) + (8 - remain(T_FZ)) * ss(lin(t, T_RW0, T_RW1)))} s`, color: "#7fe8ff" };
  if (t < K_REISS) return null;
  if (t < K_METER - 0.1) return { label: "FALLHÖHE", value: `${fmt1(Math.min(1, ss(lin(t, K_REISS + 0.2, T_STOP))))} m`, color: "#ffd60a" };
  if (t < T_H - 0.3) return { label: "FALLHÖHE", value: "1,0 m", color: "#34c759" };
  if (t >= K_STURZ - 0.1 && t < T_LAND + 0.4) return { label: "STOCKWERK", value: `${clamp(Math.round(czH(t) / 3.6) + 1, 1, 80)}`, color: "#ff3b30" };
  return null;
};
const HudBox: React.FC<{ t: number }> = ({ t }) => {
  const h = hudAt(t); if (!h) return null;
  // kurzer Pop, wenn sich das Label aendert
  const prevLabel = hudAt(t - 0.12)?.label; const pop = prevLabel !== h.label ? 1.12 : 1.0;
  const blinkFz = t >= T_FZ && t < T_RW0 && Math.floor(t * 4) % 2 === 1 ? 0.35 : 1;
  return (
    <div style={{ position: "absolute", left: 60, top: 232, transform: `scale(${pop})`, transformOrigin: "left top", opacity: blinkFz,
      background: "rgba(10,14,28,0.72)", borderRadius: 22, padding: "14px 26px 16px", borderLeft: `10px solid ${h.color}`, fontFamily }}>
      <div style={{ fontSize: 30, fontWeight: 700, letterSpacing: 2, color: "#e8ecf4" }}>{h.label}</div>
      {h.strike && <div style={{ fontSize: 40, fontWeight: 900, color: "#9aa3b5", textDecoration: "line-through", lineHeight: 1 }}>{h.strike} km/h</div>}
      <div style={{ fontSize: 84, fontWeight: 900, color: h.color, lineHeight: 1.0, fontVariantNumeric: "tabular-nums" }}>{h.value}</div>
    </div>
  );
};

// ---- Karten (1945 / Betty)
const Card: React.FC<{ t: number }> = ({ t }) => {
  const k1945 = wt("1945");
  let c: { a: string; b: string; col: string } | null = null; let t0 = 0;
  if (t >= k1945 - 0.1 && t < K_STURZ - 0.15) { c = { a: "28. JULI 1945", b: "NEW YORK · NEBEL", col: "#ffd60a" }; t0 = k1945 - 0.1; }
  if (t >= T_LAND + 0.45 && t < T_L - 0.25) { c = { a: "BETTY LOU OLIVER", b: "75 STOCKWERKE · ÜBERLEBT", col: "#34c759" }; t0 = T_LAND + 0.45; }
  if (!c) return null;
  const k = Math.min(1, (t - t0) / 0.18);
  return (
    <div style={{ position: "absolute", left: 60, width: 960, top: 236, textAlign: "center", fontFamily, transform: `translateY(${(1 - k) * -30}px)`, opacity: k }}>
      <div style={{ display: "inline-block", background: "rgba(10,14,28,0.75)", borderRadius: 24, padding: "16px 34px", borderBottom: `8px solid ${c.col}` }}>
        <div style={{ fontSize: 66, fontWeight: 900, color: "#fff", letterSpacing: 2 }}>{c.a}</div>
        <div style={{ fontSize: 36, fontWeight: 700, color: c.col, letterSpacing: 3 }}>{c.b}</div>
      </div>
    </div>
  );
};

// ---- Ton
type Cue = { s: string; at: number; v: number; dur?: number; fin?: number; fout?: number };
const CUES: Cue[] = [
  { s: "sfx/twang", at: 0, v: 0.9 },
  { s: "sfx/alarm", at: 0.05, v: 0.22, dur: 6.0, fout: 1.5 },
  { s: "sfx/fall_rush", at: 0, v: 0.32, dur: T_FZ, fout: 0.05 },
  { s: "sfx/whoosh", at: T_X, v: 0.4 },
  { s: "sfx/sparks", at: T_X + 0.6, v: 0.25 }, { s: "sfx/sparks", at: T_X + 4.0, v: 0.22 }, { s: "sfx/sparks", at: T_X + 7.5, v: 0.22 },
  { s: "sfx/pop", at: K275 - 0.1, v: 0.5 }, { s: "sfx/metal_hit", at: K265, v: 0.35 }, { s: "sfx/pop", at: K_FLACH - 0.2, v: 0.5 },
  { s: "sfx/impact", at: T_FZ, v: 0.5 },
  { s: "sfx/tick", at: T_FZ + 0.05, v: 0.6, dur: T_RW0 - T_FZ },
  { s: "sfx/rewind", at: T_RW0 - 0.1, v: 0.65 },
  { s: "sfx/metal_hit", at: T_RW1, v: 0.4 },
  { s: "sfx/twang", at: K_REISS + 0.12, v: 0.7 }, { s: "sfx/twang", at: K_REISS + 0.3, v: 0.45 },
  { s: "sfx/ratchet", at: wt("fliehkraftregler") - 0.1, v: 0.7 },
  { s: "sfx/brake_screech", at: T_WEDGE - 0.05, v: 0.6 },
  { s: "sfx/sparks", at: T_WEDGE, v: 0.4 },
  { s: "sfx/pop", at: K_METER - 0.1, v: 0.5 },
  { s: "sfx/whoosh", at: T_H - 0.55, v: 0.45 },
  { s: "sfx/plane", at: T_IMP - 4.0, v: 0.55, dur: 4.05, fout: 0.05 },
  { s: "sfx/explosion", at: T_IMP, v: 0.8 }, { s: "sfx/impact", at: T_IMP, v: 0.7 },
  { s: "sfx/whoosh", at: wt("die", 0, "history") - 0.4, v: 0.35 },
  { s: "sfx/twang", at: K_STURZ - 0.1, v: 0.5 },
  { s: "sfx/fall_rush", at: K_STURZ, v: 0.35, dur: T_LAND - K_STURZ + 0.1, fout: 0.3 },
  { s: "sfx/air_press", at: T_LAND - 1.6, v: 0.4, dur: 1.7, fout: 0.1 },
  { s: "sfx/thud", at: T_LAND - 0.02, v: 0.85 },
  { s: "sfx/ding", at: T_L + 0.15, v: 0.35 },
  { s: "sfx/button_click", at: T_PRESS - 0.03, v: 0.9 },
  { s: "sfx/doors_close", at: T_PRESS + 0.15, v: 0.5 },
  // Musik
  { s: "audio/music_tension", at: 0, v: 0.12, dur: T_FZ, fout: 0.03 },
  { s: "audio/music_calm", at: T_RW1, v: 0.12, dur: T_H - T_RW1 + 0.2, fin: 0.3, fout: 0.5 },
  { s: "audio/music_serious", at: T_H - 0.1, v: 0.14, dur: T_L - T_H + 0.5, fin: 0.6, fout: 0.4 },
];
const CueAudio: React.FC<{ c: Cue }> = ({ c }) => {
  const dur = c.dur ?? 30;
  return (
    <Sequence from={Math.max(0, Math.round(c.at * FPS))} durationInFrames={Math.max(1, Math.round(dur * FPS))}>
      <Audio src={staticFile(`${c.s}.wav`)} volume={(f) => {
        const t = f / FPS; const fi = c.fin ? Math.min(1, t / c.fin) : 1; const fo = c.fout && c.dur ? Math.min(1, Math.max(0, (dur - t) / c.fout)) : 1;
        return c.v * fi * fo;
      }} />
    </Sequence>
  );
};

export const Short: React.FC = () => {
  const f = useCurrentFrame(); const t = f / FPS;
  const frozen = t >= T_FZ && t < T_RW0; const rew = t >= T_RW0 && t < T_RW1;
  const filt = frozen ? "saturate(0.25) contrast(1.15)" : rew ? `saturate(0.6) hue-rotate(${Math.sin(t * 40) * 12}deg)` : "none";
  const flash = Math.max(interpolate(t, [T_FZ, T_FZ + 0.15], [0.8, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) * (t >= T_FZ ? 1 : 0),
    interpolate(t, [T_IMP, T_IMP + 0.25], [0.7, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) * (t >= T_IMP ? 1 : 0));
  const fog = interpolate(t, [T_H - 0.45, T_H, T_H + 0.6], [0, 0.85, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const dust = interpolate(t, [T_L - 0.3, T_L, T_L + 0.45], [0, 0.92, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <AbsoluteFill style={{ filter: filt, transform: frozen ? `scale(${1 + 0.03 * lin(t, T_FZ, T_RW0)})` : undefined }}>
        <OffthreadVideo src={staticFile("bl/onetake.mp4")} muted />
      </AbsoluteFill>
      <AbsoluteFill>
        <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute" }}>
          <image href={staticFile("img/grain.png")} x={-((f * 137) % 400)} y={-((f * 71) % 400)} width={2160} height={2160} opacity={0.05} style={{ mixBlendMode: "overlay" }} />
          {rew && Array.from({ length: 14 }, (_, i) => <rect key={i} x={0} y={((i * 151 + f * 47) % 1920)} width={1080} height={6 + (i % 3) * 4} fill="#ffffff" opacity={0.12} />)}
        </svg>
        {flash > 0 && <AbsoluteFill style={{ background: t >= T_IMP ? "#ffd9a0" : "#ffffff", opacity: flash }} />}
        {fog > 0 && <AbsoluteFill style={{ background: "#8ea0bf", opacity: fog }} />}
        {dust > 0 && <AbsoluteFill style={{ background: "radial-gradient(circle at 50% 55%, #f2dcb8, #c9a77c)", opacity: dust }} />}
        <HudBox t={t} />
        <Card t={t} />
        <Caption t={t} />
      </AbsoluteFill>
      <Audio src={staticFile("audio/voice.wav")} />
      {CUES.map((c, i) => <CueAudio key={i} c={c} />)}
    </AbsoluteFill>
  );
};
