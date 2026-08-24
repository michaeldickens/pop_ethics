#!/usr/bin/env python3
"""
Test suite for population-ethics-quiz.html.  Originally written by Claude Opus 4.8.

Setup (Linux Mint):
    python3 -m pip install --user playwright
    python3 -m playwright install chromium

Note: the geometry suite measures real text metrics, so results depend on
whether Fraunces and Space Mono actually load. Run it online, or with those
fonts installed locally, if you want the numbers the page really renders.

Run:
    ./test_quiz.py                                   # every suite
    ./test_quiz.py --suite fuzz --cases 20000        # hammer one suite
    ./test_quiz.py --seed 99 -v                      # different corpus, verbose
    ./test_quiz.py --file /path/to/quiz.html

Suites:
    engine    fixed profiles with known-correct answers
    oracle    the optimised closure vs. a naive fixpoint reference, on random input
    fuzz      seeded random profiles checked against invariants that must always hold
    geometry  every bar and label measured against its viewBox
    layout    overflow, clipping and JS errors at three viewport widths
    flow      keyboard entry, back button, restart, tally-matches-cards
    share     URL fragment round trip, share links, deep links
    conditional  questions that appear only when they are relevant
    views     named positions from population_ethics_views.py

Exit status is 0 only if every selected suite passes.
"""

import argparse
import json
import pathlib
import sys
from playwright.sync_api import sync_playwright

QIDS = ["pareto", "AvB", "misery", "neutral_mod", "benign", "nae", "generalize",
        "AvZ", "neutral_wond", "collapse", "trans_gt", "trans_none", "trans_eq",
        "menu_eq", "menu"]
PAIRS = ["AvB", "misery", "neutral_mod", "benign", "nae", "AvZ", "neutral_wond"]
PRINCIPLES = ["pareto", "generalize", "collapse", "trans_gt", "trans_none",
              "trans_eq", "menu_eq"]
CONDITIONAL = ("collapse", "trans_none", "menu_eq")
PAIR_VALUES = ["left", "right", "equal", "none"]
PRINCIPLE_VALUES = ["yes", "no"]
MENU_VALUES = ["A", "B", "Z", "none"]

# Index of the answer button to click, per question, for named profiles.
CLICK_MODAL = {"pareto": 0, "AvB": 0, "misery": 0, "neutral_mod": 2, "benign": 1,
               "nae": 1, "generalize": 0, "AvZ": 0, "neutral_wond": 2, "collapse": 0,
               "trans_gt": 0, "trans_none": 0, "trans_eq": 0, "menu_eq": 0, "menu": 0}
CLICK_TOTALIST = {"pareto": 0, "AvB": 1, "misery": 0, "neutral_mod": 1, "benign": 1,
                  "nae": 1, "generalize": 0, "AvZ": 1, "neutral_wond": 1, "collapse": 0,
                  "trans_gt": 0, "trans_none": 0, "trans_eq": 0, "menu_eq": 0, "menu": 2}
CLICK_ALPHA = dict(CLICK_TOTALIST, menu=0)
# Accepting every principle but declaring every pair unrankable. Index 3 on a
# pair is "neither - they cannot be ranked", the only way to decline.
CLICK_UNRANKABLE = {q: (0 if q in PRINCIPLES else 3) for q in QIDS}
CLICK_REJECT = {q: (1 if q in PRINCIPLES else 0) for q in QIDS}

MODAL = {"pareto": "yes", "AvB": "left", "misery": "left", "neutral_mod": "equal",
         "benign": "right", "nae": "right", "generalize": "yes", "AvZ": "left",
         "neutral_wond": "equal", "collapse": "yes", "trans_gt": "yes",
         "trans_none": "yes", "trans_eq": "yes", "menu_eq": "yes", "menu": "A"}
TOTALIST = {"pareto": "yes", "AvB": "right", "misery": "left", "neutral_mod": "right",
            "benign": "right", "nae": "right", "generalize": "yes", "AvZ": "right",
            "neutral_wond": "right", "collapse": "yes", "trans_gt": "yes", "trans_none": "yes",
            "trans_eq": "yes", "menu_eq": "yes", "menu": "Z"}

LADDER_SHORT = "AvB+benign+nae+trans_gt"
LADDER_FULL = "AvZ+benign+generalize+nae+trans_gt"
BROOME = "menu_eq+neutral_mod+neutral_wond+pareto+trans_eq"


class Report:
    def __init__(self, verbose):
        self.verbose, self.failures, self.checks = verbose, [], 0

    def check(self, ok, name, detail=""):
        self.checks += 1
        if not ok:
            self.failures.append(f"{name}  {detail}".rstrip())
        if self.verbose or not ok:
            print(f"  {'pass' if ok else 'FAIL'}  {name}" + (f"   {detail}" if detail else ""))

    def note(self, msg):
        if self.verbose:
            print(f"        {msg}")

    def suite(self, name):
        print(f"\n=== {name} ===")


def bullet_titles(page, profile):
    return page.evaluate("""(a) => { const keep = ANS; ANS = a;
                                     const t = bullets().map(x => x.t);
                                     ANS = keep; return t; }""", profile)


def analyse(page, answers):
    return page.evaluate(
        """a => { const r = analyse(a);
                  return {sets: r.sets.map(s => [...s].sort().join('+')).sort(),
                          alpha: r.alpha, collapse: r.collapse, zrank: r.zrank,
                          clashes: r.clashes.length}; }""", answers)


# ---------------------------------------------------------------- suites

