"""Named views for reviewing the population ethics quiz.

Originally written by Claude Opus 5.

To regenerate, run

    python review_views.py --file population-ethics-quiz.html -o views-review.md

Each entry pairs a prose description of a position with the answers someone
holding it would give. The point is that the two can be checked against each
other by eye, and against what the quiz then says. `expect` is filled in from
what the engine currently produces, so a diff means either a real regression or
a deliberate change that needs re-reviewing.

The worlds, for working out the answers:
    A    100 people at 100          total  10,000   average 100
    A+   100 at 101 + 100 at 25     total  12,600   average  63
    B    200 people at 64           total  12,800   average  64
    Z    51,200 people at 4         total 204,800   average   4
    K    500 people at 55           total  27,500   average  55
    K-   K plus one life at -40     total  27,460   average  54.81
    K+   K plus one life at   7     total  27,507   average  54.90
    K++  K plus one life at  70     total  27,570   average  55.03

Pair answers are from the first world's point of view: "left" means the first
is better, "right" the second, "equal" exactly as good, "none" unrankable.
    AvB          A  vs B          misery        K vs K-
    benign       A  vs A+         neutral_mod   K vs K+
    nae          A+ vs B          neutral_wond  K vs K++
    AvZ          A  vs Z
"""

# collapse and menu_eq are conditional; give an answer and it is used only if
# the view's other answers make the question come up.
VIEWS = [

    dict(
        key="total",
        name="Total utilitarianism",
        blurb="""Rank outcomes by the sum of wellbeing, with no discount for
            the people being new. Every addition of a life worth living is an
            improvement, and enough of them outweigh any loss in quality, so
            Z beats A and is chosen from the menu. Parfit's own statement of
            the view that generates the Repugnant Conclusion. Internally
            consistent: it is a complete, transitive ordering.""",
        answers=dict(pareto="yes", AvB="right", misery="left", neutral_mod="right",
                     benign="right", nae="right", generalize="yes", AvZ="right",
                     neutral_wond="right", collapse="yes", trans_gt="yes",
                     trans_eq="yes", menu_eq="yes", menu="Z"),
    ),

    dict(
        key="average",
        name="Average utilitarianism",
        blurb="""Rank outcomes by mean wellbeing. A beats B, A+ and Z, since
            all three dilute a population averaging 100. Adding Nadia at 7
            lowers the average and so makes things worse; at 70 it raises the
            average and makes things better. Consistent, but it has to deny
            benign addition, and it implies that a life well worth living can
            be a loss purely for being below par.""",
        answers=dict(pareto="yes", AvB="left", misery="left", neutral_mod="left",
                     benign="left", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="right", collapse="yes", trans_gt="yes",
                     trans_eq="yes", menu_eq="yes", menu="A"),
    ),

    dict(
        key="critical_level",
        name="Critical-level utilitarianism",
        blurb="""Sum wellbeing, but subtract a positive critical level from
            each life, here taken to be 5. Additions above 5 are gains, so the
            ladder's early rungs are accepted; Z's lives at 4 fall below it, so
            Z is worse than A and the moves cannot be repeated indefinitely.
            B is best of the three and is chosen. Blocking the ladder at 'the
            moves repeat' is what saves it, and it is committed to some lives
            worth living being not worth adding.""",
        answers=dict(pareto="yes", AvB="right", misery="left", neutral_mod="right",
                     benign="right", nae="right", generalize="no", AvZ="left",
                     neutral_wond="right", collapse="yes", trans_gt="yes",
                     trans_eq="yes", menu_eq="yes", menu="B"),
    ),

    dict(
        key="maximin",
        name="Maximin",
        blurb="""Rank outcomes by how the worst-off person fares. A beats B,
            A+ and Z, since each has someone below A's floor, and levelling up
            improves things because it raises the floor. Adding Nadia at 7 or
            at -40 lowers the floor and is worse; adding her at 70 leaves the
            floor exactly where it was, so K and K++ come out equally good.
            Worth noting that this does not collide with Pareto here: the
            Pareto question is about the same people, one of them better off,
            and K++ contains a person K does not. So maximin comes out
            consistent, and is told instead what its verdicts commit it to.""",
        answers=dict(pareto="yes", AvB="left", misery="left", neutral_mod="left",
                     benign="left", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="equal", collapse="yes", trans_gt="yes",
                     trans_eq="yes", menu_eq="yes", menu="A"),
    ),

    dict(
        key="asymmetry_menu",
        name="Procreation Asymmetry, menu-dependent",
        blurb="""As above, but the pairwise verdicts are not required to cohere
            into a single ordering. K is exactly as good as K+ and as K++ when
            each pair is considered alone; put all three on the table and K+
            falls below the other two. Denying that a verdict survives a wider
            menu is what lets all three stand. Should escape the neutral-range
            collision and be told it violates Sen's property beta.""",
        answers=dict(pareto="yes", AvB="left", misery="left", neutral_mod="equal",
                     benign="right", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="equal", collapse="yes", trans_gt="yes",
                     trans_eq="yes", menu_eq="no", menu="A"),
    ),

    dict(
        key="asymmetry_equal",
        name="Procreation Asymmetry, strong form",
        blurb="""Common-sense person-affecting view #2. Adding a miserable life
            is bad; adding a happy life is neither good nor bad, taken as
            exactly as good as leaving the person out. Existing people still
            matter, so benign addition and levelling up are both improvements,
            but A > B. Should collide twice over: once on the ladder, and once
            because two lives of very different quality cannot both be exactly
            worth nothing.""",
        answers=dict(pareto="yes", AvB="left", misery="left", neutral_mod="equal",
                     benign="right", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="equal", collapse="yes", trans_gt="yes",
                     trans_eq="yes", menu_eq="yes", menu="A"),
    ),

    dict(
        key="asymmetry_B",
        name="Procreation Asymmetry, prefer greater utility (B > A)",
        blurb="""Common-sense person-affecting view #1. Adding a happy life is
        neither good nor badr. Increasing total utility in a single step is
        good (B > A), but Z is worse than A.""",
        answers=dict(pareto="yes", AvB="right", misery="left", neutral_mod="equal",
                     benign="right", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="equal", collapse="yes", trans_gt="yes",
                     trans_eq="yes", menu_eq="no", menu="B"),
    ),

    dict(
        key="rough",
        name="Imprecise comparability",
        blurb="""Parfit's own way out of the mere addition paradox, and the
            reason he thought it was not a paradox after all. Mere addition is
            not worse than A -- the extra people have lives worth living and
            harm nobody -- but neither is it better, nor exactly as good. A+
            and A are imprecisely comparable, which is Chang's parity applied
            to populations. Levelling up from A+ to B is a clear improvement,
            and A is still better than B and than Z. The chain therefore breaks
            at its first rung rather than at transitivity, and the view should
            come out consistent. Note what the quiz cannot see: Parfit's
            distinctive claim is that 'not worse than' fails to be transitive,
            and there is no question about that relation, so an unrankable
            verdict simply contributes no link.""",
        answers=dict(pareto="yes", AvB="left", misery="left", neutral_mod="none",
                     benign="none", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="none", collapse="no", trans_gt="yes",
                     trans_eq="yes", menu_eq="yes", menu="A"),
    ),

    dict(
        key="vague_boundary",
        name="Unrankable below, better above",
        blurb="""Holds that adding Nadia at 7 does not rank against leaving her
            out, but that adding her at 70 is determinately better, and accepts
            that no hair's improvement to a life can convert 'no fact of the
            matter' into a settled verdict. Those three cannot all stand:
            Broome's collapsing principle is aimed exactly here. The one
            profile in this list that the collapsing question should catch.""",
        answers=dict(pareto="yes", AvB="right", misery="left", neutral_mod="none",
                     benign="right", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="right", collapse="yes", trans_gt="yes",
                     trans_eq="yes", menu_eq="yes", menu="B"),
    ),

    dict(
        key="vague_boundary_ok",
        name="Unrankable below, and boundaries fall where they fall",
        blurb="""The same answers as the previous view, except that a sharp
            boundary between 'unrankable' and 'better' is accepted as the price
            of vagueness. That single change should be the difference between
            being caught by the collapsing principle and not.""",
        answers=dict(pareto="yes", AvB="left", misery="left", neutral_mod="none",
                     benign="right", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="right", collapse="no", trans_gt="yes",
                     trans_eq="yes", menu_eq="yes", menu="A"),
    ),

    dict(
        key="nontransitive",
        name="Non-transitive betterness",
        blurb="""Temkin's and Rachels' position: each rung of the ladder is a
            genuine improvement and A is still better than Z, because
            better-than simply does not chain across changes in what matters.
            Denying transitivity should clear the ladder collisions outright.
            The two neutrality answers are stipulated rather than drawn from
            Temkin, and are here to show the contrast: the remaining collision
            turns on equality, which rejecting transitivity of better-than does
            nothing to touch.""",
        answers=dict(pareto="yes", AvB="left", misery="left", neutral_mod="equal",
                     benign="right", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="equal", collapse="yes", trans_gt="no",
                     trans_eq="yes", menu_eq="yes", menu="A"),
    ),

    dict(
        key="nontransitive-non-independent",
        name="Non-transitive betterness and rejecting independence",
        blurb="""A variation on Temkin's view: avoid asserting that Nadia's wonderful life is equal to her modest life by allowing verdicts to change when the menu changes.""",
        answers=dict(pareto="yes", AvB="left", misery="left", neutral_mod="equal",
                     benign="right", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="equal", collapse="yes", trans_gt="no",
                     trans_eq="yes", menu_eq="no", menu="A"),
    ),

    dict(
        key="antinatalist",
        name="Antinatalism",
        blurb="""Benatar's view: coming into existence is always a harm, so any
            addition makes things worse, whether the life goes badly or
            wonderfully. Among people who exist anyway, more wellbeing is still
            better, so levelling up improves things. Fewer people is better
            without limit, and the best world contains nobody.""",
        answers=dict(pareto="yes", AvB="left", misery="left", neutral_mod="left",
                     benign="left", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="left", collapse="yes", trans_gt="yes",
                     trans_eq="yes", menu_eq="yes", menu="A"),
    ),

    dict(
        key="intuitive-v1",
        name="The untutored intuitive package (A > B)",
        blurb="""Not a philosopher's view but the one many people arrive with.
            More happy people is straightforwardly good, so both of Nadia's
            good lives are worth adding; every step of the ladder looks right;
            better-than obviously chains; and yet A is plainly better than B
            and vastly better than Z. No view about neutrality here at all, so
            the neutral-range collision should not fire - the ladder ones
            should, twice.""",
        answers=dict(pareto="yes", AvB="left", misery="left", neutral_mod="right",
                     benign="right", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="right", collapse="yes", trans_gt="yes",
                     trans_eq="yes", menu_eq="yes", menu="A"),
    ),

    dict(
        key="intuitive-v2",
        name="The untutored intuitive package (B > A)",
        blurb="""Not a philosopher's view but the one many people arrive with (v2).
            More happy people is straightforwardly good, so both of Nadia's
            good lives are worth adding; every step of the ladder looks right;
            better-than obviously chains; B is better than A;
            and yet Z is worse than A or B. No view about neutrality here at all, so
            the neutral-range collision should not fire - the ladder ones
            should, twice.""",
        answers=dict(pareto="yes", AvB="right", misery="left", neutral_mod="right",
                     benign="right", nae="right", generalize="yes", AvZ="left",
                     neutral_wond="right", collapse="yes", trans_gt="yes",
                     trans_eq="yes", menu_eq="yes", menu="B"),
    ),

    dict(
        key="misery_gain",
        name="Suffering counts as a gain",
        blurb="""Included as a check on the quiz rather than as a position
            anyone holds: it says a life of unrelieved agony makes the world
            better by being lived. Almost nothing in the literature goes here,
            and even totalism enters that life as a negative. It should not be
            able to pass without comment.""",
        answers=dict(pareto="yes", AvB="right", misery="right", neutral_mod="right",
                     benign="right", nae="right", generalize="yes", AvZ="right",
                     neutral_wond="right", collapse="yes", trans_gt="yes",
                     trans_eq="yes", menu_eq="yes", menu="Z"),
    ),

    dict(
        key="quietist",
        name="Declining to rank anything",
        blurb="""Answers 'cannot be ranked' to every comparison and rejects
            every structural principle. A boundary case: there is nothing to be
            inconsistent with, so the quiz should find no collisions, and
            should not manufacture one. If this profile ever produces a
            conflict, something is wrong.""",
        answers=dict(pareto="no", AvB="none", misery="none", neutral_mod="none",
                     benign="none", nae="none", generalize="yes", AvZ="none",
                     neutral_wond="none", collapse="no", trans_gt="yes",
                     trans_eq="yes", menu_eq="no", menu="none"),
    ),
]

