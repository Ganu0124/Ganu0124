#!/usr/bin/env node
/**
 * Jet heatmap: your GitHub contribution graph with a ship that flies along the
 * bottom and shoots the active cells. Writes dist/dark.svg and dist/light.svg.
 *
 *   GITHUB_TOKEN=... node generate.mjs            # real data
 *   node generate.mjs --sample                    # offline demo data
 *   GITHUB_USER=someone node generate.mjs
 */
import fs from "node:fs";

const args = process.argv.slice(2);
const USER = process.env.GITHUB_USER || args.find((a) => !a.startsWith("--")) || "Ganu0124";
const TOKEN = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
const SAMPLE = args.includes("--sample") || !TOKEN;

const CELL = 14, GAP = 4, PAD = 26, STEP = CELL + GAP;
const MAX_TARGETS = 14, SLOT = 1.3;

const THEMES = {
  dark: {
    bg: "#0d1117",
    levels: ["#161b22", "#3b0764", "#5b21b6", "#7c3aed", "#a78bfa"],
    accent: "#22d3ee", ship: "#c4b5fd", ring: "#22d3ee",
  },
  light: {
    bg: "#ffffff",
    levels: ["#ebedf0", "#ddd6fe", "#a78bfa", "#7c3aed", "#4c1d95"],
    accent: "#0891b2", ship: "#6d28d9", ring: "#0891b2",
  },
};

// ---------------------------------------------------------------- data
function rng(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function sampleWeeks() {
  const r = rng(42);
  return Array.from({ length: 53 }, () =>
    Array.from({ length: 7 }, () => (r() < 0.45 ? 0 : Math.floor(r() * r() * 14))));
}

async function fetchWeeks() {
  const query = `query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{weeks{contributionDays{contributionCount weekday}}}}}}`;
  const res = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers: { Authorization: `bearer ${TOKEN}`, "Content-Type": "application/json", "User-Agent": "jet-heatmap" },
    body: JSON.stringify({ query, variables: { login: USER } }),
  });
  if (!res.ok) throw new Error(`GitHub API ${res.status}`);
  const json = await res.json();
  if (json.errors) throw new Error(JSON.stringify(json.errors));
  return json.data.user.contributionsCollection.contributionCalendar.weeks.map((w) => {
    const col = Array(7).fill(0);
    for (const d of w.contributionDays) col[d.weekday] = d.contributionCount;
    return col;
  });
}

// ---------------------------------------------------------------- svg helpers
const f = (n) => +n.toFixed(3);

function anim(tag, attrs, pts, T) {
  const p = [...pts].sort((a, b) => a[0] - b[0]);
  if (p[0][0] > 0) p.unshift([0, p[0][1]]);
  if (p[p.length - 1][0] < T) p.push([T, p[p.length - 1][1]]);
  const keyTimes = p.map((x) => f(Math.min(x[0], T) / T)).join(";");
  const values = p.map((x) => x[1]).join(";");
  return `<${tag} ${attrs} dur="${f(T)}s" repeatCount="indefinite" keyTimes="${keyTimes}" values="${values}"/>`;
}