def suite_engine(page, rep):
    rep.suite("engine")

    r = analyse(page, MODAL)
    rep.check(LADDER_SHORT in r["sets"], "modal profile: one-rung A/B contradiction found")
    rep.check(LADDER_FULL in r["sets"], "modal profile: full repugnant ladder found")
    rep.check(BROOME in r["sets"], "modal profile: Broome neutrality contradiction found")
    rep.check(len(r["sets"]) == 3, "modal profile: exactly three hits", f"got {r['sets']}")
    rep.check(r["alpha"] is None, "modal profile: no spurious contraction violation")

    r = analyse(page, dict(MODAL, trans_gt="no"))
    rep.check(not any("benign" in s for s in r["sets"]),
              "rejecting better-than transitivity kills both ladder hits")
    rep.check(BROOME in r["sets"],
              "...but not Broome, which only needs equal-goodness transitivity")

    r = analyse(page, dict(MODAL, trans_eq="no"))
    rep.check(BROOME not in r["sets"], "rejecting equal-goodness transitivity kills Broome")
    rep.check(LADDER_FULL in r["sets"], "...but leaves the ladder standing")

    r = analyse(page, dict(MODAL, pareto="no"))
    rep.check(BROOME not in r["sets"], "Broome needs Pareto")

    # Q3 is now wired into the Nadia cluster, so its answers can be load-bearing.
    never = dict(MODAL, misery="equal", neutral_mod="equal", neutral_wond="equal")
    r = analyse(page, never)
    rep.check("menu_eq+misery+neutral_mod+pareto+trans_eq" in r["sets"],
              "'creating is never better or worse' collides at the bad end too")
    rep.check("menu_eq+misery+neutral_wond+pareto+trans_eq" in r["sets"],
              "...and against the wonderful life as well")

    better = dict(MODAL, misery="right")
    r = analyse(page, better)
    rep.check(any("misery" in s for s in r["sets"]),
              "saying a life of suffering improves things is now caught")

    r = analyse(page, dict(MODAL, misery="left"))
    rep.check(not any("misery" in s for s in r["sets"]),
              "...while the modal answer (it makes things worse) stays consistent")

    r = analyse(page, dict(MODAL, generalize="no"))
    rep.check(LADDER_FULL not in r["sets"], "blocking generalisation kills the full ladder")
    rep.check(LADDER_SHORT in r["sets"], "...but the one-rung version survives")

    r = analyse(page, TOTALIST)
    rep.check(not r["sets"] and not r["alpha"], "consistent totalist crosses clean")

    abstain = {q: ("none" if q in PAIRS else "abstain") for q in QIDS}
    abstain["menu"] = "none"
    r = analyse(page, abstain)
    rep.check(not r["sets"] and not r["alpha"], "declining every comparison yields no hits")

    mixed = dict(MODAL, AvB="none")
    rep.check(LADDER_SHORT not in analyse(page, mixed)["sets"],
              "declaring a pair unrankable removes the hit that needed it")

    r = analyse(page, dict(TOTALIST, AvB="right", menu="A"))
    rep.check(r["alpha"] and r["alpha"]["picked"] == "A" and r["alpha"]["pairWinner"] == "B",
              "contraction inconsistency detected (Sen's alpha)")

    # Picking Z while ranking A above it in the pair turns on AvZ alone. Gating
    # it behind AvB let anyone who declined that pair walk through unnoticed.
    r = analyse(page, dict(MODAL, AvB="none", AvZ="left", menu="Z"))
    rep.check(r["alpha"] and r["alpha"]["viaZ"] and r["alpha"]["picked"] == "Z",
              "picking Z over a ranked A is caught with A/B declined")

    # Ranking below the gap. The ladder route is Parfit's argument run on "not
    # worse than": an unrankable pair is still a pair where neither is worse,
    # so declining to rank the rungs does not break the chain - only denying
    # that the relation chains does, which is Parfit's own answer.
    gaps = dict(MODAL, AvB="none", benign="none", AvZ="left", menu="A")
    r = analyse(page, dict(gaps, generalize="yes", trans_none="yes"))
    rep.check(r["zrank"] and r["zrank"]["via"] == "ladder",
              "gaps on every rung chain to Z through not-worse-than")
    rep.check(r["zrank"] and "trans_none" in r["zrank"]["ids"] and
              "nae" in r["zrank"]["ids"],
              "...and the chaining and the levelling step are both blamed for it")
    r = analyse(page, dict(gaps, generalize="yes", trans_none="no"))
    rep.check(r["zrank"] is None,
              "Parfit's escape - not-worse-than does not chain - clears it")
    r = analyse(page, dict(gaps, generalize="yes", trans_none="yes", nae="left"))
    rep.check(r["zrank"] is None,
              "...as does a levelling step that is a step down, which breaks the chain")
    r = analyse(page, dict(gaps, generalize="no", trans_none="yes"))
    rep.check(r["zrank"] is None,
              "...as does the verdict flipping partway down, where the chain stops")

    # The misery route has no chain to run on: it turns on ranking A above Z
    # while placing a critical level at -40, beneath the welfare Z's people
    # live at. Independent of the ladder, so it survives what breaks the chain.
    r = analyse(page, dict(gaps, generalize="no", misery="none", trans_none="yes"))
    rep.check(r["zrank"] and r["zrank"]["via"] == "misery",
              "an unrankable agony addition collides with ranking Z on its own")
    r = analyse(page, dict(gaps, generalize="yes", misery="none",
                           trans_none="yes", AvZ="right"))
    rep.check(r["zrank"] is None,
              "...and neither route bites on someone who ranks Z above A")

    # Rejecting a principle always draws a bullet. A revisionary verdict used to
    # draw nothing, so answers like "her agony improves the world" could pass
    # in total silence. Each must now name itself.
    titles = """(a) => { const keep = ANS; ANS = a;
                         const t = bullets().map(x => x.t); ANS = keep; return t; }"""
    for qid, val, phrase in [
            ("misery", "right", "as a gain"),
            ("neutral_mod", "left", "worse by being lived"),
            ("neutral_wond", "left", "worse by being lived"),
            ("benign", "left", "called it worse"),
            ("nae", "left", "levelling up")]:
        got = page.evaluate(titles, dict(MODAL, **{qid: val}))
        rep.check(any(phrase in t for t in got),
                  f"revisionary verdict {qid}={val} draws its own bullet", str(got))

    # Ranking a better life below a worse one is only a conflict if Pareto is
    # kept; with Pareto dropped it has to surface as a bullet instead.
    nonmono = page.evaluate(titles, dict(MODAL, pareto="no", neutral_wond="left"))
    rep.check(any("verdict gets worse" in t for t in nonmono),
              "ranking a better life below a worse one is flagged even without Pareto",
              str(nonmono))
    mono = page.evaluate(titles, dict(MODAL, neutral_mod="right", neutral_wond="right"))
    rep.check(not any("verdict gets worse" in t for t in mono),
              "a monotonic ranking of the three additions is not flagged", str(mono))

    # The property that matters: no revisionary answer can appear in a profile
    # the quiz says nothing at all about.
    watch = [["misery", "right"], ["neutral_mod", "left"], ["neutral_wond", "left"],
             ["benign", "left"], ["nae", "left"], ["pareto", "no"], ["trans_gt", "no"],
             ["trans_eq", "no"], ["generalize", "no"], ["AvZ", "right"]]
    silent = page.evaluate("""(cfg) => {
      const keep = ANS, bad = new Set();
      cfg.profiles.forEach(a => {
        ANS = a;
        const r = analyse(a);
        if (r.sets.length === 0 && !r.alpha && bullets().length === 0)
          cfg.watch.forEach(([q, v]) => { if (a[q] === v) bad.add(q + '=' + v); });
      });
      ANS = keep;
      return [...bad];
    }""", {"profiles": random_profiles(2500, 4242), "watch": watch})
    rep.check(not silent,
              "no revisionary answer can pass with the quiz saying nothing at all",
              str(silent))

    # A menu-dependent view: the three pairwise verdicts are each fine, and
    # cohere only because they are never required to sit in one ordering.
    FRIEND = dict(MODAL, neutral_mod="equal", neutral_wond="equal",
                  pareto="yes", trans_eq="yes", menu_eq="no")
    r = analyse(page, FRIEND)
    rep.check(BROOME not in r["sets"],
              "denying menu independence lets K=K+, K=K++ and K++>K+ stand together",
              str(r["sets"]))
    rep.check(any("wider menu" in t for t in bullet_titles(page, FRIEND)),
              "and it is recorded as a bullet rather than passing in silence",
              str(bullet_titles(page, FRIEND)))
    rep.check(BROOME in analyse(page, dict(FRIEND, menu_eq="yes"))["sets"],
              "accepting it brings the conflict straight back")

    # It must only block chaining that actually consumes an equality. The
    # ladder conflicts run on better-than, and have to survive untouched.
    rep.check(LADDER_FULL in r["sets"] and LADDER_SHORT in r["sets"],
              "denying it does not disturb the better-than ladder", str(r["sets"]))
    for name, prof in [("modal", MODAL), ("totalist", TOTALIST)]:
        with_it = analyse(page, dict(prof, menu_eq="yes"))["sets"]
        without = analyse(page, dict(prof, menu_eq="no"))["sets"]
        gone = [x for x in with_it if x not in without]
        rep.check(all("trans_eq" in x for x in gone),
                  f"{name}: only equality-chaining conflicts depend on it", str(gone))

    # Every conflict that charges trans_eq must charge menu_eq too: both are
    # needed for the step, so blaming one without the other would be wrong.
    lopsided = page.evaluate("""(profiles) => {
      const keep = ANS, bad = [];
      profiles.forEach(a => {
        ANS = a;
        analyse(a).sets.forEach(S => {
          if (S.has('trans_eq') !== S.has('menu_eq')) bad.push([...S].sort().join('+'));
        });
      });
      ANS = keep; return [...new Set(bad)];
    }""", random_profiles(2000, 5150))
    rep.check(not lopsided,
              "no conflict blames equality-chaining without blaming menu independence",
              str(lopsided[:3]))

    # Broome ch.12: the collapsing principle. "Cannot be ranked" emits no edge,
    # so before this check an incomparabilist could not be caught by anything.
    cp = dict(MODAL, collapse="yes")
    r = analyse(page, dict(cp, neutral_mod="none", neutral_wond="right"))
    rep.check(r["collapse"] and r["collapse"]["vague"]["id"] == "neutral_mod"
              and r["collapse"]["anchor"]["id"] == "neutral_wond"
              and r["collapse"]["dir"] == "up",
              "collapsing principle fires upward: unrankable low, determinate high",
              str(r["collapse"]))
    r = analyse(page, dict(cp, neutral_mod="left", neutral_wond="none"))
    rep.check(r["collapse"] and r["collapse"]["dir"] == "down",
              "collapsing principle fires downward", str(r["collapse"]))
    rep.check(not analyse(page, dict(cp, collapse="no", neutral_mod="none",
                                     neutral_wond="right"))["collapse"],
              "rejecting the collapsing principle blocks it")
    rep.check(not analyse(page, dict(cp, neutral_mod="none",
                                     neutral_wond="none"))["collapse"],
              "unrankable at every level has nothing determinate to collapse into")
    rep.check(not analyse(page, cp)["collapse"],
              "no unrankable answer means no collapse to make")
    # The boundary at welfare 0 is principled, not arbitrary: it is where the
    # Procreation Asymmetry locates the change. The principle must not reach
    # across it, or it would catch the asymmetry by brute force.
    rep.check(not analyse(page, dict(cp, misery="left", neutral_mod="none"))["collapse"],
              "the principle does not reach across the neutral level")
    levels = page.evaluate("() => [K_BAD[1].w, K_MOD[1].w, K_WOND[1].w]")
    rep.check(levels[0] < 0 < levels[1] < levels[2],
              "the three Nadia levels still straddle zero as the check assumes", str(levels))

    # The point of the whole exercise: incomparability must be falsifiable.
    caught = page.evaluate("""(ps) => {
      const keep = ANS; let ever = 0, tot = 0;
      ps.forEach(a => {
        ANS = a;
        const r = analyse(a);
        const sup = new Set();
        r.sets.forEach(s => s.forEach(x => sup.add(x)));
        if (r.collapse) { sup.add(r.collapse.vague.id); sup.add(r.collapse.anchor.id); }
        Object.keys(a).forEach(q => { if (a[q] === 'none') { tot++; if (sup.has(q)) ever++; } });
      });
      ANS = keep; return {ever, tot};
    }""", random_profiles(2000, 771))
    rep.check(caught["ever"] > 0,
              "an unrankable answer can now be implicated in a conflict",
              f"{caught['ever']} of {caught['tot']}")

    # The Procreation Asymmetry's second half says creating a happy person is
    # not BETTER. "Cannot be ranked" satisfies that as squarely as "exactly as
    # good", and is the version that survives Broome, so both must count.
    asym = """(a) => { const keep = ANS; ANS = a;
                       const b = bullets().some(x => x.t.includes('Procreation'));
                       ANS = keep; return b; }"""
    for name, prof, want in [
            ("exactly as good", dict(MODAL), True),
            ("unrankable", dict(MODAL, neutral_mod="none", neutral_wond="none"), True),
            ("unrankable, modest life only", dict(MODAL, neutral_mod="none",
                                                  neutral_wond="right"), True),
            ("unrankable, wonderful life only", dict(MODAL, neutral_mod="right",
                                                     neutral_wond="none"), True),
            ("one route each", dict(MODAL, neutral_mod="none"), True),
            ("adding a happy life is better", dict(MODAL, neutral_mod="right",
                                                   neutral_wond="right"), False),
            ("nothing ranked at all", dict(MODAL, misery="none", neutral_mod="none",
                                           neutral_wond="none"), False),
            ("adding misery is an improvement", dict(MODAL, misery="right",
                                                     neutral_mod="none"), False)]:
        rep.check(page.evaluate(asym, prof) == want,
                  f"asymmetry bullet {'fires' if want else 'stays quiet'}: {name}")

    # Unrankability is the route that dodges Broome, so the bullet is the only
    # thing that will say anything to that reader. It must not go silent.
    quiet = analyse(page, dict(MODAL, neutral_mod="none", neutral_wond="none"))
    rep.check(not any("neutral" in st for st in quiet["sets"]),
              "declaring both additions unrankable does escape the Broome conflict",
              str(quiet["sets"]))

    chain = page.evaluate("() => CHAIN.map(s => ({f: s.from, p: s.plus, t: s.to}))")
    bad = [i for i, s in enumerate(chain)
           if not (s["t"]["n"] * s["t"]["w"] > sum(g["n"] * g["w"] for g in s["p"])
                   and s["t"]["w"] > sum(g["n"] * g["w"] for g in s["p"]) / sum(g["n"] for g in s["p"])
                   and sum(g["n"] for g in s["p"]) == s["t"]["n"])]
    rep.check(not bad, "every ladder rung raises total and average and keeps headcount",
              f"bad rungs {bad}" if bad else f"{len(chain)} rungs")


