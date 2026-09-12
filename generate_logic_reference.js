/*
 * Generate logic-reference.html: a plain-language catalogue of every conflict
 * and every bullet the population-ethics quiz can report, and the answers that
 * trigger each.  Originally written by Claude Opus 4.8.
 *
 * Written in JS, not Python, on purpose: the scoring logic lives only in
 * population-ethics-quiz.js, and the faithful way to enumerate what it can say
 * is to run that engine rather than re-describe it.  This loads the real file,
 * sweeps the reachable answer space to discover every distinct card, and then
 * works out each card's trigger by perturbing one answer at a time and asking
 * the engine whether the card still fires.  Nothing here restates the quiz's
 * prose; every title, claim and explanation is taken verbatim from the engine.
 *
 *     node generate_logic_reference.js            # -> logic-reference.html
 *     node generate_logic_reference.js -o out.html
 */

const fs = require("fs");
const vm = require("vm");
const path = require("path");

const HERE = __dirname;
const JS_FILE = path.join(HERE, "population-ethics-quiz.js");
const HTML_FILE = path.join(HERE, "population-ethics-quiz.html");

// --- load the quiz engine into a sandbox with the browser stubbed out -------
function loadEngine() {
  let src = fs.readFileSync(JS_FILE, "utf8");
  // boot() wires the live page up; nothing below the engine needs it here.
  src = src.replace(/\nboot\(\);\s*$/, "\n");
  const noop = function () {};
  const el = new Proxy(
    {},
    {
      get(t, p) {
        if (p === "querySelector") return () => el;
        if (p === "querySelectorAll") return () => [];
        if (p === "style" || p === "classList" || p === "dataset") return el;
        if (p === "value" || p === "textContent" || p === "innerHTML")
          return "";
        return typeof p === "string" ? noop : el;
      },
    },
  );
  const location = {
    href: "http://local/",
    hash: "",
    replace: noop,
    split() {
      return ["http://local/"];
    },
  };
  const sandbox = {
    document: {
      querySelector: () => el,
      querySelectorAll: () => [],
      addEventListener: noop,
      getElementById: () => el,
      createElement: () => el,
      body: el,
      documentElement: el,
    },
    window: {
      addEventListener: noop,
      scrollTo: noop,
      location,
      matchMedia: () => ({ matches: false, addEventListener: noop }),
    },
    location,
    navigator: { clipboard: null },
    localStorage: { getItem: () => null, setItem: noop, removeItem: noop },
    setTimeout: noop,
    clearTimeout: noop,
    console,
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(src, sandbox, { filename: "population-ethics-quiz.js" });
  return sandbox;
}

const S = loadEngine();
const { QUESTIONS, STORIES } = S;

// --- answer domains and the human wording the quiz shows for each answer ----
const PAIR_VALUES = ["left", "right", "equal", "none"];
const PRINCIPLE_VALUES = ["yes", "no"];
const MENU_VALUES = ["A", "B", "Z", "AB", "all"];

function valuesFor(q) {
  if (q.kind === "pair") return PAIR_VALUES;
  if (q.kind === "menu") return MENU_VALUES;
  return PRINCIPLE_VALUES; // principle
}

// The option text a person actually clicks, keyed by answer value. Pair
// options come from PAIR_OPTS; the rest carry their own opts array.
const OPT_TEXT = {};
QUESTIONS.forEach((q) => {
  const opts = q.kind === "pair" ? S.PAIR_OPTS(q) : q.opts || [];
  const m = {};
  opts.forEach((o) => {
    m[o[2]] = o[1];
  });
  OPT_TEXT[q.id] = m;
});
const QById = {};
QUESTIONS.forEach((q) => (QById[q.id] = q));

function answerPhrase(qid, v) {
  const t = OPT_TEXT[qid] && OPT_TEXT[qid][v];
  return t || v;
}

// --- reachable-profile helpers, reusing the engine's own activation logic ---
function setANS(a) {
  S.ANS = Object.assign({}, a);
}

// Drop answers to questions that this set of answers would never have shown,
// exactly as the live quiz does, then report whether every shown question has
// an answer. An incomplete run yields no verdict, so it yields no cards.
function normalize(a) {
  setANS(a);
  S.pruneInactive();
  const complete = S.missingActive().length === 0;
  return { a: S.ANS, complete };
}

// Every card a complete set of answers produces, each with a stable key. The
// key groups genuinely-identical cards while keeping distinct wordings apart.
function cardsOf(a) {
  const norm = normalize(a);
  if (!norm.complete) return [];
  const ans = norm.a;
  setANS(ans);
  const out = [];

  const R = S.analyse(ans);
  R.sets.forEach((set) => {
    const ids = [...set].sort();
    const story = S.storyFor(set, ans);
    const title = story
      ? typeof story.title === "function"
        ? story.title(ans)
        : story.title
      : "These answers cannot all hold.";
    out.push({
      kind: "conflict",
      key: "C|set|" + title + "|" + ids.join(","),
      title,
      ids,
      set,
      story,
    });
  });
  R.extras.forEach((x) => {
    out.push({
      kind: "conflict",
      key: "C|extra|" + x.id,
      extraId: x.id,
      data: x.data,
    });
  });

  const B = S.bullets();
  B.forEach((b) => {
    // Digit runs (an "N of 9 pairs" count, welfare numbers) are the only thing
    // that varies within one bullet, so normalise them out of the key.
    const norm2 = b.t.replace(/\d+/g, "#");
    out.push({ kind: "bullet", key: "B|" + norm2, bullet: b });
  });
  return out;
}

function keysOf(a) {
  return cardsOf(a).map((c) => c.key);
}

// Can this set of answers produce the card, allowing for questions it would
// newly raise? Perturbing one answer can open a conditional question that was
// not shown before (e.g. ranking K above K± opens "the modest addition against
// the harm"). Left unanswered the run is incomplete and scores nothing, which
// would look like the perturbed answer killed the card. So complete any newly
// raised questions every possible way and report whether ANY completion still
// fires it; only if none do is the perturbed answer truly incompatible.
function canProduce(a, key, budget) {
  const norm = normalize(a);
  if (norm.complete) return keysOf(norm.a).indexOf(key) !== -1;
  const miss = S.missingActive();
  if (!miss.length) return false;
  const q = QUESTIONS[miss[0]];
  const vals = valuesFor(q);
  budget = budget === undefined ? 400 : budget;
  if (budget - vals.length < 0) return true; // too wide to search: don't invent a constraint
  for (let i = 0; i < vals.length; i++) {
    const b = Object.assign({}, norm.a);
    b[q.id] = vals[i];
    if (canProduce(b, key, budget - vals.length)) return true;
  }
  return false;
}

// --- discover every distinct card by sweeping the reachable answer space ----
function mulberry32(seed) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function randomProfile(rng) {
  // Assign in ask order, so a conditional question is only given an answer
  // when the answers before it would actually have raised it.
  const a = {};
  QUESTIONS.forEach((q) => {
    setANS(a);
    if (q.when && !q.when(a)) return;
    const vals = valuesFor(q);
    a[q.id] = vals[Math.floor(rng() * vals.length)];
  });
  return a;
}

// Hand seeds guarantee the rarer conditional cards show up; they change only
// what gets discovered, never how a card's trigger is described (that comes
// from perturbation below). Each is a full, reachable set of answers.
const SEEDS = [
  // collapsing principle: an unrankable addition beside a determinate one.
  { misery: "none", neutral_mod: "right", neutral_wond: "right", pareto: "yes",
    same_number: "right", AvB: "left", benign: "right", nae: "right",
    generalize: "yes", AvZ: "left", greedy: "right", trans_gt: "yes",
    trans_eq: "yes", collapse: "yes" },
  // chaining through the gap (zrank): needs trans_none = yes on the ladder.
  { misery: "left", neutral_mod: "right", neutral_wond: "right", pareto: "yes",
    same_number: "right", AvB: "left", benign: "none", nae: "right",
    generalize: "yes", AvZ: "left", greedy: "right", trans_gt: "yes",
    trans_eq: "yes", trans_none: "yes" },
  // menu independence (menu_eq) firing on chained equalities.
  { misery: "equal", neutral_mod: "equal", neutral_wond: "equal", pareto: "yes",
    same_number: "equal", AvB: "equal", benign: "equal", nae: "right",
    generalize: "yes", AvZ: "equal", greedy: "equal", trans_gt: "yes",
    trans_eq: "yes", menu_eq: "no", menu: "all", menu_alpha: "no" },
  // alpha violation: pick a menu loser after ranking the pair.
  { misery: "left", neutral_mod: "right", neutral_wond: "right", pareto: "yes",
    same_number: "right", AvB: "left", benign: "right", nae: "right",
    generalize: "yes", AvZ: "left", greedy: "right", trans_gt: "yes",
    trans_eq: "yes", menu: "Z", menu_alpha: "yes" },
  // plusVsBoth routes: modest addition unrankable, K ranked above the pair.
  { misery: "left", neutral_mod: "none", neutral_wond: "right", pareto: "yes",
    same_number: "right", AvB: "left", benign: "right", nae: "right",
    generalize: "yes", AvZ: "left", greedy: "left", plusVsBoth: "equal",
    trans_gt: "yes", trans_eq: "yes" },
  { misery: "left", neutral_mod: "none", neutral_wond: "right", pareto: "yes",
    same_number: "right", AvB: "left", benign: "right", nae: "right",
    generalize: "yes", AvZ: "left", greedy: "left", plusVsBoth: "left",
    trans_gt: "yes", trans_eq: "yes" },
];

const reps = new Map(); // key -> representative profile (a copy)
function record(a) {
  const cards = cardsOf(a);
  cards.forEach((c) => {
    if (!reps.has(c.key)) reps.set(c.key, Object.assign({}, a));
  });
}

const rng = mulberry32(20260912);
const SWEEP = 50000;
for (let i = 0; i < SWEEP; i++) record(randomProfile(rng));
SEEDS.forEach(record);
// Perturb each seed once per question to widen coverage of nearby cards.
SEEDS.forEach((seed) => {
  QUESTIONS.forEach((q) => {
    valuesFor(q).forEach((v) => {
      const a = Object.assign({}, seed);
      a[q.id] = v;
      record(a);
    });
  });
});

// --- derive a card's trigger by one-at-a-time perturbation -------------------
// For the representative answers, hold everything fixed and vary one question:
// the values that keep the card firing are that question's allowed answers. A
// question every value tolerates does not matter and is dropped. This reads the
// engine's real behaviour rather than the source text, so it stays honest.
function triggerFor(key, rep) {
  const norm = normalize(rep).a; // the answers as the quiz would keep them
  const constraints = [];
  QUESTIONS.forEach((q) => {
    if (norm[q.id] === undefined) return; // not shown for these answers
    const vals = valuesFor(q);
    const allowed = vals.filter((v) => {
      const a = Object.assign({}, norm);
      a[q.id] = v;
      return canProduce(a, key);
    });
    if (allowed.length && allowed.length < vals.length) {
      constraints.push({ q, allowed });
    }
  });
  return constraints;
}

// --- rendering ---------------------------------------------------------------
function esc(s) {
  return String(s).replace(/&(?![a-z#0-9]+;)/gi, "&amp;");
}

function renderTrigger(constraints) {
  let h = '<div class="trigger"><div class="trigtag">Appears when</div><ul>';
  if (!constraints.length) {
    // No single answer is decisive here: the card turns on a combination (a
    // count, a disjunction across many questions). The note below spells it out.
    h +=
      '<li>No single answer settles this one — it turns on a combination of your answers. See the note below.</li>';
  }
  constraints.forEach((c) => {
    const phrases = c.allowed.map((v) => answerPhrase(c.q.id, v));
    h +=
      "<li><span class=\"qn\">" +
      esc(c.q.label) +
      "</span> &mdash; " +
      phrases.map((p) => "<em>" + esc(p) + "</em>").join(" <b>or</b> ") +
      "</li>";
  });
  h += "</ul></div>";
  return h;
}

// A conflict from the closure, rendered the way showResults() renders one, but
// with the sequential "Conflict N" number replaced by the standing category.
function renderConflictSet(card, rep, compact) {
  const ans = normalize(rep).a;
  setANS(ans);
  const st = card.story;
  let h = '<div class="hit"><div class="tag">Conflict &middot; ' +
    card.set.size + " answers, jointly unsatisfiable</div>";
  h += '<h3 style="margin-top:10px">' + card.title + "</h3>";
  h += '<ol class="claims">';
  QUESTIONS.forEach((q) => {
    if (card.set.has(q.id)) h += "<li>" + S.claimText(q.id) + "</li>";
  });
  h += "</ol>";
  // The generic contradictions all carry the same one-line explanation, stated
  // once at the head of their section, so it is not repeated on each card.
  if (compact) return h + "</div>";
  if (st) {
    h +=
      '<p class="because">' +
      (typeof st.because === "function" ? st.because(ans) : st.because) +
      "</p>";
  } else {
    h +=
      '<p class="because">If the principles of transitivity and menu-independence hold — and your answers said they do — then your ranking of outcomes contradicts itself.</p>';
  }
  if (st && st.chain) h += '<div class="chainwrap">' + S.chainSVG(true) + "</div>";
  if (st && st.world) h += S.worldNote(st.world);
  h += "</div>";
  return h;
}

function renderConflictExtra(card, rep) {
  const ans = normalize(rep).a;
  setANS(ans);
  // CARD_HTML prints "Conflict N · <category>"; drop the run-specific number.
  let h = S.CARD_HTML[card.extraId](card.data, "");
  h = h.replace(/Conflict\s+&middot;/, "Conflict &middot;");
  return h;
}

function renderBullet(card, rep) {
  const ans = normalize(rep).a;
  setANS(ans);
  const b = card.bullet;
  let h =
    '<div class="bullet"><div class="tag">Consistent, but costly</div><h3 style="margin-top:8px">' +
    b.t +
    "</h3>";
  if (b.claims && b.claims.length) {
    h += '<ol class="claims">';
    QUESTIONS.forEach((q) => {
      if (b.claims.indexOf(q.id) >= 0) h += "<li>" + S.claimText(q.id) + "</li>";
    });
    h += "</ol>";
  }
  h +=
    '<p class="qbody" style="font-size:17px">' +
    b.b +
    "</p>" +
    (b.world ? S.worldNote(b.world) : "") +
    "</div>";
  return h;
}

// Short human notes for the few cards whose trigger is a disjunction or an
// "only if" the one-at-a-time perturbation cannot phrase on its own. Keyed by
// the stable card key; each is clearly marked as an editorial clarification.
const NOTES = {
  "B|You said a life worth living makes the world worse by being lived.":
    "Either addition alone is enough: it fires if the modest good life, the wonderful life, or both are judged to make the world worse.",
  "B|Nadia’s life gets better and your verdict gets worse.":
    "Fires whenever any better life for Nadia is ranked below a worse one for her — across the life-of-agony, modest-life and wonderful-life additions.",
  "B|You judged # of the # pairs unrankable.":
    "Fires when at least three of the nine pair comparisons are answered “cannot be ranked.” Which three does not matter; the count is what triggers it.",
  "B|Comparable when the numbers match, unrankable when they do not.":
    "Fires when the same-number pair is ranked determinately while at least one different-number pair is left unrankable. Any one such pair is enough.",
  "B|You hold the Procreation Asymmetry.":
    "Fires when adding a life of suffering is judged bad while adding a good life (modest or wonderful) is judged not-good — either “exactly as good” or “cannot be ranked.”",
  "B|A neutral addition made a harm unrankable.":
    "The wonderful-life addition may be judged either “exactly as good” or “cannot be ranked” against leaving Nadia out.",
};

// --- assemble the page -------------------------------------------------------
const styleMatch = fs.readFileSync(HTML_FILE, "utf8").match(/<style>[\s\S]*?<\/style>/i);
const STYLE = styleMatch ? styleMatch[0] : "";

const EXTRA_STYLE = `
<style>
.wrap{max-width:820px}
.docintro{margin:0 0 10px}
.docintro .lede{margin-top:18px}
.count{font-family:var(--mono);font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);margin-top:8px}
.entry{margin:34px 0 0}
.trigger{background:var(--panel);border:1px solid var(--hair);border-left:3px solid var(--ink);padding:14px 16px;margin:0 0 -6px}
.trigger .trigtag{font-family:var(--mono);font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--dim);margin-bottom:8px}
.trigger ul{margin:0;padding:0;list-style:none}
.trigger li{padding:5px 0;border-top:1px solid var(--hair);font-size:16px}
.trigger li:first-child{border-top:0}
.trigger .qn{font-weight:600}
.trigger em{font-style:normal;background:rgba(27,63,139,.10);padding:1px 6px;border:1px solid var(--blue-30)}
.trigger b{font-family:var(--mono);font-size:11px;letter-spacing:.06em;color:var(--dim)}
.note{font-size:15.5px;color:var(--dim);border-left:2px solid var(--violet);padding:2px 0 2px 14px;margin:12px 0 0;max-width:64ch}
.note b{color:var(--violet);font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase}
.sectionhead{margin:54px 0 0}
.sectionhead h2{font-size:clamp(30px,6vw,44px);letter-spacing:-.02em}
</style>`;

// Order: conflicts first (closure sets, then the checks outside the closure),
// then bullets. Within each, order by first appearance in the sweep is stable
// enough, but a fixed sort by title keeps regenerations diff-friendly.
const GENERIC_TITLE = "These answers cannot all hold.";
const allKeys = [...reps.keys()];
const conflicts = allKeys
  .filter((k) => k.startsWith("C|") && k.indexOf("|" + GENERIC_TITLE + "|") === -1)
  .sort();
const generic = allKeys
  .filter((k) => k.indexOf("|" + GENERIC_TITLE + "|") !== -1)
  .sort();
const bullets = allKeys.filter((k) => k.startsWith("B|")).sort();

function entryFor(key, compact) {
  const rep = reps.get(key);
  const cards = cardsOf(rep);
  const card = cards.find((c) => c.key === key);
  const constraints = triggerFor(key, rep);
  let body;
  if (card.kind === "bullet") body = renderBullet(card, rep);
  else if (card.extraId) body = renderConflictExtra(card, rep);
  else body = renderConflictSet(card, rep, compact);
  const note = NOTES[key]
    ? '<div class="note"><b>Note</b> &middot; ' + NOTES[key] + "</div>"
    : "";
  return '<div class="entry">' + renderTrigger(constraints) + body + note + "</div>";
}

let body = "";
body +=
  '<div class="hero docintro" style="padding:8vh 0 0">' +
  '<div class="kicker">Transparency &middot; the full rulebook</div>' +
  '<h1 style="font-size:clamp(34px,8vw,64px);letter-spacing:-.02em;margin-top:14px">Every conflict and every bullet</h1>' +
  '<p class="lede">This page lists every result the <a href="population-ethics-quiz.html">Population Ethics Consistency Test</a> can report, and the answers that trigger each. The quiz only shows you the handful that apply to your own answers; here they are all laid out so you can read through the whole of its logic.</p>' +
  '<p class="lede small">A <strong>conflict</strong> is a set of answers that cannot all be true together. A <strong>bullet</strong> is a position that is perfectly consistent but carries a cost many find hard to accept. Every title, claim and explanation below is generated directly from the quiz’s own code; the &ldquo;Appears when&rdquo; box above each card is worked out by checking which answers actually make it fire.</p>' +
  '<p class="small">The answers are named the way the quiz words its options. The worlds: <strong>A</strong> 100 people at 100; <strong>A+</strong> 100 at 101 plus 100 at 25; <strong>B</strong> 200 at 64; <strong>Z</strong> 51,200 barely-good lives; <strong>K</strong> 500 at 55; <strong>K− / K+ / K++</strong> K plus one life at −40 / 7 / 70 (Nadia); <strong>K±</strong> K with Owen down to 20 and Nadia added at 70.</p>' +
  '<hr class="rule"></div>';

body +=
  '<div class="sectionhead"><div class="eyebrow" style="color:var(--red)">Part one</div>' +
  '<h2>Conflicts</h2><p class="count">' +
  conflicts.length +
  " named conflicts</p>" +
  '<p class="qbody" style="max-width:64ch">Each of these is a set of answers that cannot all be true together, with the argument that shows why.</p></div>';
conflicts.forEach((k) => (body += entryFor(k)));

if (generic.length) {
  body +=
    '<div class="sectionhead"><div class="eyebrow" style="color:var(--red)">Part one, continued</div>' +
    '<h2>Further contradictions</h2><p class="count">' +
    generic.length +
    " answer sets with no dedicated write-up</p>" +
    '<p class="qbody" style="max-width:64ch">Underneath the named arguments is a general check: the quiz takes every ranking your answers imply and follows the chain wherever transitivity and menu-independence lead. Any answers that make the chain reverse itself are flagged, whether or not one of the arguments above has a story for them. The sets below are the ones an extensive search turned up that fall outside the named arguments; for each, the quiz says only that the answers cannot all hold. The check is general, so unusual combinations may produce others.</p></div>';
  generic.forEach((k) => (body += entryFor(k, true)));
}

body +=
  '<div class="sectionhead"><div class="eyebrow" style="color:var(--blue)">Part two</div>' +
  '<h2>Bullets</h2><p class="count">' +
  bullets.length +
  " distinct bullet cards</p>" +
  '<p class="qbody" style="max-width:64ch">Each of these is consistent — nothing here contradicts anything else you said — but carries a cost many find hard to accept.</p></div>';
bullets.forEach((k) => (body += entryFor(k)));

const page = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Population Ethics Test — Full Logic Reference</title>
<meta name="description" content="Every conflict and every bullet the Population Ethics Consistency Test can report, and the answers that trigger each.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,900&family=Newsreader:opsz,wght@6..72,300;6..72,400;6..72,600&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
${STYLE}
${EXTRA_STYLE}
</head>
<body>
<div class="wrap">
${body}
<footer></footer>
</div>
</body>
</html>
`;

const outArg = process.argv.indexOf("-o");
const outFile =
  outArg !== -1 ? process.argv[outArg + 1] : path.join(HERE, "logic-reference.html");
fs.writeFileSync(outFile, page);
console.error(
  "Discovered " +
    conflicts.length +
    " conflict cards and " +
    bullets.length +
    " bullet cards; wrote " +
    outFile,
);