function render(weeks, theme) {
  const nWeeks = weeks.length;
  const flat = weeks.flat();
  const max = Math.max(1, ...flat);
  const level = (c) => (c === 0 ? 0 : Math.min(4, Math.ceil((4 * c) / max)));

  const gridW = nWeeks * STEP - GAP;
  const gridH = 7 * STEP - GAP;
  const W = gridW + PAD * 2;
  const shipY = PAD + gridH + 46;
  const H = shipY + 34;

  // one target per column: the lowest active cell (the first one a bullet meets)
  const candidates = [];
  weeks.forEach((col, wi) => {
    for (let d = 6; d >= 0; d--) if (col[d] > 0) { candidates.push({ wi, d }); break; }
  });
  const r = rng(7);
  for (let i = candidates.length - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1));
    [candidates[i], candidates[j]] = [candidates[j], candidates[i]];
  }
  const targets = candidates.slice(0, MAX_TARGETS);
  const N = Math.max(targets.length, 1);
  const T = N * SLOT + 1.2;

  const cx = (wi) => PAD + wi * STEP + CELL / 2;
  const cy = (d) => PAD + d * STEP + CELL / 2;

  let cells = "";
  weeks.forEach((col, wi) =>
    col.forEach((c, d) => {
      cells += `<rect x="${PAD + wi * STEP}" y="${PAD + d * STEP}" width="${CELL}" height="${CELL}" rx="3" fill="${theme.levels[level(c)]}"/>`;
    }));

  const startX = W / 2;
  const shipPts = [[0, `${startX} ${shipY}`]];
  const bx = [], by = [], bo = [[0, 0]];
  let overlays = "", rings = "";
  let curX = startX;

  targets.forEach((t, i) => {
    const s = i * SLOT + 0.3;
    const tx = cx(t.wi), ty = cy(t.d);
    const hit = s + 0.85;
    shipPts.push([s, `${curX} ${shipY}`], [s + 0.5, `${tx} ${shipY}`]);
    curX = tx;
    bx.push([s + 0.5, tx], [hit, tx]);
    by.push([s + 0.5, shipY - 16], [hit, ty]);
    bo.push([s + 0.49, 0], [s + 0.5, 1], [hit, 1], [hit + 0.01, 0]);

    overlays += `<rect x="${tx - CELL / 2}" y="${ty - CELL / 2}" width="${CELL}" height="${CELL}" rx="3" fill="${theme.bg}" opacity="0">` +
      anim("animate", 'attributeName="opacity"', [[0, 0], [hit, 0], [hit + 0.05, 0.88], [T - 0.6, 0.88], [T, 0]], T) + `</rect>`;
    rings += `<circle cx="${tx}" cy="${ty}" r="0" fill="none" stroke="${theme.ring}" stroke-width="2" opacity="0">` +
      anim("animate", 'attributeName="r"', [[0, 0], [hit, 2], [hit + 0.4, CELL * 1.2]], T) +
      anim("animate", 'attributeName="opacity"', [[0, 0], [hit, 1], [hit + 0.4, 0]], T) + `</circle>`;
  });

  shipPts.push([N * SLOT + 0.3, `${curX} ${shipY}`], [T, `${startX} ${shipY}`]);

  const bullet = `<circle r="2.6" fill="${theme.accent}" opacity="0">` +
    anim("animate", 'attributeName="cx"', bx.length ? bx : [[0, 0]], T) +
    anim("animate", 'attributeName="cy"', by.length ? by : [[0, 0]], T) +
    anim("animate", 'attributeName="opacity"', bo, T) + `</circle>`;

  const ship = `<g transform="translate(${startX} ${shipY})">` +
    anim("animateTransform", 'attributeName="transform" type="translate"', shipPts, T) +
    `<path d="M0,-15 L11,8 L4,4 L0,10 L-4,4 L-11,8 Z" fill="${theme.ship}"/>` +
    `<circle cx="0" cy="-2" r="2.4" fill="${theme.bg}"/>` +
    `<path d="M-2.5,11 L0,17 L2.5,11 Z" fill="${theme.accent}"><animate attributeName="opacity" values="1;.25;1" dur="0.25s" repeatCount="indefinite"/></path>` +
    `</g>`;

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">` +
    `<rect width="${W}" height="${H}" rx="12" fill="${theme.bg}"/>${cells}${overlays}${rings}${bullet}${ship}</svg>\n`;
}

// ---------------------------------------------------------------- main
const weeks = SAMPLE ? sampleWeeks() : await fetchWeeks();
fs.mkdirSync("dist", { recursive: true });
for (const [name, theme] of Object.entries(THEMES)) fs.writeFileSync(`dist/${name}.svg`, render(weeks, theme));
console.log(`wrote dist/dark.svg and dist/light.svg (${SAMPLE ? "sample data" : "live data for " + USER})`);