NAIVE_ORACLE = """
(a) => ({edges: compile(a), useGt: a.trans_gt === 'yes', useEq: a.trans_eq === 'yes',
         fast: findClashes(closeUp(compile(a), a.trans_gt === 'yes',
                                   a.trans_eq === 'yes', null))
                 .map(c => [c.a, c.b, c.kind].join('~'))})
"""


def naive_clashes(edges, use_gt, use_eq):
    # Deliberately dumb: no provenance, no pruning, no Floyd-Warshall, just
    # relax until nothing changes. Slow, but obviously correct.
    gt, eq = set(), set()
    for e in edges:
        if e["type"] == "gt":
            gt.add((e["a"], e["b"]))
        else:
            eq.add((e["a"], e["b"]))
            eq.add((e["b"], e["a"]))
    while True:
        add_gt, add_eq = set(), set()
        if use_gt:
            add_gt |= {(a, d) for a, b in gt for c, d in gt if b == c}
        if use_eq:
            add_eq |= {(a, d) for a, b in eq for c, d in eq if b == c}
        if use_gt and use_eq:
            add_gt |= {(a, d) for a, b in eq for c, d in gt if b == c}
            add_gt |= {(a, d) for a, b in gt for c, d in eq if b == c}
        if add_gt <= gt and add_eq <= eq:
            break
        gt |= add_gt
        eq |= add_eq
    out = set()
    for a, b in gt:
        if (b, a) in gt:
            out.add("~".join(sorted((a, b)) + ["cycle"]))
        # A self-loop in gt is already reported as a cycle; labelling the same
        # node gt_and_eq as well would double-count one contradiction.
        if (a, b) in eq and a != b:
            out.add("~".join(sorted((a, b)) + ["gt_and_eq"]))
    return out


def suite_oracle(page, rep, profiles):
    rep.suite("oracle")
    mismatches = 0
    for ans in profiles:
        d = page.evaluate(NAIVE_ORACLE, ans)
        want = naive_clashes(d["edges"], d["useGt"], d["useEq"])
        got = {"~".join(sorted(s.split("~")[:2]) + [s.split("~")[2]])
               for s in d["fast"] if not (s.split("~")[0] == s.split("~")[1]
                                          and s.endswith("gt_and_eq"))}
        if want != got:
            mismatches += 1
            if mismatches <= 3:
                rep.note(f"profile {json.dumps(ans)}\n        missing {want - got}\n        extra {got - want}")
    rep.check(mismatches == 0,
              f"optimised closure agrees with naive fixpoint on {len(profiles)} profiles",
              f"{mismatches} mismatches" if mismatches else "")
    passes = page.evaluate("() => closeUp.PASSES || 0")
    rep.check(passes < 24, "closure reached a fixpoint inside the runaway guard",
              f"max {passes} sweeps needed")


