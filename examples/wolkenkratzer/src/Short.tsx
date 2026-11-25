import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, interpolate, OffthreadVideo } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import tl from "./timeline.de.json";
const { fontFamily } = loadFont("normal", { weights: ["900"], subsets: ["latin", "latin-ext"] });

const FPS = 30;
type W = { w: string; s: number; e: number; line: string };
const WORDS: W[] = tl.lines.flatMap((l) => l.words.map((w) => ({ ...w, line: l.id })));
const norm = (s: string) => s.toLowerCase().replace(/[^a-zäöüß0-9]/g, "");
const wt = (needle: string, nth = 0, line?: string, end = false) => {
  const m = WORDS.filter((w) => norm(w.w).startsWith(norm(needle)) && (!line || w.line === line));
  return m[nth] ? (end ? m[nth].e : m[nth].s) : 0;
};
export const END_T = WORDS[WORDS.length - 1].e + 0.22;   // harter Schnitt nach dem letzten Wort
export const NFR = Math.round(END_T * FPS);

// ---- Untertitel: 2-4 Woerter, Satzzeichen bleiben, Zahlen als Ziffern, weiss mit dicker schwarzer Kontur
const NUM: [RegExp, string][] = [[/^fünfzehn/i, "15"], [/^dreißig/i, "30"], [/^sechsundvierzig/i, "46"], [/^fünfzig/i, "50"]];
const disp = (w: string, next?: string) => {
  let x = w.replace(/–/g, "").trim();
  const lead = x.match(/^[„"]/)?.[0] ?? ""; let core = x.slice(lead.length);
  for (const [re, d] of NUM) core = core.replace(re, d);
  if (/^eine$/i.test(core) && next && /^million/i.test(next)) core = "1";
  return lead + core;
};
const up = (s: string) => s.replace(/ß/g, "ẞ").toUpperCase();
type Grp = { txt: string; s: number; e: number; line: string };
const noBreak = (a: string, b: string) => /^new$/i.test(a) || (/^eine$/i.test(a) && /^million/i.test(b));
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
  // einzelne kurze Satzenden ("AB.", "SICH,") an die vorige Gruppe haengen
  const m: Grp[] = [];
  for (const g of out) {
    const p = m[m.length - 1];
    if (p && !g.txt.includes(" ") && g.txt.length <= 7 && /[.,:;!?“]$/.test(g.txt) && p.line === g.line && g.s - p.e < 0.32 && !/[.,:;!?“]$/.test(p.txt) && (p.txt + " " + g.txt).length <= 26)
      { p.txt += " " + g.txt; p.e = g.e; } else m.push({ ...g });
  }
  return m;
})();
// Safe-Zone (stickblend/assets/safezone.json): Untertitel nur in x 70-860, y 980-1500 (links der Button-Leiste, ueber Titel/Beschreibung)
const CAP = { x0: 70, x1: 860, yc: 1290 };
const wrap = (s: string, max = 13) => {
  const words = s.split(" "); const lines: string[] = []; let l = "";
  for (const w of words) { if (l && (l + " " + w).length > max) { lines.push(l); l = w; } else l = l ? l + " " + w : w; }
  if (l) lines.push(l);
  if (lines.length === 1 && lines[0].length > 16 && lines[0].includes("-")) {   // lange Bindestrich-Woerter zweizeilig
    const t = lines[0]; const mid = t.length / 2; let best = -1;
    [...t].forEach((ch, i) => { if (ch === "-" && (best < 0 || Math.abs(i - mid) < Math.abs(best - mid))) best = i; });
    return [t.slice(0, best + 1), t.slice(best + 1)];
  }
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

// ---- Ton (Grenzen wie in shots.py an Woerter gebunden)
const T_A1 = wt("lift") - 0.14, T_B1 = wt("du", 0, "cavern") + 0.27, T_C1 = wt("klingt") - 0.18, T_D1 = wt("die", 0, "penthouse") - 0.15;
const D_T = Array.from({ length: 6 }, (_, i) => wt("also") + 0.5 + i * 1.12);
const t_press = wt("sechsundvierzig") + 0.78, t_stamp = wt("stempel"), t_open = wt("öffnet"), t_doch = wt("doch");
type Cue = { s: string; at: number; v: number; dur?: number; fin?: number; fout?: number };
const CUES: Cue[] = [
  { s: "sfx/elevator_hum", at: 0, v: 0.12, dur: T_B1, fout: 0.6 },
  { s: "sfx/button_click", at: t_press - 0.05, v: 1.0 },
  { s: "sfx/button_beep", at: t_press + 0.02, v: 0.35 },
  { s: "sfx/doors_close", at: wt("gleiten") + 0.55, v: 0.5 },
  ...[T_A1, T_C1, T_D1].map((x) => ({ s: "sfx/whoosh", at: x - 0.45, v: 0.35 })),
  { s: "sfx/shaft_rush", at: T_A1, v: 0.3, dur: T_B1 - T_A1 + 0.3, fout: 0.3 },
  // Drop: Gitter oeffnet in die Leere
  { s: "sfx/impact", at: T_B1 - 0.05, v: 0.75 },
  { s: "sfx/cavern_wind", at: T_B1 - 0.2, v: 0.3, dur: T_C1 - T_B1 + 0.4, fin: 0.4, fout: 0.4 },
  { s: "sfx/wind_gust", at: wt("pfeifender") - 0.3, v: 0.5 },
  { s: "sfx/pipe_tap", at: wt("klopft") + 0.08, v: 1.0 },
  { s: "sfx/stamp", at: t_stamp - 0.02, v: 1.0 },
  { s: "sfx/impact", at: t_stamp - 0.02, v: 0.4 },
  { s: "sfx/city_distant", at: T_C1, v: 0.1, dur: T_D1 - T_C1 + 0.3, fin: 0.6, fout: 0.4 },
  ...D_T.flatMap((x) => [{ s: "sfx/crate_lift", at: x, v: 0.3 }, { s: "sfx/crate_knock", at: x + 0.58, v: 0.4 }]),
  { s: "sfx/ding", at: t_open - 0.25, v: 0.4 },
  { s: "sfx/reveal_hit", at: t_open + 0.15, v: 0.5 },
  { s: "sfx/penthouse_breeze", at: T_D1, v: 0.1, fin: 0.4 },
  { s: "sfx/remote_click", at: END_T - 0.18, v: 0.7 },
  // Musik (unter der Stimme)
  { s: "audio/music_lux", at: 0, v: 0.11, dur: T_B1 - 0.05, fin: 0.3, fout: 0.08 },                 // harter Stopp vor dem Drop
  { s: "audio/music_mystery", at: t_doch - 0.2, v: 0.14, dur: t_stamp - (t_doch - 0.2), fin: 0.25, fout: 0.03 },   // setzt mit "Doch" ein, Drop auf dem Stempel
  { s: "audio/music_groove", at: T_C1 + 0.1, v: 0.075, dur: T_D1 - T_C1 - 0.2, fin: 0.4, fout: 0.5 },
  { s: "audio/music_swell", at: t_open - 0.1, v: 0.14, fin: 0.2 },
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
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <OffthreadVideo src={staticFile("bl/onetake.mp4")} muted />
      <AbsoluteFill>
        <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{ position: "absolute" }}>
          <image href={staticFile("img/grain.png")} x={-((f * 137) % 400)} y={-((f * 71) % 400)} width={2160} height={2160} opacity={0.05} style={{ mixBlendMode: "overlay" }} />
        </svg>
        <Caption t={t} />
      </AbsoluteFill>
      <Audio src={staticFile("audio/voice.wav")} volume={interpolate(t, [0, 0.05], [0.9, 1], { extrapolateRight: "clamp" })} />
      {CUES.map((c, i) => <CueAudio key={i} c={c} />)}
    </AbsoluteFill>
  );
};