VIEWS_BY_KEY = {v["key"]: v for v in VIEWS}

# What the engine currently produces for each view, checked by eye against the
# descriptions above. A test asserts these still hold, so a diff means either a
# regression or a change that needs reviewing again. Regenerate with
#     python3 review_views.py --expect

EXPECT = {
    'total': {'conflicts': [], 'alpha': False, 'collapse': False, 'bullets': ['You accepted the repugnant conclusion.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu']},
    'average': {'conflicts': [], 'alpha': False, 'collapse': False, 'bullets': ['You said a life worth living makes the world worse by being lived.', 'Everyone gains, good lives are added, and you called it worse.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu']},
    'critical_level': {'conflicts': [], 'alpha': False, 'collapse': False, 'bullets': ['You said the verdict flips somewhere on the ladder.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu']},
    'maximin': {'conflicts': [], 'alpha': False, 'collapse': False, 'bullets': ['You said a life worth living makes the world worse by being lived.', 'Everyone gains, good lives are added, and you called it worse.', 'You hold the Procreation Asymmetry.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu_eq', 'menu']},
    'asymmetry_equal': {'conflicts': [['AvB', 'benign', 'nae', 'trans_gt'], ['AvZ', 'benign', 'generalize', 'nae', 'trans_gt'], ['menu_eq', 'neutral_mod', 'neutral_wond', 'pareto', 'trans_eq']], 'alpha': False, 'collapse': False, 'bullets': ['You hold the Procreation Asymmetry.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu_eq', 'menu']},
    'asymmetry_menu': {'conflicts': [['AvB', 'benign', 'nae', 'trans_gt'], ['AvZ', 'benign', 'generalize', 'nae', 'trans_gt']], 'alpha': False, 'collapse': False, 'bullets': ['You denied that a verdict survives a wider menu.', 'You hold the Procreation Asymmetry.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu_eq', 'menu']},
    'asymmetry_B': {'conflicts': [['AvZ', 'benign', 'generalize', 'nae', 'trans_gt']], 'alpha': False, 'collapse': False, 'bullets': ['You denied that a verdict survives a wider menu.', 'You hold the Procreation Asymmetry.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu_eq', 'menu']},
    'rough': {'conflicts': [], 'alpha': False, 'collapse': False, 'bullets': ['You judged 3 of the 7 pairs unrankable.', 'You hold the Procreation Asymmetry.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu']},
    'vague_boundary': {'conflicts': [['AvZ', 'benign', 'generalize', 'nae', 'trans_gt']], 'alpha': False, 'collapse': True, 'bullets': ['You hold the Procreation Asymmetry.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'collapse', 'trans_gt', 'trans_eq', 'menu']},
    'vague_boundary_ok': {'conflicts': [['AvB', 'benign', 'nae', 'trans_gt'], ['AvZ', 'benign', 'generalize', 'nae', 'trans_gt']], 'alpha': False, 'collapse': False, 'bullets': ['You hold the Procreation Asymmetry.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'collapse', 'trans_gt', 'trans_eq', 'menu']},
    'nontransitive': {'conflicts': [['menu_eq', 'neutral_mod', 'neutral_wond', 'pareto', 'trans_eq']], 'alpha': False, 'collapse': False, 'bullets': ['You rejected transitivity of better-than.', 'You hold the Procreation Asymmetry.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu_eq', 'menu']},
    'nontransitive-non-independent': {'conflicts': [], 'alpha': False, 'collapse': False, 'bullets': ['You rejected transitivity of better-than.', 'You denied that a verdict survives a wider menu.', 'You hold the Procreation Asymmetry.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu_eq', 'menu']},
    'antinatalist': {'conflicts': [], 'alpha': False, 'collapse': False, 'bullets': ['You said a life worth living makes the world worse by being lived.', 'Everyone gains, good lives are added, and you called it worse.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu']},
    'intuitive-v1': {'conflicts': [['AvB', 'benign', 'nae', 'trans_gt'], ['AvZ', 'benign', 'generalize', 'nae', 'trans_gt']], 'alpha': False, 'collapse': False, 'bullets': [], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu']},
    'intuitive-v2': {'conflicts': [['AvZ', 'benign', 'generalize', 'nae', 'trans_gt']], 'alpha': False, 'collapse': False, 'bullets': [], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu']},
    'misery_gain': {'conflicts': [], 'alpha': False, 'collapse': False, 'bullets': ['You accepted the repugnant conclusion.', 'You counted a life of suffering as a gain.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu']},
    'quietist': {'conflicts': [], 'alpha': False, 'collapse': False, 'bullets': ['You rejected the Pareto principle.', 'You denied that levelling up improves things.', 'You judged none of the seven pairs rankable.'], 'asked': ['pareto', 'AvB', 'misery', 'neutral_mod', 'benign', 'nae', 'generalize', 'AvZ', 'neutral_wond', 'trans_gt', 'trans_eq', 'menu']},
}