FUZZ_JS = r"""
({seed, cases, qids, pairs, principles, pairValues, principleValues, menuValues}) => {
  const rand = (a => () => { a |= 0; a = a + 0x6D2B79F5 | 0;
      let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296; })(seed);
  const pick = xs => xs[Math.floor(rand() * xs.length)];
  const key  = S => [...S].sort().join('+');
  const fails = [], dist = {};

  for (let i = 0; i < cases; i++) {
    const ans = {};
    pairs.forEach(k => ans[k] = pick(pairValues));
    principles.forEach(k => ans[k] = pick(principleValues));
    ans.menu = pick(menuValues);
    const bad = m => fails.push({case: i, ans, why: m});

    let r;
    try { r = analyse(ans); } catch (e) { bad('threw: ' + e.message); continue; }
    const sets = r.sets;
    dist[sets.length] = (dist[sets.length] || 0) + 1;

    // 1. soundness — every reported set really is unsatisfiable
    for (const S of sets)
      if (!hasClash(ans, S).length) bad('unsound set ' + key(S));

    // 2. minimality — drop any single answer and the contradiction dissolves
    for (const S of sets)
      for (const x of S) {
        const T = new Set([...S].filter(y => y !== x));
        if (hasClash(ans, T).length) bad('non-minimal ' + key(S) + ' without ' + x);
      }

    // 3. irredundancy — no reported set contains another
    for (const S of sets) for (const T of sets)
      if (S !== T && T.size < S.size && [...T].every(x => S.has(x)))
        bad('superset leak ' + key(S) + ' over ' + key(T));

    // 4. completeness — if any clash exists, at least one set is reported
    if (r.clashes.length && !sets.length) bad('clash found but no set reported');

    // 5. determinism
    if (key(analyse(ans).sets.map(key)) !== key(sets.map(key))) bad('non-deterministic');

    // 6. no transitivity, no hits — every contradiction here needs closure
    const flat = analyse(Object.assign({}, ans, {trans_gt: 'no', trans_eq: 'no'}));
    if (flat.sets.length) bad('hit survives with both transitivity principles rejected');

    // 7. monotonicity — refusing to rank a pair can never create a contradiction.
    //    Clash identity is orientation-independent, so normalise the pair.
    const cid = c => [c.a, c.b].sort().join('~') + '~' + c.kind;
    const victim = pick(pairs);
    if (ans[victim] !== 'none') {
      const before = new Set(analyse(ans).clashes.map(cid));
      const after  = analyse(Object.assign({}, ans, {[victim]: 'none'})).clashes.map(cid);
      for (const c of after) if (!before.has(c)) bad('weakening ' + victim + ' created clash ' + c);
    }
    if (fails.length > 40) break;
  }
  return {fails, dist};
}
"""


def suite_fuzz(page, rep, seed, cases):
    rep.suite(f"fuzz  (seed {seed}, {cases} profiles)")
    out = page.evaluate(FUZZ_JS, {
        "seed": seed, "cases": cases, "qids": QIDS, "pairs": PAIRS,
        "principles": PRINCIPLES, "pairValues": PAIR_VALUES,
        "principleValues": PRINCIPLE_VALUES, "menuValues": MENU_VALUES})
    for f in out["fails"][:5]:
        rep.note(f"case {f['case']}: {f['why']}\n        {json.dumps(f['ans'])}")
    rep.check(not out["fails"],
              "soundness, minimality, irredundancy, completeness, determinism, "
              "transitivity-gating and monotonicity hold",
              f"{len(out['fails'])} violations" if out["fails"] else "")
    rep.note("hits per profile: " + json.dumps(out["dist"]))


PROBE_FIGURE = """
() => {
  const f = document.querySelector('.figure');
  if (!f) return null;
  const svg = f.querySelector('svg'), vb = svg.viewBox.baseVal;
  return {
    vbW: vb.width, vbH: vb.height,
    rects: [...svg.querySelectorAll('rect')].map(r => {
      const b = r.getBoundingClientRect();
      return {w: +r.getAttribute('width'), h: +r.getAttribute('height'),
              px: +b.width.toFixed(1), py: +b.height.toFixed(1)};
    }),
    texts: [...svg.querySelectorAll('text')].map(t => {
      const b = t.getBBox(), f = parseFloat(getComputedStyle(t).fontSize);
      // getBBox returns the em box, which for these fonts runs 1.47x the font
      // size and so overlaps between any two normally-leaded lines. The
      // baseline plus a cap-height band is what the eye actually sees.
      const base = t.hasAttribute('y') ? +t.getAttribute('y') : b.y + b.height * 0.76;
      return {s: t.textContent, x1: b.x, x2: b.x + b.width,
              y1: b.y, y2: b.y + b.height,
              ink1: base - f * 0.78, ink2: base + f * 0.24};
    })};
}
"""


def reset(page):
    # The quiz stores its state in the URL fragment, so a plain reload would
    # drop you back where you left off. Every suite that wants a virgin page
    # has to strip the hash.
    page.goto(page.url.split("#")[0])
    page.wait_for_timeout(500)


DONE = "#results:not(.hide) .verdict"

# Kept in step with review_views.py: both need the same view of a profile.
VIEW_PROBE = """(a) => {
  const keep = ANS;
  // Same pruning as showResults, so a catalogue entry cannot be scored on a
  // question the person would never have been shown.
  ANS = Object.assign({}, a);
  pruneInactive();
  const eff = ANS;
  const r = analyse(eff);
  const out = {
    asked: QUESTIONS.filter(q => isActive(q)).map(q => q.id),
    conflicts: r.sets.map(S => [...S].sort())
                .sort((x, y) => x.join().localeCompare(y.join())),
    alpha: !!r.alpha,
    collapse: !!r.collapse,
    zrank: r.zrank ? r.zrank.via : null,
    bullets: bullets().map(b => b.t)
  };
  ANS = keep;
  return out;
}"""


def current_qid(page):
    return page.evaluate("() => QUESTIONS[IDX].id")


def answer(page, clicks, probe=None):
    # Some questions are conditional, so the sequence is not known in advance:
    # read which question is on screen, answer it, and wait for the app to move.
    # Waiting on a state change rather than a sleep avoids racing the 260ms
    # auto-advance. The last question moves to the (optional) namestep screen
    # rather than straight to results, so that counts as having moved too.
    qid = current_qid(page)
    seen = page.evaluate(probe) if probe else None
    page.query_selector_all(".opt")[clicks[qid]].click()
    page.wait_for_function(
        "p => document.querySelector('#results:not(.hide) .verdict')"
        "     || document.querySelector('#namestep:not(.hide)')"
        "     || QUESTIONS[IDX].id !== p", arg=qid, timeout=5000)
    return qid, seen


def pass_namestep(page):
    # The namestep screen sits between the last question and the verdict.
    # Every walk through the quiz passes through it once, name left blank.
    if page.query_selector("#namestep:not(.hide)"):
        page.click("#namenext")
        page.wait_for_selector(DONE, timeout=5000)
        return True
    return False


def walk(page, clicks, probe=None):
    reset(page)
    page.click("#start")
    seen, asked = {}, []
    for _ in range(len(QIDS) + 2):
        if page.query_selector(DONE):
            break
        if pass_namestep(page):
            break
        qid, got = answer(page, clicks, probe)
        asked.append(qid)
        if probe:
            seen[qid] = got
    page.wait_for_selector(DONE, timeout=5000)
    walk.asked = asked
    return seen


def suite_geometry(page, rep):
    rep.suite("geometry")
    reset(page)
    figures = walk(page, CLICK_MODAL, PROBE_FIGURE)
    for qid, d in figures.items():
        if not d:
            continue
        tiny = [r for r in d["rects"] if r["w"] <= 0 or r["h"] <= 0]
        rep.check(not tiny, f"{qid}: no bar with non-positive width or height", str(tiny))
        invisible = [r for r in d["rects"] if r["px"] < 3 or r["py"] < 1.5]
        rep.check(not invisible, f"{qid}: every bar is big enough to see", str(invisible))
        spill = [t["s"] for t in d["texts"]
                 if t["x1"] < -1 or t["x2"] > d["vbW"] + 1 or t["y2"] > d["vbH"] + 1]
        rep.check(not spill, f"{qid}: no label outside the viewBox", str(spill))
        # The ladder once stacked A's and B's captions on top of each other,
        # which no viewBox check would have caught. Compare ink bands, not em
        # boxes: stacked lines always overlap as em boxes and look fine.
        overlaps = []
        for i, a in enumerate(d["texts"]):
            for b in d["texts"][i + 1:]:
                if (min(a["x2"], b["x2"]) - max(a["x1"], b["x1"]) > 1
                        and min(a["ink2"], b["ink2"]) - max(a["ink1"], b["ink1"]) > 1):
                    overlaps.append(f'{a["s"]!r}/{b["s"]!r}')
        rep.check(not overlaps, f"{qid}: no two labels overlap", str(overlaps))
        rep.note(f"{qid}: bars " + ", ".join(f"{r['px']}x{r['py']}" for r in d["rects"]))

    # The added person must be drawn, and captioned, on all three addition cases.
    for qid, caption in [("misery", "Nadia"), ("neutral_mod", "Nadia"),
                         ("neutral_wond", "Nadia")]:
        d = figures[qid]
        rep.check(any(caption == t["s"] for t in d["texts"]),
                  f"{qid}: the added person carries a caption")
        rep.check(len(d["rects"]) == 3, f"{qid}: the added person is drawn as its own bar",
                  f"{len(d['rects'])} bars")

    # Above the knee the blocks stop encoding total welfare as area, so those
    # figures carry a to-scale bar row instead. That row has to be exact.
    scale = page.evaluate("""() => {
      const out = {};
      QUESTIONS.filter(q => q.totals).forEach(q => {
        const svg = new DOMParser().parseFromString(
          popSVG(q.pops, q.names, {totals: true}), 'image/svg+xml').documentElement;
        out[q.id] = {
          bars: [...svg.querySelectorAll('rect')]
                  .filter(r => +r.getAttribute('height') === 16)
                  .map(r => +r.getAttribute('width')),
          totals: q.pops.map(p => p.reduce((a, g) => a + g.n * g.w, 0))};
      });
      return out;
    }""")
    rep.check(set(scale) == {"AvZ", "menu"},
              "the figures that span the knee are the ones carrying to-scale bars",
              str(sorted(scale)))
    for qid, d in scale.items():
        bars, totals = d["bars"], d["totals"]
        rep.check(len(bars) == len(totals), f"{qid}: one to-scale bar per population",
                  f"{len(bars)} bars, {len(totals)} populations")
        biggest = max(range(len(totals)), key=lambda i: totals[i])
        errs = [f"{totals[i]}:{bars[i]:.1f}" for i in range(len(totals))
                if abs(bars[i] / bars[biggest] - totals[i] / totals[biggest]) > 0.01
                and bars[i] > 3.5]
        rep.check(not errs, f"{qid}: bar length is proportional to total welfare", str(errs))
        rep.note(f"{qid}: " + ", ".join(f"{t:,}->{w:.0f}px" for t, w in zip(totals, bars)))
        # The whole point: Z must read as the larger quantity somewhere.
        rep.check(bars[biggest] == max(bars), f"{qid}: the largest total gets the longest bar")

    # Which figures need that row is not a judgement call: below the knee a
    # block's area IS its total welfare, and the row is needed exactly where
    # the squeezed width breaks that. Tagged bars are excluded, since a single
    # person is deliberately drawn oversized so as to stay visible.
    honesty = page.evaluate("""() => {
      const SC = 1.75;
      const ink = p => p.filter(g => !g.tag).reduce((a, g) => a + wpx(g.n) * Math.abs(g.w) * SC, 0);
      const real = p => p.filter(g => !g.tag).reduce((a, g) => a + g.n * Math.abs(g.w), 0);
      return QUESTIONS.filter(q => q.pops).map(q => ({
        id: q.id, totals: !!q.totals,
        err: Math.max(...q.pops.map(p =>
               Math.abs((ink(p) / ink(q.pops[0])) / (real(p) / real(q.pops[0])) - 1)))}));
    }""")
    for f in honesty:
        distorted = f["err"] > 0.15
        rep.note(f"{f['id']}: area error {f['err'] * 100:.1f}%"
                 + (" (to-scale row present)" if f["totals"] else ""))
        rep.check(distorted == f["totals"],
                  f"{f['id']}: carries a to-scale row iff its blocks distort area",
                  f"area error {f['err'] * 100:.0f}%, totals={f['totals']}")

    # Population order must be legible as width: more people, wider bar.
    widths = page.evaluate("() => [1, 100, 200, 500, 1000, 51200].map(wpx)")
    rep.check(all(b > a for a, b in zip(widths, widths[1:])),
              "bar width increases monotonically with headcount",
              " < ".join(f"{w:.0f}" for w in widths))
    rep.check(abs(widths[2] / widths[1] - 2.0) < 0.01,
              "below the knee width is exactly proportional: 2x people is 2x wide",
              f"{widths[2] / widths[1]:.2f}x")
    # A+ splits 200 people into two groups; B keeps them in one. Same headcount
    # must mean same total width, or the diagram contradicts the prompt.
    additive = page.evaluate(
        "() => [wpx(100) * 2, wpx(200), wpx(500) + wpx(1), wpx(501)]")
    rep.check(abs(additive[0] - additive[1]) < 0.01,
              "width is additive: A+ (100+100) is exactly as wide as B (200)",
              f"{additive[0]:.1f} vs {additive[1]:.1f}")
    rep.check(widths[-1] / widths[1] > 5,
              "512x the people still reads as a clearly wider bar",
              f"{widths[-1] / widths[1]:.1f}x")


def suite_layout(page_factory, rep):
    rep.suite("layout")
    for w, h, label in [(1100, 900, "desktop"), (390, 844, "mobile"), (768, 1024, "tablet")]:
        page = page_factory(w, h)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.wait_for_timeout(600)
        worst = page.evaluate("() => document.documentElement.scrollWidth")
        page.click("#start")
        for _ in range(len(QIDS) + 2):
            if page.query_selector(DONE):
                break
            worst = max(worst, page.evaluate("() => document.documentElement.scrollWidth"))
            if pass_namestep(page):
                break
            answer(page, CLICK_MODAL)
        page.wait_for_timeout(900)
        worst = max(worst, page.evaluate("() => document.documentElement.scrollWidth"))
        clipped = page.evaluate(
            "() => [...document.querySelectorAll('.hit,.bullet,.opt,.figure')]"
            ".filter(e => e.scrollWidth > e.clientWidth + 2).length")
        rep.check(worst <= w, f"{label}: no horizontal overflow", f"scrollWidth {worst} vs {w}")
        rep.check(clipped == 0, f"{label}: nothing clipped", f"{clipped} boxes")
        rep.check(not errors, f"{label}: no JS errors", str(errors))
        page.close()


def suite_flow(page, rep):
    rep.suite("flow")
    reset(page)
    page.click("#start")
    page.wait_for_timeout(300)
    page.keyboard.press("a")
    page.wait_for_timeout(400)
    rep.check("QUESTION 2" in page.inner_text("#counter"), "keyboard shortcut advances")
    page.click("#back")
    page.wait_for_timeout(300)
    rep.check(page.eval_on_selector_all(".opt", "e => e.some(x => x.classList.contains('sel'))"),
              "going back restores the previous answer")
    rep.check("QUESTION 1" in page.inner_text("#counter"), "going back moves the counter")

    for name, clicks in [("modal", CLICK_MODAL), ("alpha", CLICK_ALPHA),
                         ("unrankable", CLICK_UNRANKABLE), ("totalist", CLICK_TOTALIST)]:
        reset(page)
        walk(page, clicks)
        hits = len(page.query_selector_all(".hit"))
        bullets = len(page.query_selector_all(".bullet"))
        tally = [e.inner_text() for e in page.query_selector_all(".tally b")]
        rep.check([str(hits), str(bullets)] == tally,
                  f"{name}: headline tally matches the cards rendered",
                  f"cards {hits}/{bullets} vs tally {tally}")
        rows = page.eval_on_selector_all(
            "#results table.rev tr", "rs => rs.map(r => r.cells[1].innerText)")
        rep.check(len(rows) == len(walk.asked),
                  f"{name}: every question asked appears in the summary exactly once",
                  f"{len(rows)} rows for {len(walk.asked)} questions asked")
        rep.check(not [r for r in rows if "undefined" in r or not r.strip()],
                  f"{name}: no blank or undefined summary rows")
        if hits == 0:
            rep.check(bool(page.query_selector(".clean")), f"{name}: clean-crossing card shown")

    # Regression: the summary once printed each principle's affirmative claim
    # regardless of the answer, so rejecting or abstaining was reported as assent.
    AFFIRMATIVE = ["If the very same people all live better lives, that is better.",
                   "Those two verdicts hold identically at every rung of the ladder.",
                   "\u201cBetter than\u201d is transitive.",
                   "\u201cExactly as good as\u201d is transitive."]
    for name, clicks, expect_affirmed in [
            ("rejecting every principle", CLICK_REJECT, False),
            ("declining every pair", CLICK_UNRANKABLE, True)]:
        reset(page)
        walk(page, clicks)
        rows = page.eval_on_selector_all(
            "#results table.rev tr", "rs => rs.map(r => r.cells[1].innerText)")
        echoed = [a for a in AFFIRMATIVE if any(a == r for r in rows)]
        if expect_affirmed:
            rep.check(len(echoed) == len(AFFIRMATIVE),
                      f"{name}: accepted principles are reported as accepted",
                      f"{len(echoed)} of {len(AFFIRMATIVE)}")
        else:
            rep.check(not echoed,
                      f"{name}: summary does not assert principles you rejected", str(echoed))
        rep.check(not [r for r in rows if "undefined" in r or not r.strip()],
                  f"{name}: no blank or undefined summary rows")
        # Raw answer tokens must never reach the page.
        leaked = [r for r in rows
                  if any(t in r for t in ("abstain", "none", "left is", "right is"))]
        rep.check(not leaked, f"{name}: no raw answer values in the summary", str(leaked))

    reset(page)
    page.click("#start")
    counts = {}
    for _ in range(len(QIDS) + 2):
        if page.query_selector(DONE):
            break
        if pass_namestep(page):
            break
        counts[current_qid(page)] = len(page.query_selector_all(".opt"))
        answer(page, CLICK_MODAL)
    page.wait_for_selector(DONE, timeout=5000)
    want = {q: (2 if q in PRINCIPLES else 4) for q in counts}
    rep.check(counts == want, "option counts are as designed", f"{counts} vs {want}")
    # The quiz deliberately has no escape hatch: every answer is a commitment,
    # and "cannot be ranked" is a claim about the outcomes, not about confidence.
    labels = page.evaluate(
        "() => QUESTIONS.map(q => (q.opts || PAIR_OPTS(q)).map(o => o[1] + '|' + o[2]))")
    hatch = [l for qs in labels for l in qs
             if "abstain" in l or "no view" in l.lower() or "know" in l.lower()]
    rep.check(not hatch, "no question offers a don't-know option", str(hatch))

    # The results page is a stop on the walk, not a dead end: back returns to
    # the last question with the answer intact, and forward recomputes.
    walk(page, CLICK_MODAL)
    verdict = page.inner_text("#results .verdict")
    rep.check(bool(page.query_selector("#rback")), "the results page offers a back button")
    page.click("#rback")
    page.wait_for_timeout(400)
    rep.check(current_qid(page) == walk.asked[-1],
              "back from the results returns to the last question asked",
              f"{current_qid(page)} vs {walk.asked[-1]}")
    rep.check(page.eval_on_selector_all(".opt", "e => e.some(x => x.classList.contains('sel'))"),
              "back from the results keeps the last answer selected")
    page.click("#next")
    page.wait_for_selector("#namestep:not(.hide)", timeout=5000)
    page.click("#namenext")
    page.wait_for_selector(DONE, timeout=5000)
    rep.check(page.inner_text("#results .verdict") == verdict,
              "going straight forward again reproduces the same verdict")
    # Changing that answer has to move the engine, or back would be cosmetic.
    page.click("#rback")
    page.wait_for_timeout(400)
    page.query_selector_all(".opt")[2].click()
    page.wait_for_selector("#namestep:not(.hide)", timeout=5000)
    page.click("#namenext")
    page.wait_for_selector(DONE, timeout=5000)
    page.wait_for_timeout(300)
    rep.check(page.inner_text("#results .verdict") != verdict,
              "editing the last answer through back changes the verdict",
              f"still {verdict!r}")

    reset(page)
    walk(page, CLICK_MODAL)
    page.click("#again")
    page.wait_for_timeout(400)
    rep.check("QUESTION 1" in page.inner_text("#counter"), "restart returns to the first question")
    rep.check(not page.eval_on_selector_all(".opt", "e => e.some(x => x.classList.contains('sel'))"),
              "restart clears previous answers")


ROUNDTRIP_JS = """
() => {
  const vals = {pair: ['left', 'right', 'equal', 'none'],
                menu: ['A', 'B', 'Z', 'none'],
                principle: ['yes', 'no']};
  const keep = ANS, bad = [];
  ANS = {};
  if (encodeAns() !== '-'.repeat(QUESTIONS.length)) bad.push('blank profile does not encode to dashes');
  if (Object.keys(decodeAns(encodeAns())).length) bad.push('dashes do not decode to a blank profile');
  QUESTIONS.forEach(q => vals[q.kind].forEach(v => {
    ANS = {}; ANS[q.id] = v;
    const back = decodeAns(encodeAns());
    if (back[q.id] !== v) bad.push(`${q.id}=${v} came back as ${back[q.id]}`);
    if (Object.keys(back).length !== 1) bad.push(`${q.id}=${v} leaked into other questions`);
  }));
  ANS = keep;
  return bad;
}
"""


def suite_share(page, rep):
    rep.suite("share")
    reset(page)
    base = page.url

    rep.check(page.evaluate("() => location.hash") == "", "intro leaves the URL clean")
    bad = page.evaluate(ROUNDTRIP_JS)
    rep.check(not bad, "every answer value survives an encode/decode round trip", str(bad[:4]))

    # Mid-run the fragment must record both the answers so far and the position,
    # so that a reload during development lands back on the same question.
    page.click("#start")
    for i, qid in enumerate(QIDS[:5]):
        page.wait_for_function(
            "n => { const c = document.querySelector('#counter');"
            "       return c && c.textContent.startsWith('Question ' + n + ' of'); }",
            arg=i + 1, timeout=5000)
        page.query_selector_all(".opt")[CLICK_MODAL[qid]].click()
    page.wait_for_timeout(400)
    mid = page.url
    rep.check("&q=6" in mid, "the fragment tracks the current question", mid.split("#")[-1])
    page.goto(mid)
    page.wait_for_timeout(500)
    rep.check("QUESTION 6" in page.inner_text("#counter"),
              "reloading mid-run returns to the same question", page.inner_text("#counter"))
    page.click("#back")
    page.wait_for_timeout(300)
    rep.check(page.eval_on_selector_all(".opt", "e => e.some(x => x.classList.contains('sel'))"),
              "reloading mid-run restores the answers already given")

    # A finished run is a link, and the link reproduces the page exactly.
    walk(page, CLICK_MODAL)
    rep.check(page.url.endswith("&q=r"), "finishing marks the results view in the URL")
    share = page.input_value("#sharelink")
    rep.check("#a=" in share and "&q=" not in share,
              "the share link carries answers and no view marker", share.split("#")[-1])
    original = page.inner_text("#results")

    fresh = page.context.browser.new_page()
    errors = []
    fresh.on("pageerror", lambda e: errors.append(str(e)))
    fresh.goto(share)
    fresh.wait_for_selector("#results .verdict", timeout=5000)
    rep.check(not errors, "opening a share link raises no JS errors", str(errors))
    rep.check(bool(fresh.query_selector(".shared")), "a shared run is labelled as someone else's")
    rep.check(not fresh.query_selector("#rback"),
              "a shared run offers no back button into someone else's answers")
    replayed = fresh.inner_text("#results")
    rep.check(fresh.inner_text("#results .verdict") == page.inner_text("#results .verdict"),
              "the share link reproduces the verdict")
    rep.check(len(fresh.query_selector_all(".hit")) == len(page.query_selector_all(".hit"))
              and len(fresh.query_selector_all(".bullet")) == len(page.query_selector_all(".bullet")),
              "the share link reproduces every conflict and bullet card")
    # inner_text returns what CSS renders, so the chrome comes back uppercased.
    chrome = ("shared results", "take the test", "start over", "\u2190 back")
    strip = lambda t: "\n".join(l for l in t.splitlines()
                                if not any(c in l.lower() for c in chrome))
    rep.check(strip(replayed) == strip(original),
              "the share link reproduces the whole results page")

    # Deep links, including into a question you have not reached.
    blank = "-" * len(QIDS)
    fresh.goto(f"{base}#a={blank}&q=8")
    fresh.wait_for_timeout(400)
    rep.check("QUESTION 8" in fresh.inner_text("#counter"),
              "a bare deep link opens the question it names", fresh.inner_text("#counter"))
    rep.check(not fresh.eval_on_selector_all(".opt", "e => e.some(x => x.classList.contains('sel'))"),
              "a bare deep link selects nothing")

    partial = "".join("y" if q in PRINCIPLES else "l" for q in QIDS[:4]) + "-" * (len(QIDS) - 4)
    fresh.goto(f"{base}#a={partial}")
    fresh.wait_for_timeout(400)
    rep.check("QUESTION 5" in fresh.inner_text("#counter"),
              "a partial profile with no view marker resumes at the first gap",
              fresh.inner_text("#counter"))
    rep.check(bool(fresh.query_selector(".notice")),
              "...and says why it did not go to the results")

    # A verdict is only ever shown over a full set of answers. An unanswered
    # question emits no edges, which is indistinguishable in the closure from a
    # considered "cannot be ranked", so a run with holes in it would score as a
    # confident verdict over answers nobody gave. Every route to the results
    # that can carry holes has to turn back at the first one.
    holed = "y" + "-" * (len(QIDS) - 1)
    fresh.goto(f"{base}#a={holed}&q=r")
    fresh.wait_for_timeout(400)
    rep.check(fresh.evaluate("() => VIEW") == "quiz",
              "asking for the results with answers missing shows no verdict",
              fresh.evaluate("() => VIEW"))
    rep.check("QUESTION 2" in fresh.inner_text("#counter"),
              "...and lands on the first unanswered question", fresh.inner_text("#counter"))
    rep.check(bool(fresh.query_selector(".notice")), "...saying why")
    rep.check("&q=r" not in fresh.url, "...and the view marker leaves the URL", fresh.url)
    rep.check(fresh.evaluate("() => missingActive().length") == len(QIDS) - 3,
              "...counting only the questions that are live",
              str(fresh.evaluate("() => missingActive().length")))

    # Filling the gap returns to the verdict that was asked for, rather than
    # marching back through the answers already given. AvZ is the hole to make
    # here precisely because nothing is conditional on it: the ordinary forward
    # step would land on the next question, so arriving at the results is the
    # turn-back completing its errand and nothing else.
    code = share.split("#a=")[1]
    i = QIDS.index("AvZ")
    fresh.goto(f"{base}#a={code[:i]}-{code[i + 1:]}&q=r")
    fresh.wait_for_timeout(400)
    rep.check(fresh.evaluate("() => QUESTIONS[IDX].id") == "AvZ",
              "one hole in a finished run turns back to exactly that question",
              fresh.evaluate("() => QUESTIONS[IDX].id"))
    fresh.query_selector_all(".opt")[CLICK_MODAL["AvZ"]].click()
    fresh.wait_for_selector("#namestep:not(.hide)", timeout=5000)
    fresh.click("#namenext")
    fresh.wait_for_selector(DONE, timeout=5000)
    rep.check(fresh.inner_text("#results .verdict") == page.inner_text("#results .verdict"),
              "answering it goes straight back to the verdict",
              fresh.inner_text("#results .verdict"))
    fresh.click("#rback")
    fresh.wait_for_timeout(320)
    rep.check(not fresh.query_selector(".notice"),
              "the explanation is spent where it was shown, and does not follow you")

    # A hole can retire a later question, and filling it puts that question
    # back. The run is not finished until that one has an answer either.
    j = QIDS.index("trans_eq")
    fresh.goto(f"{base}#a={code[:j]}-{code[j + 1:]}&q=r")
    fresh.wait_for_timeout(400)
    rep.check(fresh.evaluate("() => ANS.menu_eq") is None,
              "a hole that retires a later question clears that answer too")
    fresh.query_selector_all(".opt")[CLICK_MODAL["trans_eq"]].click()
    fresh.wait_for_function("() => document.querySelector('#results:not(.hide) .verdict')"
                            " || QUESTIONS[IDX].id !== 'trans_eq'", timeout=5000)
    rep.check(fresh.evaluate("() => QUESTIONS[IDX].id") == "menu_eq",
              "filling it turns back again for the question that answer revived",
              fresh.evaluate("() => QUESTIONS[IDX].id"))

    for junk in ["#a=zzzzzzzzzzzz&q=99", "#a=&q=r", "#q=3", "#a=%%%", "#nonsense"]:
        errors.clear()
        fresh.goto(base + junk)
        fresh.wait_for_timeout(300)
        visible = fresh.evaluate(
            "() => ['#intro', '#quiz', '#namestep', '#results']"
            ".filter(s => !document.querySelector(s).classList.contains('hide')).length")
        rep.check(not errors and visible == 1,
                  f"malformed fragment {junk} degrades quietly",
                  f"{len(errors)} errors, {visible} sections visible")

    fresh.close()

    # Starting over must not leave the old answers in the URL.
    walk(page, CLICK_MODAL)
    page.click("#again")
    page.wait_for_timeout(400)
    rep.check(page.url.split("#")[-1].startswith("a=" + "-" * len(QIDS)),
              "starting over clears the answers from the URL", page.url.split("#")[-1])


# neutral_mod 3 = "cannot be ranked"; neutral_wond 1 = "K++ is better"
CLICK_VAGUE = dict(CLICK_MODAL, neutral_mod=3, neutral_wond=1)
# CLICK_MODAL answers both neutral questions "exactly as good", so the
# equalities chain and menu independence is live instead.
CLICK_NO_CHAIN = dict(CLICK_MODAL, trans_eq=1)
# Unrankable with nothing determinate beside it: one edit away from triggering
# the collapsing question, but not triggering it yet.
CLICK_GAP = dict(CLICK_MODAL, neutral_mod=3)


def suite_conditional(page, rep):
    rep.suite("conditional")

    # Each conditional question must appear exactly when it can bite, and the
    # two must gate independently of one another.
    for label, clicks, want in [
            ("unrankable beside a determinate verdict", CLICK_VAGUE, {"collapse"}),
            ("two chaining equalities", CLICK_MODAL, {"menu_eq"}),
            ("equalities that cannot chain", CLICK_NO_CHAIN, set())]:
        walk(page, clicks)
        got = {q for q in CONDITIONAL if q in walk.asked}
        rep.check(got == want, f"{label}: asks {sorted(want) or 'none of them'}",
                  f"asked {sorted(got)}")
        rep.check(len(walk.asked) == len(QIDS) - len(CONDITIONAL) + len(want),
                  f"{label}: quiz length matches", str(len(walk.asked)))

    walk(page, CLICK_VAGUE)
    rep.check(walk.asked.index("collapse") == walk.asked.index("neutral_wond") + 1,
              "the collapsing question follows what it depends on", str(walk.asked))

    # Being asked and biting must not be able to disagree.
    mismatch = page.evaluate("""(profiles) => {
      const keep = ANS, bad = [];
      profiles.forEach(a => {
        ANS = a;
        if (!!collapseCandidate(a) !==
            !!analyse(Object.assign({}, a, {collapse: 'yes'})).collapse) bad.push('collapse');
        // Same contract for the ladder route: shown exactly when saying yes
        // to it would score, and never scored without having been shown.
        const zr = analyse(Object.assign({}, a, {trans_none: 'yes'})).zrank;
        if (zRankLadder(a) !== (!!zr && zr.via === 'ladder')) bad.push('trans_none');
        // Menu independence is live exactly when denying it removes a conflict.
        const withIt = analyse(Object.assign({}, a, {menu_eq: 'yes'})).sets.length;
        const without = analyse(Object.assign({}, a, {menu_eq: 'no'})).sets.length;
        if (!eqChainMatters(a) && withIt !== without) bad.push('menu_eq');
      });
      ANS = keep; return [...new Set(bad)];
    }""", random_profiles(1500, 8181))
    rep.check(not mismatch,
              "each question appears exactly when answering it would matter", str(mismatch))

    # Counter and ticks must describe the quiz actually being taken.
    reset(page)
    page.click("#start")
    seen = []
    for _ in range(len(QIDS) + 2):
        if page.query_selector(DONE):
            break
        if pass_namestep(page):
            break
        seen.append((current_qid(page), page.inner_text("#counter"),
                     len(page.query_selector_all(".tick"))))
        answer(page, CLICK_VAGUE)
    page.wait_for_selector(DONE, timeout=5000)
    bad = [t for t in seen if t[2] != int(t[1].upper().split(" OF ")[1].split(" ")[0])]
    rep.check(not bad, "one progress tick per live question", str(bad))
    rep.check(seen[-1][1].upper().startswith(f"QUESTION {len(seen)} OF {len(seen)}"),
              "the last question is numbered last", seen[-1][1])

    # Going back and retiring an answered question must not leave it scored.
    walk(page, CLICK_VAGUE)
    rep.check("collapsing principle" in page.inner_text("#results").lower(),
              "the collapse conflict is reported when it fires")
    page.click("#rback")
    page.wait_for_timeout(320)
    for _ in range(len(QIDS)):
        if current_qid(page) == "neutral_wond":
            break
        page.click("#back")
        page.wait_for_timeout(300)
    rep.check(current_qid(page) == "neutral_wond",
              "can step back to the question the condition depends on", current_qid(page))
    page.query_selector_all(".opt")[2].click()      # "exactly as good" retires it
    page.wait_for_timeout(400)
    rep.check(current_qid(page) != "collapse",
              "changing the dependency skips the retired question", current_qid(page))
    rep.check(page.evaluate("() => ANS.collapse") is None,
              "the retired answer is discarded, not left in state")
    rep.check(page.evaluate(
        "() => encodeAns()[QUESTIONS.findIndex(q => q.id === 'collapse')]") == "-",
        "the retired answer is cleared from the share link too")

    # The mirror image, and the one with teeth: an edit that brings a question
    # into play leaves a hole in a run that was finished without it. Walking
    # forward asks it, but a "&q=r" URL - the address bar of the results page
    # this run came from - goes straight for the verdict, and must not get one.
    walk(page, CLICK_GAP)
    rep.check("collapse" not in walk.asked, "a run that never triggers the question is not asked it")
    base = page.url.split("#")[0]
    page.click("#rback")
    page.wait_for_timeout(320)
    for _ in range(len(QIDS)):
        if current_qid(page) == "neutral_wond":
            break
        page.click("#back")
        page.wait_for_timeout(300)
    page.query_selector_all(".opt")[1].click()      # "K++ is better" triggers it
    page.wait_for_timeout(400)
    rep.check(page.evaluate("() => isActive(QUESTIONS.find(q => q.id === 'collapse'))"),
              "changing the dependency brings the retired question back")
    page.goto(f"{base}#a={page.evaluate('() => encodeAns()')}&q=r")
    page.wait_for_timeout(400)
    rep.check(current_qid(page) == "collapse" and page.evaluate("() => VIEW") == "quiz",
              "a results link from before the edit turns back to the new question",
              f"{current_qid(page)} / {page.evaluate('() => VIEW')}")
    rep.check(bool(page.query_selector(".notice")), "...with the reason on screen")


def suite_views(page, rep):
    rep.suite("views")
    try:
        from population_ethics_views import VIEWS, EXPECT
    except ImportError:
        rep.check(False, "population_ethics_views.py is importable")
        return

    # Every named view keeps producing what it produced when it was reviewed.
    # The catalogue is the readable artefact; this is the tripwire on it.
    for view in VIEWS:
        key, want = view["key"], EXPECT.get(view["key"])
        if want is None:
            rep.check(False, f"{key}: has a reviewed expectation")
            continue
        got = page.evaluate(VIEW_PROBE, view["answers"])
        rep.check(got["conflicts"] == want["conflicts"], f"{key}: same conflicts",
                  f"{got['conflicts']} vs {want['conflicts']}")
        rep.check(got["alpha"] == want["alpha"] and got["collapse"] == want["collapse"],
                  f"{key}: same choice-consistency cards",
                  f"alpha {got['alpha']}/{want['alpha']}, "
                  f"collapse {got['collapse']}/{want['collapse']}")
        rep.check(got["bullets"] == want["bullets"], f"{key}: same bullets",
                  f"{got['bullets']} vs {want['bullets']}")
        rep.check(got["asked"] == want["asked"], f"{key}: same questions asked",
                  f"{got['asked']} vs {want['asked']}")

    # A view that gives an answer to a question it is never asked would be a
    # sign the catalogue and the conditional logic have drifted apart.
    for view in VIEWS:
        answered = set(view["answers"])
        rep.check(answered == set(QIDS),
                  f"{view['key']}: answers every question in the quiz",
                  str(answered ^ set(QIDS)))

    # The descriptions are prose and cannot be checked mechanically, but a
    # missing one silently removes a view from review.
    thin = [v["key"] for v in VIEWS if len(v["blurb"].split()) < 25]
    rep.check(not thin, "every view carries a description long enough to review",
              str(thin))
    dupes = [v["key"] for v in VIEWS if [w["answers"] for w in VIEWS].count(v["answers"]) > 1]
    rep.check(not dupes, "no two views give identical answers", str(dupes))


# ---------------------------------------------------------------- driver

def random_profiles(n, seed):
    state = seed & 0xFFFFFFFF

    def rnd():
        nonlocal state
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF

    out = []
    for _ in range(n):
        a = {k: PAIR_VALUES[int(rnd() * len(PAIR_VALUES))] for k in PAIRS}
        a.update({k: PRINCIPLE_VALUES[int(rnd() * len(PRINCIPLE_VALUES))]
                  for k in PRINCIPLES})
        a["menu"] = MENU_VALUES[int(rnd() * len(MENU_VALUES))]
        out.append(a)
    return out


def main():
    ap = argparse.ArgumentParser(description="Test the population ethics quiz.")
    ap.add_argument("--file", default="population-ethics-quiz.html")
    ap.add_argument("--suite", default="all",
                    choices=["all", "engine", "oracle", "fuzz", "geometry", "layout",
                             "flow", "share", "conditional", "views"])
    ap.add_argument("--seed", type=int, default=20260723)
    ap.add_argument("--cases", type=int, default=4000)
    ap.add_argument("--oracle-cases", type=int, default=400)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    path = pathlib.Path(args.file).resolve()
    if not path.exists():
        sys.exit(f"no such file: {path}")
    url = "file://" + str(path)
    rep = Report(args.verbose)
    want = lambda s: args.suite in ("all", s)

    with sync_playwright() as p:
        browser = p.chromium.launch()

        def page_factory(w, h):
            pg = browser.new_page(viewport={"width": w, "height": h})
            pg.goto(url)
            return pg

        page = page_factory(1100, 950)
        page.wait_for_timeout(700)

        if want("engine"):
            suite_engine(page, rep)
        if want("oracle"):
            suite_oracle(page, rep, random_profiles(args.oracle_cases, args.seed))
        if want("fuzz"):
            suite_fuzz(page, rep, args.seed, args.cases)
        if want("geometry"):
            suite_geometry(page, rep)
        if want("flow"):
            suite_flow(page, rep)
        if want("share"):
            suite_share(page, rep)
        if want("conditional"):
            suite_conditional(page, rep)
        if want("views"):
            suite_views(page, rep)
        if want("layout"):
            suite_layout(page_factory, rep)

        browser.close()

    print(f"\n{rep.checks} checks run")
    if rep.failures:
        print(f"{len(rep.failures)} FAILED:")
        for f in rep.failures:
            print("  - " + f)
        sys.exit(1)
    print("all passed")


if __name__ == "__main__":
    main()
