/* ===ENGINE START=== */
/* ---------------------------------------------------------------
   Populations. A population is a list of groups {n, w}: n people
   at lifetime welfare w. 0 = the level at which a life is neither
   good nor bad for the person who lives it.
   --------------------------------------------------------------- */
function buildChain(){
    // Each rung applies two moves to a uniform population n@w:
    //   BENIGN:  everyone gains 1, and n new people appear at floor(w/4)
    //   NAE:     level that off into 2n people, all equal, with strictly
    //            higher total AND higher average than the step before
    var steps=[], n=100, w=100;
    for(var k=0;k<40;k++){
        var lo=Math.floor(w*0.25);
        var plus=[{n:n,w:w+1},{n:n,w:lo}];
        var avg=((w+1)+lo)/2;
        var nw=Math.floor(avg)+1;
        if(nw>=w) break;                       // stop when it stops descending
        steps.push({from:{n:n,w:w}, plus:plus, to:{n:2*n,w:nw}});
        n=2*n; w=nw;
    }
    return steps;
}
var CHAIN=buildChain();
var A_POP =[{n:CHAIN[0].from.n, w:CHAIN[0].from.w}];
var AP_POP=[CHAIN[0].plus[0],{n:CHAIN[0].plus[1].n,w:CHAIN[0].plus[1].w,tag:"the added hundred"}];
var B_POP =[{n:CHAIN[0].to.n,   w:CHAIN[0].to.w}];
var last=CHAIN[CHAIN.length-1].to;
var Z_POP =[{n:last.n, w:last.w}];

var K_BASE=[{n:500,w:55}];
var K_BAD =[{n:500,w:55},{n:1,w:-40,tag:"Nadia"}];
var K_MOD =[{n:500,w:55},{n:1,w:7,tag:"Nadia"}];
var K_WOND=[{n:500,w:55},{n:1,w:70,tag:"Nadia"}];
// One of K's own people harmed, with an addition alongside. K+- holds the same
// 501 people as K++, Owen worse off in it, so Pareto ranks the two; against K,
// which has no Nadia in it, there is no Pareto comparison at all. That missing
// comparison is what the greediness argument turns on.
//
// The addition is the wonderful life rather than the modest one, and that is
// forced rather than chosen. What the argument needs is that the gap the
// addition opens be wide enough to cover Owen's loss, and the only evidence of
// its width is which additions the person called unrankable. Someone who calls
// both the life at 7 and the life at 70 unrankable has told us their range of
// critical levels reaches from 70 down to at least 7, so adding at 70 is worth
// anywhere from nothing to 63 by their own account - which covers 35. Adding at
// 7 would be worth at most 7 to them, and could not cover any harm worth
// drawing.
var K_BOTH=[{n:499,w:55},{n:1,w:20,tag:"Owen"},{n:1,w:K_WOND[1].w,tag:"Nadia"}];

var PARETO_BEFORE=[{n:100,w:50}];
var PARETO_AFTER =[{n:100,w:90}];

/* ---------------------------------------------------------------
   Questions. Three kinds:
   pair      — compare two populations; answer becomes a gt/eq edge
   principle — a yes/no commitment that licenses edges or closure
   menu      — pick the best of three (for contraction consistency)
   --------------------------------------------------------------- */
var QUESTIONS=[
    {
        id:"pareto", kind:"principle", label:"Pareto improvement",
        pops:[PARETO_BEFORE,PARETO_AFTER], names:["Before","After"],
        title:"The same people, all better off.",
        body:"Two futures contain <strong>exactly the same people</strong> \u2014 nobody extra, nobody missing. In the second, <strong>every single one of them has a better life</strong> than they do in the first.",
        ask:"Is the \"After\" future better?",
        opts:[["A","Yes","yes"],["B","No \u2013 they are equal or incomparable","no"]]
    },
    {
        id:"same_number", kind:"pair", label:"The same number, different people",
        // Deliberately the same two populations as the Pareto question, drawn
        // the same way: the figure is identical because what separates the two
        // questions is who the people are, and no arrangement of blocks can
        // show that. It is the only same-number, different-people comparison
        // in the quiz - every other pair changes the headcount - so it is the
        // one place an ordering that declines to rank across changes in who
        // exists has to say so plainly.
        pops:[PARETO_BEFORE,PARETO_AFTER], names:["First","Second"],
        title:"A better-off world, but not the same people.",
        body:"Two futures again, 100 people in each, and again every person in the second is far better off than those in the first. However: <strong>these are not the same people</strong>. Not a single person exists in both — branching futures and butterfly effects led to an entirely different set of people being born."
    },
    {
        id:"AvB", kind:"pair", label:"A against B",
        pops:[A_POP,B_POP], names:["A","B"],
        title:"Two futures, side by side.",
        body:"<strong>A</strong> has 100 people living excellent lives. <strong>B</strong> has 200 people living lives that are less good, but still more than half as good. Nothing else separates them."
    },
    {
        id:"misery", kind:"pair", label:"Adding a life of suffering",
        pops:[K_BASE,K_BAD], names:["K","K\u2212"],
        title:"One more person, and their life is agony.",
        body:"<strong>K</strong> holds 500 people with good lives. <strong>K\u2212</strong> holds those same 500, <strong>completely unaffected</strong>, plus one more person \u2014 call her <strong>Nadia</strong>. Here Nadia\u2019s life contains far more suffering than good: a life it would have been better for <em>her</em> never to have had."
    },
    {
        id:"neutral_mod", kind:"pair", label:"Adding a modest good life",
        pops:[K_BASE,K_MOD], names:["K","K+"],
        title:"The same person, a life worth living.",
        body:"The same <strong>K</strong>, and <strong>the same one person added \u2014 Nadia again</strong>, with everyone else once more <strong>completely unaffected</strong>. In this case, Nadia's life is <strong>clearly worth living</strong>, though it is not a remarkable one."
    },
    {
        id:"benign", kind:"pair", label:"Benign addition",
        pops:[A_POP,AP_POP], names:["A","A+"],
        title:"Everyone gains, and new people arrive.",
        body:"Everyone in <strong>A</strong> also exists in <strong>A+</strong>, and in A+ <strong>each of them is slightly <em>better</em> off</strong>. A+ then <strong>adds 100 further people</strong> whose lives are clearly worth living, though less good than the first hundred\u2019s."
    },
    {
        id:"nae", kind:"pair", label:"Levelling up",
        pops:[AP_POP,B_POP], names:["A+","B"],
        title:"Same population, more total welfare, more equality.",
        body:"<strong>A+</strong> and <strong>B</strong> both hold 200 people. <strong>B has more welfare in total</strong>, more welfare on average, and spreads it perfectly evenly instead of splitting people into a better-off and a worse-off group."
    },
    {
        id:"generalize", kind:"principle", label:"Repeating the moves",
        title:"Now do it again. And again.",
        body:"Repeat the two moves from the last two questions: (1) make everyone slightly better off and create a new group of less-happy people; then (2) keep the same population, but increase both total welfare and equality. Repeat again and again a total of "+CHAIN.length+" times, each new rung making the population larger but less happy.",
        ask:"Would you make those same two judgements at every rung?",
        opts:[["A","Yes \u2014 the same at every rung","yes"],["B","No \u2014 somewhere my verdict flips","no"]],
        chain:true
    },
    {
        id:"AvZ", kind:"pair", label:"A against Z",
        pops:[A_POP,Z_POP], names:["A","Z"], totals:true,
        title:"The far end of the ladder.",
        body:"<strong>A</strong> is where the ladder started: 100 people with excellent lives. <strong>Z</strong> is where it ends: "+last.n.toLocaleString()+" people whose lives are <strong>barely worth living</strong>. Z holds about <strong>20 times more total welfare</strong> than A. <em>The blocks cannot be drawn to scale \u2014 Z\u2019s would be thirty pages wide \u2014 so the bars underneath carry the totals instead.</em>"
    },
    {
        id:"neutral_wond", kind:"pair", label:"Adding a wonderful life",
        pops:[K_BASE,K_WOND], names:["K","K++"],
        title:"The same person, a wonderful life.",
        body:"Nadia once more, added to the same <strong>K</strong>, with everyone else unaffected. The only change is that here her life is a wonderful one \u2014 better than that of anyone already in K."
    },
    {
        id:"collapse", kind:"principle", label:"The collapsing principle",
        // Only worth asking of someone who has left a gap next to a
        // determinate verdict; otherwise there is nothing for it to bite on.
        when:function(a){ return !!collapseCandidate(a); },
        title:"Where does \u201Cno fact of the matter\u201D end?",
        body:function(a){
            var c=collapseCandidate(a);
            var lo=Math.min(c.vague.w,c.anchor.w), hi=Math.max(c.vague.w,c.anchor.w);
            return "This question is here because of two answers you have already given. You said that adding Nadia with <strong>"+
                c.vague.life+"</strong> (wellbeing "+c.vague.w+") <strong>cannot be ranked</strong> against leaving her out \u2014 not better, not worse, not exactly as good. But adding her with <strong>"+
                c.anchor.life+"</strong> (wellbeing "+c.anchor.w+") you ranked determinately: that world is "+
                (c.dir==="up"?"<strong>better</strong>":"<strong>worse</strong>")+
                " than leaving her out. Somewhere between "+lo+" and "+hi+" for her, then, lies a boundary \u2014 a point where a hair\u2019s change to her life, one unit, a single good afternoon, turns \u201Cthere is no fact of the matter\u201D into a settled verdict.";
        },
        ask:"Can so small a change carry so much weight?",
        opts:[["A","No \u2014 so the earlier case was never really unrankable","yes"],
              ["B","Yes \u2014 boundaries have to fall somewhere","no"]]
    },
    {
        id:"greedy", kind:"pair", label:"A harm beside the addition",
        // Nothing here can bite on someone who ranked both additions as plain
        // improvements: the conflicts all run through a verdict that the
        // addition is not a gain, and for a totalist K+- is simply a sum. The
        // question stays live for everyone else, including the person who
        // thinks an addition is bad.
        when:function(a){ return a.neutral_mod!=="right" || a.neutral_wond!=="right"; },
        pops:[K_BASE,K_BOTH], names:["K","K±"],
        title:"One person worse off, one person added.",
        body:"<strong>K</strong> once more, and beside it <strong>K±</strong>, which differs in exactly two ways. First, one person — <strong>Owen</strong>, who is there in both futures — drops from "+K_BASE[0].w+" to "+K_BOTH[1].w+
             ". Second, <strong>Nadia is added at "+K_WOND[1].w+"</strong>: the same wonderful life you were asked about earlier. Nobody else is touched."
    },
    {
        id:"trans_gt", kind:"principle", label:"Transitivity of better-than",
        title:"Better than, and better than again.",
        body:"Take any three futures. Suppose the first is better than the second, and the second is better than the third.",
        ask:"Does it follow that the first is better than the third?",
        opts:[["A","Yes, always","yes"],["B","No, not always","no"]]
    },
    {
        id:"trans_none", kind:"principle", label:"Transitivity of not-worse-than",
        // Only worth asking of someone whose gaps sit on the ladder with a
        // verdict at the end of it: that is the one shape where chaining
        // "not worse than" reaches anything.
        when:function(a){ return !!zRankLadder(a); },
        title:"Not worse than, and not worse than again.",
        body:"Take any three futures. Suppose the first is <strong>not worse than</strong> the second, and the second is not worse than the third. Note that this is weaker than the last question: if two futures cannot be ranked, then the first is not worse than the second.",
        ask:"Does it follow that the first is not worse than the third?",
        opts:[["A","Yes, always","yes"],["B","No, not always","no"]]
    },
    {
        id:"trans_eq", kind:"principle", label:"Transitivity of equal-goodness",
        title:"Exactly as good, twice over.",
        body:"Take any three futures. Suppose the first is exactly as good as the second \u2014 neither better nor worse \u2014 and the second is exactly as good as the third.",
        ask:"Does it follow that the first is exactly as good as the third?",
        opts:[["A","Yes, always","yes"],["B","No, not always","no"]]
    },
    {
        id:"menu_eq", kind:"principle", label:"Verdicts across a wider menu",
        // Pointless unless chaining equalities actually derives something.
        when:function(a){ return eqChainMatters(a); },
        title:"Does a verdict survive a third option arriving?",
        body:"The last question was about the relation <em>exactly as good</em> taken by itself. This one is about where your verdicts came from: every comparison you have made was between <strong>two</strong> futures, weighed on their own. Suppose <strong>A</strong> and <strong>B</strong> come out exactly as good when those are the only options, and <strong>B</strong> and <strong>C</strong> come out exactly as good when <em>those</em> are the only options.",
        ask:"Offered all three at once, must all three be equally good?",
        opts:[["A","Yes \u2014 a verdict does not depend on what else is on offer","yes"],
              ["B","No \u2014 a third option can change how the first two compare","no"]]
    },
    {
        id:"menu", kind:"menu", label:"Choosing from three",
        pops:[A_POP,B_POP,Z_POP], names:["A","B","Z"], totals:true,
        title:"All three at once.",
        body:"The three futures you have already seen, now offered together: <strong>A</strong> with its 100 excellent lives, <strong>B</strong> with its 200 good ones, <strong>Z</strong> with its "+last.n.toLocaleString()+" barely-good ones.",
        ask:"Which is the best of the three?",
        opts:[["A","A","A"],["B","B","B"],["C","Z","Z"],["D","None \u2014 they cannot be ranked","none"]]
    }
];

var PAIR_OPTS=function(q){
    return [
        ["A", q.names[0]+" is better", "left"],
        ["B", q.names[1]+" is better", "right"],
        ["C", "Exactly as good as each other", "equal"],
        ["D", "Neither — they cannot be ranked", "none"]
    ];
};

/* ---------------------------------------------------------------
   Compile answers into edges.
   Every edge carries the set of answer-ids that licence it.
   --------------------------------------------------------------- */
function compile(ans){
    var E=[]; // {type:'gt'|'eq'|'ne', a, b, sup:[ids]}
    function edge(type,a,b,sup){ E.push({type:type,a:a,b:b,sup:sup}); }
    function fromPair(qid,A,B,sup){
        var v=ans[qid]; if(!v||v==="abstain") return;
        if(v==="left")  edge("gt",A,B,sup);
        if(v==="right") edge("gt",B,A,sup);
        if(v==="equal") edge("eq",A,B,sup);
        // "Cannot be ranked" is a claim, not a silence: not better, not worse,
        // not equal. It licenses no relation and chains with nothing, so it
        // never helps derive anything - but if the rest of the answers derive
        // a relation between these two worlds anyway, the person has denied
        // and asserted the same thing, and findClashes says so. Without this
        // edge "unrankable" was invisible to the closure, and an ordering
        // could decline a pair its own commitments already settled.
        if(v==="none")  edge("ne",A,B,sup);
    }

    fromPair("AvB","A","B",["AvB"]);
    fromPair("AvZ","A","Z",["AvZ"]);
    fromPair("misery","K","K-",["misery"]);
    fromPair("neutral_mod","K","K+",["neutral_mod"]);
    fromPair("neutral_wond","K","K++",["neutral_wond"]);
    fromPair("greedy","K","K±",["greedy"]);

    // Rung 0 of the ladder, stated directly.
    fromPair("benign","A","A+",["benign"]);
    fromPair("nae","A+","B",["nae"]);

    // Rungs 1..n-1, licensed only if the verdicts generalise.
    if(ans.generalize==="yes"){
        for(var k=1;k<CHAIN.length;k++){
            var p="P"+k, pp="P"+k+"+", nx="P"+(k+1);
            if(k===1){ p="B"; }
            if(k+1===CHAIN.length){ nx="Z"; }
            fromPair("benign",p,pp,["benign","generalize"]);
            fromPair("nae",pp,nx,["nae","generalize"]);
        }
    }

    // Pareto ranks the three versions of Nadia's life against each other
    // directly: the same 501 people throughout, one of them better off.
    if(ans.pareto==="yes"){
        edge("gt","K++","K+",["pareto"]);
        edge("gt","K+","K-",["pareto"]);
        edge("gt","K++","K-",["pareto"]);
        // K+- has the same 501 people as K++, with Owen worse off and nobody
        // better, so Pareto ranks it below. This is what makes Owen's loss a
        // loss on the person's own accounting. Against K+ and K- it says
        // nothing - Nadia is better off in K+- and Owen worse - and against K
        // it says nothing either, which is the whole difficulty.
        edge("gt","K++","K±",["pareto"]);
    }

    return E;
}

/* ---------------------------------------------------------------
   Closure + contradiction search.
   --------------------------------------------------------------- */
function unite(a,b,extra){
    var s=new Set(a); b.forEach(function(x){s.add(x);});
    if(extra){
        if(typeof extra==="string") s.add(extra);
        else extra.forEach(function(x){ s.add(x); });
    }
    return s;
}

function closeUp(edges, useGt, useEq, allowed, eqTags){
    // eqTags: what to charge a step that consumes an equality verdict. Always
    // "trans_eq"; also "menu_eq" once the person has been asked whether a
    // verdict reached between two options survives a third joining them.
    eqTags = eqTags || ["trans_eq"];
    // allowed: null, or a Set of answer-ids we are permitted to draw on.
    // Each cell holds the smallest support set found for that relation.
    function supOK(list){
        if(!allowed) return true;
        for(var i=0;i<list.length;i++) if(!allowed.has(list[i])) return false;
        return true;
    }
    function setOK(s){
        if(!allowed) return true;
        var good=true; s.forEach(function(x){ if(!allowed.has(x)) good=false; });
        return good;
    }
    var idx={}, names=[];
    function id(n){ if(!(n in idx)){ idx[n]=names.length; names.push(n); } return idx[n]; }
    edges.forEach(function(e){ if(supOK(e.sup)){ id(e.a); id(e.b); } });

    var N=names.length, gt=[], eq=[], ne=[], i, j, k;
    for(i=0;i<N;i++){
        gt.push(new Array(N).fill(null));
        eq.push(new Array(N).fill(null));
        ne.push(new Array(N).fill(null));
    }
    function better(cur,cand){ return !cur || cand.size<cur.size; }

    edges.forEach(function(e){
        if(!supOK(e.sup)) return;
        var a=idx[e.a], b=idx[e.b];
        if(e.type==="gt"){
            var s=new Set(e.sup); if(better(gt[a][b],s)) gt[a][b]=s;
        } else if(e.type==="ne"){
            // Symmetric, and deliberately inert: a denial licenses nothing, so
            // it takes no part in the sweep below and can only ever collide.
            var n1=new Set(e.sup); if(better(ne[a][b],n1)) ne[a][b]=n1;
            var n2=new Set(e.sup); if(better(ne[b][a],n2)) ne[b][a]=n2;
        } else {
            var s1=new Set(e.sup); if(better(eq[a][b],s1)) eq[a][b]=s1;
            var s2=new Set(e.sup); if(better(eq[b][a],s2)) eq[b][a]=s2;
        }
    });

    // Mixed-relation closure does not always settle in a single
    // Floyd-Warshall sweep, so sweep to a genuine fixpoint. The cap is only
    // a runaway guard; PASSES records what was actually needed.
    for(var pass=0;pass<24;pass++){
        var dirty=false;
        for(k=0;k<N;k++) for(i=0;i<N;i++){
            if(!gt[i][k] && !eq[i][k]) continue;
            for(j=0;j<N;j++){
                var c;
                if(useGt && gt[i][k] && gt[k][j]){
                    c=unite(gt[i][k],gt[k][j],"trans_gt");
                    if(setOK(c)&&better(gt[i][j],c)){ gt[i][j]=c; dirty=true; }
                }
                if(useEq && eq[i][k] && eq[k][j]){
                    c=unite(eq[i][k],eq[k][j],eqTags);
                    if(setOK(c)&&better(eq[i][j],c)){ eq[i][j]=c; dirty=true; }
                }
                if(useGt && useEq && eq[i][k] && gt[k][j]){
                    c=unite(eq[i][k],gt[k][j],eqTags); c.add("trans_gt");
                    if(setOK(c)&&better(gt[i][j],c)){ gt[i][j]=c; dirty=true; }
                }
                if(useGt && useEq && gt[i][k] && eq[k][j]){
                    c=unite(gt[i][k],eq[k][j],eqTags); c.add("trans_gt");
                    if(setOK(c)&&better(gt[i][j],c)){ gt[i][j]=c; dirty=true; }
                }
            }
        }
        if(!dirty) break;
        closeUp.PASSES=Math.max(closeUp.PASSES||0, pass+2);
    }
    return {gt:gt,eq:eq,ne:ne,names:names,N:N};
}

function findClashes(M){
    var out=[];
    // Pair names are sorted so a clash has one canonical identity regardless of
    // the order nodes were registered in.
    function emit(kind,a,b,sup){
        var p=[M.names[a],M.names[b]].sort();
        out.push({kind:kind,a:p[0],b:p[1],sup:sup});
    }
    for(var i=0;i<M.N;i++){
        if(M.gt[i][i]) emit("cycle",i,i,new Set(M.gt[i][i]));
        for(var j=0;j<M.N;j++){
            if(i===j) continue;
            if(i<j && M.gt[i][j] && M.gt[j][i]) emit("cycle",i,j,unite(M.gt[i][j],M.gt[j][i]));
            if(M.gt[i][j] && M.eq[i][j])        emit("gt_and_eq",i,j,unite(M.gt[i][j],M.eq[i][j]));
            // A pair called unrankable whose relation the other answers settle
            // anyway. One emit per direction of the relation found, which the
            // pair-name sort collapses to one clash identity.
            if(M.ne[i][j] && M.gt[i][j])        emit("denied",i,j,unite(M.ne[i][j],M.gt[i][j]));
            if(i<j && M.ne[i][j] && M.eq[i][j]) emit("denied",i,j,unite(M.ne[i][j],M.eq[i][j]));
        }
    }
    return out;
}

var _memo=null;
function setKey(s){ return s? Array.from(s).sort().join(","):"*"; }
function ansKey(a){ return QUESTIONS.map(function(q){ return a[q.id]||"-"; }).join("|"); }

function hasClash(ans, allowedSet){
    // The cache is keyed on the profile too: allowedSet alone is not a
    // sufficient key, since the same subset means different things for
    // different answers.
    var fp=ansKey(ans);
    if(!_memo || _memo.fp!==fp) _memo={fp:fp, c:{}};
    var mk=setKey(allowedSet);
    if(mk in _memo.c) return _memo.c[mk];
    var useGt = ans.trans_gt==="yes" && (!allowedSet || allowedSet.has("trans_gt"));
    // Chaining equalities takes verdicts reached in separate two-way
    // comparisons and combines them, which is exactly what menu independence
    // licenses. Only charge it to people who were actually asked.
    var eqTags = ans.menu_eq===undefined ? ["trans_eq"] : ["trans_eq","menu_eq"];
    var useEq = ans.trans_eq==="yes" && ans.menu_eq!=="no" &&
                (!allowedSet || eqTags.every(function(t){ return allowedSet.has(t); }));
    var res=findClashes(closeUp(compile(ans),useGt,useEq,allowedSet||null,eqTags));
    _memo.c[mk]=res;
    return res;
}

// Brute-force reduction of a blame set to its minimal unsatisfiable subsets.
function minimise(ans, sup){
    var arr=Array.from(sup), n=arr.length, found=[];
    for(var size=1;size<=n;size++){
        var idx=[];
        (function rec(start,pick){
            if(pick.length===size){
                var S=new Set(pick.map(function(i){return arr[i];}));
                // skip if it contains an already-found minimal set
                for(var f=0;f<found.length;f++){
                    var sub=true; found[f].forEach(function(x){ if(!S.has(x)) sub=false; });
                    if(sub) return;
                }
                if(hasClash(ans,S).length) found.push(S);
                return;
            }
            for(var i=start;i<n;i++){ pick.push(i); rec(i+1,pick); pick.pop(); }
        })(0,idx);
        // Sizes are scanned in order, so the first size that yields anything
        // yields every minimal set reachable inside this blame set.
        if(found.length) break;
    }
    return found;
}

/* ---------------------------------------------------------------
   Two questions are worth asking only of certain people, so each needs a
   relevance test. Both are defined here, beside the checks they gate, because
   a question that appears when it cannot bite - or bites without having been
   asked - is worse than either behaviour alone.
--------------------------------------------------------------- */
var NADIA_LEVELS=[
    {id:"misery",       w:K_BAD[1].w,  world:"K\u2212", life:"a life of agony"},
    {id:"neutral_mod",  w:K_MOD[1].w,  world:"K+",       life:"a modest good life"},
    {id:"neutral_wond", w:K_WOND[1].w, world:"K++",      life:"a wonderful life"}
];
// The collapsing principle needs an unrankable verdict with a determinate one
// beside it: something for the indeterminacy to collapse into.
function collapseCandidate(ans){
    for(var li=0; li<NADIA_LEVELS.length; li++){
        for(var hi=li+1; hi<NADIA_LEVELS.length; hi++){
            var lo=NADIA_LEVELS[li], up=NADIA_LEVELS[hi];
            // The principle turns on the boundary between the two levels being
            // arbitrary. Across welfare 0 it is not: that is the neutral level
            // itself, and locating the change there is exactly what the
            // Procreation Asymmetry does. Only compare levels on one side.
            if((lo.w<0) !== (up.w<0)) continue;
            if(ans[lo.id]==="none" && ans[up.id]==="right")
                return {vague:lo, anchor:up, dir:"up"};
            if(ans[up.id]==="none" && ans[lo.id]==="left")
                return {vague:up, anchor:lo, dir:"down"};
        }
    }
    return null;
}

/* ---------------------------------------------------------------
   Ranking Z while declining to rank the steps that lead to it.

   Two ways to get there, and they are not equally strong.

   The ladder route is Parfit's own argument run on "not worse than" rather
   than "better than", which is what lets it pass through a gap. Being
   unrankable, A+ is not worse than A; B is better than A+, so B is not worse
   than A+ either. Chain that down every rung and Z is not worse than A - but
   judging A better than Z says Z is worse than A. Nothing about neutral
   ranges or numbers is needed, only the chaining, which is why it is scored
   only against someone who has been asked for it and said yes. Parfit's
   answer was no: his claim is precisely that "not worse than" does not chain,
   and that is why he thought mere addition was no paradox.

   The misery route has no chain to run on and rests on a reading instead:
   take a neutral range as Broome does, a range of critical levels shared by
   every addition, a comparison coming out determinate only when it holds at
   every level in the range. Then A vs Z turns over at 3.81, just under Z's
   people at welfare 4, so ranking A above Z says every level you entertain
   sits above 4 - while calling the addition of a life at -40 unrankable puts
   one down at -40. The card says out loud that this one assumes the reading.

   Neither is visible to the closure, which never sees an unrankable verdict.
   What is no conflict at all is a gap at the top of the ladder with the
   verdict flipping partway down: the chain breaks where it flips. bullets()
   covers that case instead.
--------------------------------------------------------------- */
var Z_LEVEL=Z_POP[0].w;
// Split out so the trans_none question can gate on the same shape it scores.
// "Not worse than" needs every link: an unrankable benign step, a levelling
// step that is not a step down, and the repetition that carries both to Z.
function zRankLadder(ans){
    return ans.AvZ==="left" && ans.benign==="none" &&
           ans.nae!=="left" && ans.generalize==="yes";
}
function zRankCandidate(ans){
    // Only a determinate "A is better" makes the claim. Ranking Z above A is
    // consistent with any range whose levels all sit below Z.
    if(ans.AvZ!=="left") return null;
    if(zRankLadder(ans) && ans.trans_none==="yes")
        return {via:"ladder", level:Z_LEVEL,
                ids:["AvZ","benign","nae","generalize","trans_none"]};
    if(ans.misery==="none")
        return {via:"misery", level:K_BAD[1].w, ids:["AvZ","misery"]};
    return null;
}

// Menu independence only bites if chaining equalities derives something.
// Rather than enumerate the cases, run the closure both ways and see whether
// any relation appears only when the chaining is allowed.
function eqChainMatters(ans){
    if(ans.trans_eq!=="yes") return false;
    var E=compile(ans), useGt=ans.trans_gt==="yes";
    var on=closeUp(E,useGt,true,null), off=closeUp(E,useGt,false,null);
    for(var i=0;i<on.N;i++) for(var j=0;j<on.N;j++){
        if(on.gt[i][j] && !off.gt[i][j]) return true;
        if(on.eq[i][j] && !off.eq[i][j]) return true;
    }
    return false;
}

/* ---------------------------------------------------------------
   Broome's greediness of neutrality, checked outside the closure for the same
   reason as the collapsing principle: the verdict it needs - that adding
   Nadia leaves K and K++ beyond ranking - emits no edge, so nothing the closure
   can see is disturbed by what follows it.

   The dilemma only exists for the weak form. Someone who calls the addition
   exactly as good as leaving her out already has Pareto's K++ > K+- to chain
   with, and so derives K > K+- rather than helping themselves to it; if they
   then rank K+- level with K or above it, that is an ordinary cycle and the
   closure catches it. Someone who calls the addition unrankable derives
   nothing, and a determinate K > K+- is a claim about how wide their own gap is.

   Which is why both neutrality answers are required, and it is not caution.
   Greediness is a claim about width: a gap swallows a harm only if the addition
   could be worth more than the harm. Read the gaps as a range of critical
   levels, and calling the life at 70 unrankable puts a level at or above 70,
   while calling the life at 7 unrankable puts one at or below 7 - so adding at
   70 is worth anywhere from nothing to 63 on the person's own account, and
   Owen's 35 sits inside that. One answer alone fixes only one end of the range
   and leaves the width unknown, and a range that stops just short of Nadia's
   own level swallows nothing at all. The reading is stated on the card; it is
   the same one the misery route above assumes.
--------------------------------------------------------------- */
function greedyCandidate(ans){
    // Both, and for the width rather than for emphasis: see above.
    if(ans.neutral_mod!=="none" || ans.neutral_wond!=="none") return null;
    if(ans.greedy!=="left") return null;        // ...ranked determinately anyway
    if(ans.pareto!=="yes") return null;         // ...with the harm counting as one
    return {level:K_WOND[1].w, floor:K_MOD[1].w, from:K_BASE[0].w, to:K_BOTH[1].w};
}

/* ---------------------------------------------------------------
   The checks that run outside the closure. Each is a different reason a set of
   answers can be in trouble without any pair of outcomes being ranked in both
   directions at once, which is the only thing the closure can see:

     alpha     a choice from three that reverses a choice from two
     collapse  a gap with a determinate verdict one welfare unit away
     zrank     a gap on the ladder with Z ranked at the end of it
     greedy    a gap wide enough to swallow a harm, with the harm ranked anyway

   They are listed rather than written out one after another because each one
   used to be wired into five places - the analyse return, the headline tally,
   the card's number, and both of the probes the tests and the catalogue run.
   Numbering a card by hand is what makes a fifth check expensive: every earlier
   card's number has to learn about it. Here a check is an entry, its card is an
   entry in CARD_HTML beside the other cards, and nothing counts anything.
--------------------------------------------------------------- */
function alphaCandidate(ans){
    var declined=function(v){ return !v||v==="none"||v==="abstain"; };
    if(declined(ans.menu)) return null;
    var pick=ans.menu;
    // Picking Z from the three while ranking A above Z in the pair is a
    // violation on its own terms. It turns on AvZ, not AvB, so it must not be
    // gated behind AvB: an incomparabilist who declines A against B would
    // otherwise walk through it.
    if(pick==="Z" && ans.AvZ==="left")
        return {picked:"Z", pairWinner:"A", third:"B", viaZ:true};
    if(declined(ans.AvB)) return null;
    var pairWinner = ans.AvB==="left" ? "A" : ans.AvB==="right" ? "B" : "tie";
    if((pick==="A"||pick==="B") && pairWinner!=="tie" && pick!==pairWinner)
        return {picked:pick, pairWinner:pairWinner, third:"Z"};
    return null;
}

var EXTRA_CHECKS=[
    // Contraction consistency (Sen's property alpha): a constraint on choice
    // rather than on the betterness ordering.
    {id:"alpha", run:alphaCandidate},
    // Broome's collapsing principle (Weighing Lives ch. 12). Asked before it is
    // scored, so an unasked or rejected principle cannot bite.
    {id:"collapse", run:function(a){ return a.collapse==="yes" ? collapseCandidate(a) : null; }},
    {id:"zrank", run:zRankCandidate},
    {id:"greedy", run:greedyCandidate}
];

// Each check's result under its own name, plus the list of the ones that
// fired, in order. Callers that want one check ask for it by name; callers
// that want to count or render them all walk the list and stay correct when
// the list grows.
function runExtras(ans, into){
    var out=[];
    EXTRA_CHECKS.forEach(function(c){
        var d=c.run(ans) || null;
        into[c.id]=d;
        if(d) out.push({id:c.id, data:d});
    });
    return out;
}

function analyse(ans){
    var clashes=hasClash(ans,null);

    // A single long cycle yields one clash per pair of nodes on it, but they
    // collapse to a handful of distinct blame sets. Minimise each set once.
    var blames=[], bseen={};
    clashes.forEach(function(c){
        var k=setKey(c.sup);
        if(!bseen[k]){ bseen[k]=1; blames.push(c.sup); }
    });

    var sets=[], seen={};
    blames.forEach(function(sup){
        minimise(ans,sup).forEach(function(S){
            var key=setKey(S);
            if(!seen[key]){ seen[key]=1; sets.push(S); }
        });
    });
    // drop any set that strictly contains another
    sets=sets.filter(function(S){
        return !sets.some(function(T){
            if(T===S||T.size>=S.size) return false;
            var sub=true; T.forEach(function(x){ if(!S.has(x)) sub=false; });
            return sub;
        });
    });

    var out={sets:sets, clashes:clashes};
    out.extras=runExtras(ans, out);
    return out;
}
/* ===ENGINE END=== */

/* =============== UI =============== */
var ANS={}, IDX=0, VIEW="intro", SHARED=false;
// Optional, given on the namestep screen just before results. Never required,
// never decoded from a share link - it travels only in the /log POST.
var NAME="";
// Set when a request for the results was turned back for want of an answer;
// rendered on the question it was turned back to, then spent.
var NOTICE="";
// True between such a turn-back and the verdict it was headed for, so that
// filling the gaps returns there instead of marching through the answers
// already given on the way.
var RETURNING=false;
var $=function(s){return document.querySelector(s);};

/* ---------------------------------------------------------------
   State lives in the URL fragment: one character per question, plus
   which screen you are on. Three things fall out of that — a refresh
   keeps your place, a finished run is a link you can send, and
   #a=------------&q=7 jumps straight to question 7.
   --------------------------------------------------------------- */
var CODES={
    pair: {left:"l", right:"r", equal:"e", none:"n"},
    menu: {A:"a", B:"b", Z:"z", none:"n"},
    principle: {yes:"y", no:"x"}
};
var DECODES={};
Object.keys(CODES).forEach(function(k){
    DECODES[k]={};
    Object.keys(CODES[k]).forEach(function(v){ DECODES[k][CODES[k][v]]=v; });
});

function encodeAns(){
    return QUESTIONS.map(function(q){
        var m=CODES[q.kind], v=ANS[q.id];
        return (v!==undefined && m[v]) ? m[v] : "-";
    }).join("");
}
function decodeAns(code){
    var out={};
    // One character per question, positionally. A link made before a question
    // was added or removed would decode shifted, so refuse it outright.
    if(code.length!==QUESTIONS.length) return out;
    QUESTIONS.forEach(function(q,i){
        var v=DECODES[q.kind][code.charAt(i)];
        if(v!==undefined) out[q.id]=v;
    });
    return out;
}

/* ---------------------------------------------------------------
   Optional response logging. On a genuine completion - not a shared
   link being replayed - POST the answers to the server, which appends
   one line to a log file. Most of what's identifying (IP, user-agent, the
   arrival time) is filled in server-side; the client sends the answers and,
   if the person chose to give one on the namestep screen, a name - the one
   piece of identity the server can't infer, and the only way to recognize
   the same person across devices instead of just across a shared IP.
   Best-effort: if there is no endpoint (opened from disk, or served by a
   plain static host) the request just fails and the quiz carries on.
   Nothing here blocks rendering or touches the UI.

   LOG_ENDPOINT is resolved relative to the page, so it lands on the
   same origin whether the quiz sits at "/" or a subpath. Set it to ""
   to switch logging off, or to an absolute URL to point elsewhere.
--------------------------------------------------------------- */
var LOG_ENDPOINT="log";
var LOGGED=false;
function logAnswers(){
    // Once per run; never a replay; never a run with holes in it, which the
    // deep links make reachable and which would silently skew the corpus.
    if(LOGGED || SHARED || !LOG_ENDPOINT || missingActive().length) return;
    LOGGED=true;
    var payload={ code:encodeAns(), answers:ANS, page:baseURL() };
    if(NAME) payload.name=NAME;
    try{
        // keepalive lets the POST finish even if the tab is closed right after.
        fetch(LOG_ENDPOINT,{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify(payload),
            keepalive:true
        }).catch(function(){});   // no backend (static host / file://) - ignore
    }catch(e){}
}

var LASTHASH="";
function fragment(){
    if(VIEW==="intro") return "";
    return "#a="+encodeAns()+"&q="+(VIEW==="results"?"r":IDX+1);
}
function baseURL(){ return location.href.split("#")[0]; }
function shareURL(){ return baseURL()+"#a="+encodeAns(); }
function syncHash(){
    var frag=fragment();
    if(frag===LASTHASH && location.hash===frag) return;
    LASTHASH=frag;
    // file:// URLs reject some history writes, so fall back to a same-document
    // replace, which also leaves the back button alone.
    try{ history.replaceState(null,"",baseURL()+frag); }
    catch(e){ location.replace(baseURL()+frag); }
}
function readHash(){
    var h=location.hash.replace(/^#/,""), out={};
    if(!h) return null;
    h.split("&").forEach(function(kv){
        var i=kv.indexOf("="), raw=kv.slice(i+1);
        if(i<1) return;
        // A hand-edited fragment can carry a broken escape; take it literally
        // rather than throwing on the way in.
        try{ out[kv.slice(0,i)]=decodeURIComponent(raw); }
        catch(e){ out[kv.slice(0,i)]=raw; }
    });
    return (out.a!==undefined || out.q!==undefined) ? out : null;
}

function show(view){
    VIEW=view;
    $("#intro").classList.toggle("hide", view!=="intro");
    $("#quiz").classList.toggle("hide", view!=="quiz");
    $("#namestep").classList.toggle("hide", view!=="namestep");
    $("#results").classList.toggle("hide", view!=="results");
}

/* ---------------------------------------------------------------
   Conditional questions. IDX still indexes QUESTIONS, so a "&q=" deep link
   means the same thing whatever else you answered; navigation steps over the
   inactive ones and the counter reports position among the live ones.
--------------------------------------------------------------- */
function isActive(q){ return !q.when || q.when(ANS); }
function activeIdx(){
    var out=[];
    QUESTIONS.forEach(function(q,i){ if(isActive(q)) out.push(i); });
    return out;
}
// Changing an earlier answer can retire a question that was already answered;
// leaving that answer behind would put a claim in the summary, and possibly in
// a conflict, that the person was never actually shown.
function pruneInactive(){
    QUESTIONS.forEach(function(q){ if(!isActive(q)) delete ANS[q.id]; });
}
function stepTo(i,dir){
    var A=activeIdx();
    for(var k=0;k<A.length;k++){
        if(dir>0 && A[k]>=i) return A[k];
        if(dir<0 && A[A.length-1-k]<=i) return A[A.length-1-k];
    }
    return dir>0 ? A[A.length-1] : A[0];
}

// Which live questions have no answer behind them. An unanswered question emits
// no edges, which the closure cannot tell apart from a considered "cannot be
// ranked" - so a run with gaps in it would score as a confident verdict over
// answers nobody gave. showResults is gated on this coming back empty.
function missingActive(){
    return activeIdx().filter(function(i){ return ANS[QUESTIONS[i].id]===undefined; });
}
function firstUnanswered(){
    var m=missingActive();
    if(m.length) return m[0];
    var A=activeIdx();
    return A[A.length-1];
}

function boot(){
    var p=readHash();
    RETURNING=false;                 // a fresh navigation is not a turn-back
    if(!p){ ANS={}; IDX=0; SHARED=false; NAME=""; show("intro"); LASTHASH=""; return; }
    ANS=decodeAns(p.a||"");
    pruneInactive();
    var n=parseInt(p.q,10);
    // Both forms of "show me the results" - the view marker, and the share link,
    // which carries answers and no marker at all - go through showResults, which
    // turns back at the first gap rather than scoring one.
    if(p.q==="r" || p.q===undefined){
        // No &q on a complete profile means the link came from someone else.
        SHARED = p.q===undefined && !missingActive().length;
        IDX=stepTo(QUESTIONS.length-1,-1);
        showResults();
        return;
    }
    SHARED=false;
    IDX = (n>=1 && n<=QUESTIONS.length) ? stepTo(n-1,1) : firstUnanswered();
    show("quiz"); renderQ();
}

window.addEventListener("hashchange",function(){
    if(location.hash===LASTHASH) return;
    boot();
    window.scrollTo({top:0});
});

var FRAME=760;                      // every figure is drawn into the same
// frame width so type stays one size

// Figures are drawn at FRAME px and then scaled down to fit the column, so
// every size here lands on screen about 10% smaller than it reads.
var FS={val:15, cap:16, tag:14, name:26, cnum:14, cname:20, cnote:12};
var CHW=FS.cap*0.64;                // Space Mono advance plus letter-spacing

// Width is proportional to headcount up to KNEE people, so two blocks of equal
// width really do hold equally many, and a population split into groups is
// exactly as wide as the same population undivided. Above KNEE it turns
// sub-linear, or Z at 51,200 would run off the page. MINW keeps a single
// added person visible.
var PPP=0.45, KNEE=250, TAIL=0.25, MINW=12;
function wpx(n){
    if(n<=KNEE) return Math.max(MINW, PPP*n);
    return PPP*KNEE*Math.pow(n/KNEE, TAIL);
}

function popSVG(popsList, names, opts){
    var SC=1.75, baseGap=90, basePad=34, TAGSTEP=22;
    opts=opts||{};
    // Two tagged bars in one population sit a single person's width apart, so
    // their captions would collide on one line. They get a row each instead,
    // and the figure grows by however many rows the busiest population needs.
    var tagRows=popsList.reduce(function(m,p){
        return Math.max(m, p.filter(function(g){ return g.tag; }).length); },0);
    var hasTag=tagRows>0;

    var blocks=popsList.map(function(p,i){
        var cnt=p.reduce(function(a,g){return a+g.n;},0);
        var tot=p.reduce(function(a,g){return a+g.n*g.w;},0);
        var l1=cnt.toLocaleString()+" people", l2="total "+tot.toLocaleString();
        return {p:p, name:names[i], l1:l1, l2:l2, total:tot,
                w:p.reduce(function(a,g){return a+wpx(g.n);},0),
                half:Math.max(l1.length,l2.length)*CHW/2};
    });

    var tallest=0, deepest=0;
    popsList.forEach(function(p){ p.forEach(function(g){
        tallest=Math.max(tallest,g.w); deepest=Math.max(deepest,-g.w);
    });});

    // Captions are centred under narrow blocks, so the frame has to leave room
    // for them to overhang; otherwise they run off the edge.
    var pad=basePad, gap=baseGap;
    pad=Math.max(pad, blocks[0].half-blocks[0].w/2+10);
    pad=Math.max(pad, blocks[blocks.length-1].half-blocks[blocks.length-1].w/2+10);
    for(var i=0;i<blocks.length-1;i++){
        gap=Math.max(gap, blocks[i].half+blocks[i+1].half+18-blocks[i].w/2-blocks[i+1].w/2);
    }

    var baseY  = tallest*SC+36;
    var drop   = deepest*SC + (deepest? 26:0);   // negative bars plus their numbers
    var tagY   = baseY + drop + 26;
    var nameY  = baseY + drop + (hasTag? 60+(tagRows-1)*TAGSTEP : 30);
    var bodyVH = nameY + 60;
    // Above the knee the blocks stop being area-honest, so those figures carry a
    // second row where length alone stands for total welfare and is exact.
    var TH     = opts.totals ? 52+blocks.length*28 : 0;
    var VH     = bodyVH + TH;

    var content=blocks.reduce(function(a,b){return a+b.w;},0)+gap*(blocks.length-1)+pad*2;
    var W=Math.max(content,FRAME);
    var x=(W-content)/2+pad;                     // centre the content in the frame

    var s='<svg viewBox="0 0 '+Math.round(W)+' '+Math.round(VH)+'" role="img" aria-label="'+
        names.join(' compared with ')+(opts.totals?', with total welfare drawn to scale':'')+'">';

    blocks.forEach(function(bl){
        var bx=x, tagRow=0, tagS="";
        bl.p.slice().sort(function(a,b){return b.w-a.w;}).forEach(function(g){
            var gw=wpx(g.n), h=Math.abs(g.w)*SC, pos=g.w>=0, y=pos? baseY-h : baseY;
            var cx=bx+(gw-2)/2;
            s+='<rect x="'+bx.toFixed(1)+'" y="'+y.toFixed(1)+'" width="'+(gw-2).toFixed(1)+
                '" height="'+Math.max(h,2).toFixed(1)+'" fill="'+(pos?'var(--blue)':'var(--red)')+
                '" opacity="'+(pos?'.85':'.9')+(g.tag?'" stroke="var(--ink)" stroke-width="1.5':'')+'"/>';
            s+='<text x="'+cx.toFixed(1)+'" y="'+(pos? y-10 : baseY+h+20).toFixed(1)+
                '" text-anchor="middle" font-family="Space Mono, monospace" font-size="'+FS.val+'" fill="var(--ink)">'+g.w+'</text>';
            if(g.tag){
                // leader line down to a caption, so a one-person bar cannot be missed
                var ty=tagY+(tagRow++)*TAGSTEP;
                s+='<line x1="'+cx.toFixed(1)+'" y1="'+(pos? baseY+4 : baseY+h+26).toFixed(1)+
                    '" x2="'+cx.toFixed(1)+'" y2="'+(ty-13)+'" stroke="var(--ink)" stroke-width="1"/>';
                // A caption on a lower row has its neighbour's leader line running
                // through it, so each one is laid on a patch of the panel - and
                // held back until every line in this block has been drawn.
                var half=g.tag.length*FS.tag*0.66/2+4;
                tagS+='<rect class="mask" x="'+(cx-half).toFixed(1)+'" y="'+(ty-13)+
                    '" width="'+(half*2).toFixed(1)+'" height="18" fill="var(--panel)"/>';
                tagS+='<text x="'+cx.toFixed(1)+'" y="'+ty+'" text-anchor="middle" font-family="Space Mono, monospace" '+
                    'font-size="'+FS.tag+'" letter-spacing=".06em" fill="var(--ink)">'+g.tag+'</text>';
            }
            bx+=gw;
        });
        s+=tagS;
        s+='<line x1="'+(x-12).toFixed(1)+'" y1="'+baseY+'" x2="'+(x+bl.w+8).toFixed(1)+'" y2="'+baseY+
            '" stroke="var(--ink)" stroke-width="2"/>';

        var mid=(x+bl.w/2).toFixed(1);
        s+='<text x="'+mid+'" y="'+nameY+'" text-anchor="middle" font-family="Fraunces, Georgia, serif" font-weight="900" font-size="'+FS.name+'" fill="var(--ink)">'+bl.name+'</text>';
        s+='<text x="'+mid+'" y="'+(nameY+23)+'" text-anchor="middle" font-family="Space Mono, monospace" font-size="'+FS.cap+'" fill="var(--ink)" letter-spacing=".04em">'+bl.l1+'</text>';
        s+='<text x="'+mid+'" y="'+(nameY+43)+'" text-anchor="middle" font-family="Space Mono, monospace" font-size="'+FS.cap+'" fill="var(--ink)" letter-spacing=".04em">'+bl.l2+'</text>';
        x+=bl.w+gap;
    });

    if(opts.totals){
        // Length, not area, so the 20x ratio between A and Z survives the page.
        var y0=bodyVH+4, mL=34, labW=30, numW=118;
        var barMax=W-mL*2-labW-12-numW;
        var maxT=blocks.reduce(function(a,b){ return Math.max(a,b.total); },0);
        s+='<line x1="'+mL+'" y1="'+y0+'" x2="'+(W-mL)+'" y2="'+y0+'" stroke="var(--hair)" stroke-width="1"/>';
        s+='<text x="'+mL+'" y="'+(y0+22)+'" font-family="Space Mono, monospace" font-size="'+FS.cnote+
            '" letter-spacing=".11em" fill="var(--blue)">TOTAL WELFARE, THIS TIME DRAWN TO SCALE</text>';
        blocks.forEach(function(bl,i){
            var yy=y0+48+i*28, len=Math.max(3, barMax*bl.total/maxT);
            s+='<text x="'+mL+'" y="'+(yy+5)+'" font-family="Fraunces, Georgia, serif" font-weight="900" '+
                'font-size="17" fill="var(--ink)">'+bl.name+'</text>';
            s+='<rect x="'+(mL+labW)+'" y="'+(yy-8)+'" width="'+len.toFixed(1)+'" height="16" fill="var(--blue)" opacity=".85"/>';
            s+='<text x="'+(mL+labW+len+10).toFixed(1)+'" y="'+(yy+5)+'" font-family="Space Mono, monospace" '+
                'font-size="'+FS.cnum+'" fill="var(--ink)">'+bl.total.toLocaleString()+'</text>';
        });
    }
    return s+'</svg>';
}

function chainSVG(withArc){
    var SC=1.05, gap=9, pad=30;
    var nodes=[{n:CHAIN[0].from.n,w:CHAIN[0].from.w,label:"A"}];
    CHAIN.forEach(function(st,i){
        nodes.push({n:st.to.n, w:st.to.w, label:(i===CHAIN.length-1)?"Z":(i===0?"B":"")});
    });
    // Same width curve as the pair diagrams, scaled down to fill one row.
    var raw=nodes.map(function(nd){ return wpx(nd.n); });
    var k=(FRAME-pad*2-gap*(nodes.length-1))/raw.reduce(function(a,b){return a+b;},0);
    var cw=raw.map(function(r){ return r*k; });

    var baseY=nodes[0].w*SC+22;
    var content=pad*2+cw.reduce(function(a,b){return a+b;},0)+gap*(nodes.length-1);
    var W=Math.max(content,FRAME), VH=baseY+(withArc?200:104);
    var x=(W-content)/2+pad, xs=[];

    var s='<svg viewBox="0 0 '+Math.round(W)+' '+Math.round(VH)+'" role="img" '+
        'aria-label="The ladder of outcomes from A down to Z">';
    // A and B are the two narrowest bars and sit side by side, so their captions
    // would overlap on one line. Labelled nodes alternate between two rows.
    var row=0;
    nodes.forEach(function(nd,i){
        var gw=cw[i], h=nd.w*SC;
        s+='<rect x="'+x.toFixed(1)+'" y="'+(baseY-h).toFixed(1)+'" width="'+(gw-2).toFixed(1)+
            '" height="'+Math.max(h,2).toFixed(1)+'" fill="var(--blue)" opacity="'+(nd.label?".85":".5")+'"/>';
        xs.push(x+gw/2);
        if(nd.label){
            var cy=baseY+44+(row%2)*21; row++;
            var cap=nd.n.toLocaleString()+' \u00D7 '+nd.w;
            // A sits against the left edge and Z against the right, so their captions
            // are wider than the room under them. Slide them back inside the frame.
            var half=cap.length*FS.cnum*0.62/2;
            var cxc=Math.min(Math.max(x+gw/2, half+4), W-half-4);
            s+='<text x="'+(x+gw/2).toFixed(1)+'" y="'+(baseY+24)+'" text-anchor="middle" font-family="Fraunces, Georgia, serif" font-weight="900" font-size="'+FS.cname+'" fill="var(--ink)">'+nd.label+'</text>';
            s+='<text x="'+cxc.toFixed(1)+'" y="'+cy+'" text-anchor="middle" font-family="Space Mono, monospace" font-size="'+FS.cnum+'" fill="var(--ink)">'+cap+'</text>';
        }
        x+=gw+gap;
    });
    s+='<line x1="'+((W-content)/2+pad-10).toFixed(1)+'" y1="'+baseY+'" x2="'+(x-gap+8).toFixed(1)+'" y2="'+baseY+'" stroke="var(--ink)" stroke-width="2"/>';
    s+='<text x="'+(W/2).toFixed(1)+'" y="'+(baseY+94)+'" text-anchor="middle" font-family="Space Mono, monospace" font-size="'+FS.cnote+'" letter-spacing=".11em" fill="var(--blue)">EACH RUNG: EVERYONE GAINS &#183; GOOD LIVES ARE ADDED &#183; TOTAL WELFARE UP</text>';

    if(withArc){
        var x0=xs[xs.length-1], x1=xs[0], top=baseY+112, dip=baseY+172;
        s+='<path class="arc" style="--len:'+Math.round(Math.abs(x0-x1)*1.7)+'" d="M '+x0.toFixed(1)+' '+top+
            ' C '+x0.toFixed(1)+' '+dip+', '+x1.toFixed(1)+' '+dip+', '+x1.toFixed(1)+' '+top+
            '" fill="none" stroke="var(--red)" stroke-width="2.5"/>';
        s+='<path d="M '+x1.toFixed(1)+' '+top+' l -5 9 l 10 0 z" fill="var(--red)"/>';
        s+='<rect x="'+(((x0+x1)/2)-160).toFixed(1)+'" y="'+(dip-13)+'" width="320" height="26" fill="var(--panel)"/>';
        s+='<text x="'+((x0+x1)/2).toFixed(1)+'" y="'+(dip+5)+'" text-anchor="middle" font-family="Space Mono, monospace" font-size="'+FS.cnum+'" letter-spacing=".1em" fill="var(--red)">AND YET A IS BETTER THAN Z</text>';
    }
    return s+'</svg>';
}

function renderQ(){
    pruneInactive();
    if(!isActive(QUESTIONS[IDX])) IDX=stepTo(IDX,1);
    var q=QUESTIONS[IDX], A=activeIdx(), pos=A.indexOf(IDX);
    $("#counter").textContent="Question "+(pos+1)+" of "+A.length+" \u00B7 "+q.label;
    var t=""; for(var i=0;i<A.length;i++){
        var cls = i<pos?"done": i===pos?"now":"";
        var h = 6+((i%3)*4);
        t+='<div class="tick '+cls+'" style="height:'+(i===pos?16:h+4)+'px"></div>';
    }
    $("#ticks").innerHTML=t;

    var opts = q.kind==="pair" ? PAIR_OPTS(q) : q.opts;
    var fig="";
    if(q.pops) fig='<div class="figure">'+popSVG(q.pops,q.names,{totals:q.totals})+'</div>';
    if(q.chain) fig='<div class="figure">'+chainSVG(false)+'</div>';
    var ask = q.ask || "Which is better?";

    // Spent on the way out: the explanation belongs to the arrival, not to the
    // question, and must not follow the person down the rest of the quiz.
    var html = NOTICE ? '<p class="notice">'+NOTICE+'</p>' : '';
    NOTICE="";
    html+='<div class="q"><h2 class="qtitle">'+q.title+'</h2>'+
        '<p class="qbody">'+(typeof q.body==="function"?q.body(ANS):q.body)+'</p>'+fig+
        '<p class="qbody" style="margin-top:20px"><strong>'+ask+'</strong></p><div class="opts">';
    opts.forEach(function(o){
        var sel = ANS[q.id]===o[2] ? " sel":"";
        html+='<button class="opt'+sel+'" data-v="'+o[2]+'"><span class="key">'+o[0]+'</span><span>'+o[1]+'</span></button>';
    });
    html+='</div></div>';
    $("#qslot").innerHTML=html;

    Array.prototype.forEach.call(document.querySelectorAll(".opt"),function(b){
        b.addEventListener("click",function(){
            ANS[q.id]=b.dataset.v;
            Array.prototype.forEach.call(document.querySelectorAll(".opt"),function(x){x.classList.remove("sel");});
            b.classList.add("sel");
            $("#next").disabled=false;
            syncHash();
            setTimeout(function(){ if(ANS[q.id]) advance(); },260);
        });
    });
    $("#next").disabled = !ANS[q.id];
    $("#back").style.visibility = pos===0 ? "hidden":"visible";
    $("#next").textContent = pos===A.length-1 ? "See the verdict \u2192" : "Next \u2192";
    syncHash();
}

function advance(){
    // The answer just given may have brought a later question into play or
    // retired one, so recompute rather than trusting the list from render time.
    var A=activeIdx(), pos=A.indexOf(IDX);
    // Sent back here to fill a gap: take the next gap, or the verdict that was
    // asked for in the first place. A gap opened by this very answer - a
    // conditional question it just brought into play - is caught the same way.
    if(RETURNING && pos>=0){
        var miss=missingActive();
        if(miss.length){ IDX=miss[0]; renderQ(); window.scrollTo({top:0,behavior:"smooth"}); }
        else { showNameStep(); }
        return;
    }
    if(pos>=0 && pos<A.length-1){ IDX=A[pos+1]; renderQ(); window.scrollTo({top:0,behavior:"smooth"}); }
    else { showNameStep(); }
}

// One screen, offered once, between the last question and the verdict - a
// name is never required to see results. Skipped entirely on a reload of a
// finished run (boot() goes straight to showResults) since it has nothing to
// ask that a fresh completion doesn't already have an answer to.
function showNameStep(){
    $("#namefield").value=NAME;
    show("namestep");
    window.scrollTo({top:0,behavior:"smooth"});
    setTimeout(function(){ $("#namefield").focus(); },0);
}
function finishNameStep(){
    NAME=$("#namefield").value.trim();
    logAnswers();
    showResults();
}
$("#namenext").addEventListener("click",finishNameStep);
$("#nameback").addEventListener("click",function(){
    show("quiz"); renderQ(); window.scrollTo({top:0,behavior:"smooth"});
});
$("#namefield").addEventListener("keydown",function(e){
    if(e.key==="Enter") finishNameStep();
});

$("#start").addEventListener("click",function(){
    ANS={}; IDX=0; SHARED=false; RETURNING=false; NAME=""; show("quiz"); renderQ();
});
$("#next").addEventListener("click",advance);
$("#back").addEventListener("click",function(){
    // Stepping back deliberately ends the errand: from here on, forward means
    // the next question rather than the next gap.
    RETURNING=false;
    var A=activeIdx(), pos=A.indexOf(IDX);
    if(pos>0){ IDX=A[pos-1]; renderQ(); window.scrollTo({top:0,behavior:"smooth"}); }
});
document.addEventListener("keydown",function(e){
    if($("#quiz").classList.contains("hide")) return;
    var k=e.key.toUpperCase(), map={A:0,B:1,C:2,D:3};
    if(k in map){ var bs=document.querySelectorAll(".opt"); if(bs[map[k]]) bs[map[k]].click(); }
});

/* ---------- prose for the results ---------- */
var LABELS={
    pareto:function(a){ return {
        yes:"If the very same people all live better lives, that is better.",
        no:"A future need not be better even when the very same people are all better off in it.",
        abstain:"No view on whether the same people all being better off makes a future better."}[a]; },
    same_number:function(a){ return "A future of 100 people is "+
        ({left:"better than",right:"worse than",equal:"exactly as good as",none:"not rankable against"}[a])+
        " a future of 100 entirely different people whose lives all go far better."; },
    AvB:function(a){ return "A is "+({left:"better than",right:"worse than",equal:"exactly as good as",none:"not rankable against"}[a])+" B."; },
    AvZ:function(a){ return "A is "+({left:"better than",right:"worse than",equal:"exactly as good as",none:"not rankable against"}[a])+" Z."; },
    misery:function(a){ return "Adding Nadia with a life of suffering makes the outcome "+({left:"worse",right:"better",equal:"neither better nor worse",none:"incomparable"}[a])+"."; },
    neutral_mod:function(a){ return "Adding Nadia with a modest good life makes the outcome "+({left:"worse",right:"better",equal:"neither better nor worse",none:"incomparable"}[a])+"."; },
    neutral_wond:function(a){ return "Adding Nadia with a wonderful life makes the outcome "+({left:"worse",right:"better",equal:"neither better nor worse",none:"incomparable"}[a])+"."; },
    greedy:function(a){ return "K is "+({left:"better than",right:"worse than",equal:"exactly as good as",none:"not rankable against"}[a])+
        " K± — Owen down from "+K_BASE[0].w+" to "+K_BOTH[1].w+", and Nadia added at "+K_WOND[1].w+"."; },
    benign:function(a){ return "A+ is "+({left:"worse than",right:"better than",equal:"exactly as good as",none:"not rankable against"}[a])+" A \u2014 everyone gains, and good new lives are added."; },
    nae:function(a){ return "B is "+({left:"worse than",right:"better than",equal:"exactly as good as",none:"not rankable against"}[a])+" A+ \u2014 same headcount, more total, more average, fully equal."; },
    generalize:function(a){ return {
        yes:"Those two verdicts hold identically at every rung of the ladder.",
        no:"Somewhere on the ladder those two verdicts flip.",
        abstain:"No view on whether those two verdicts survive repetition."}[a]; },
    collapse:function(a){ return {
        yes:"A tiny improvement to one life cannot turn \u201Cunrankable\u201D into a determinate verdict.",
        no:"A tiny improvement to one life can turn \u201Cunrankable\u201D into a determinate verdict.",
        abstain:"No view on whether unrankability collapses at its boundary."}[a]; },
    menu_eq:function(a){ return {
        yes:"A verdict reached between two options still holds when a third joins them.",
        no:"A third option can change how the first two compare.",
        abstain:"No view on whether verdicts survive a wider menu."}[a]; },
    trans_gt:function(a){ return {
        yes:"\u201CBetter than\u201D is transitive.",
        no:"\u201CBetter than\u201D is not always transitive.",
        abstain:"No view on whether \u201Cbetter than\u201D is transitive."}[a]; },
    trans_none:function(a){ return {
        yes:"\u201CNot worse than\u201D is transitive.",
        no:"\u201CNot worse than\u201D is not always transitive.",
        abstain:"No view on whether \u201Cnot worse than\u201D is transitive."}[a]; },
    trans_eq:function(a){ return {
        yes:"\u201CExactly as good as\u201D is transitive.",
        no:"\u201CExactly as good as\u201D is not always transitive.",
        abstain:"No view on whether \u201Cexactly as good as\u201D is transitive."}[a]; }
};
function claimText(id){
    var v=LABELS[id];
    return (typeof v==="function") ? v(ANS[id]) : v;
}

/* K± meets the closure whenever the wonderful addition was ranked at all: the
   answer supplies K = K++ or K > K++, Pareto supplies K++ > K±, and between
   them K is better than K±. Ranking K± level with K or above it then
   contradicts a verdict the person's own answers deliver.

   Two sets, because the contradiction is reached either by chaining equalities
   or in one step of better-than. The sets do not line up with the answers,
   though: the one-step set is reached from two different pairs of verdicts, so
   the prose has to be read off the answers rather than off the set. Both are
   the same complaint, so they share a group and are shown once. */
function greedyPriced(needs){
    return {
        needs: needs,
        // Five answer shapes reach these two sets, and which of the two
        // verdicts was the denial changes what the card has to say, so both
        // the title and the prose are read off the answers.
        title:function(a){
            return a.neutral_wond==="none"
                ? "You ranked K± in a way that ranks K++ after all."
                : a.greedy==="none"
                ? "You declined a comparison your other answers had already made."
                : "Your own answers already rank K above K±.";
        },
        because:function(a){
            var harm=K_BASE[0].w-K_BOTH[1].w;
            var pareto="Pareto puts K++ above K±: the same 501 people, Owen better off by "+
                harm+" in one of them and nobody worse.";
            if(a.neutral_wond==="none"){
                var put=a.greedy==="right" ? "above K" : "exactly level with K";
                return "You placed K and K++ beyond ranking: not better, not worse, not equal. But you put K± "+put+
                    ", and "+pareto+" Taken together, those two say K++ is better than K, which is the pair you had just declined to rank. "+
                    "If adding a good life is enough to outweigh a loss, then it must also be better than no change.";
            }
            if(a.greedy==="none"){
                var said=a.neutral_wond==="equal"
                    ? "exactly as good as leaving her out, so K and K++ stand level"
                    : "worse than leaving her out, so K stands above K++";
                return "You judged the ranking of K and K± to be indeterminate. But you said adding Nadia at "+K_WOND[1].w+" is "+
                    said+", and "+pareto+" Between them those two give K better than K± — a ranking of the pair you had just declined to rank.";
            }
            var said = a.neutral_wond==="equal"
                ? "You said adding Nadia at "+K_WOND[1].w+" is exactly as good as leaving her out, so K and K++ stand level."
                : "You said adding Nadia at "+K_WOND[1].w+" makes the outcome worse, so K stands above K++.";
            var put = a.greedy==="equal" ? "exactly level with K" : "above K";
            var moral = a.neutral_wond==="equal"
                ? "Nadia's arrival is judged to outweigh the loss of Owen's welfare, but you denied that Nadia's arrival made things better when all else was held fixed."
                : "Her arrival is a cost by your own account, and Owen's loss is a second one. Two costs and no gain cannot leave the world better off.";
            return said+" "+pareto+" Between them those two give K better than K±, and you put K± "+put+" instead. "+moral;
        },
        group:"greedyPriced"
    };
}

var STORIES=[
    // One entry per route to the same complaint: better-than in a single step,
    // equalities chained, or a chain that also crosses a denied verdict.
    greedyPriced(["greedy","neutral_wond","pareto","trans_gt"]),
    greedyPriced(["greedy","neutral_wond","pareto","trans_eq","menu_eq"]),
    greedyPriced(["greedy","neutral_wond","pareto","trans_eq","menu_eq","trans_gt"]),
    {
        needs:["benign","nae","trans_gt","AvB"],
        // Only for the shape the prose describes: two improvements and a
        // verdict swinging back. The same four answers collide in other ways.
        when:function(a){ return a.benign==="right" && a.nae==="right" && a.AvB==="left"; },
        title:"The ladder reaches B, but you say B is worse.",
        because:"Two rungs are all it takes. If A+ improves on A, and B improves on A+, then transitivity delivers B over A. You also judged A over B directly. One of those four has to go — and notice how little the argument needed: no vast numbers, no lives barely worth living, just one application of each move."
    },
    {
        // Same four answers as the story above, reached the other way round:
        // there the rungs deliver a verdict that collides with A over B, here
        // they deliver the rung the person declined to give.
        needs:["benign","nae","trans_gt","AvB"],
        when:function(a){ return a.benign==="none" && a.AvB==="left" && a.nae==="right"; },
        title:"The rungs rank the step you declined to rank.",
        because:"You judged A to be incomparable against A+: not better, not worse, not equal. But you judged A better than B, and B better than A+, and better-than chains \u2014 so A is better than A+, which is a verdict on the very pair you had just judged indeterminate."
    },
    {
        needs:["benign","nae","generalize","trans_gt","AvZ"],
        when:function(a){ return a.benign==="right" && a.nae==="right" && a.AvZ==="left"; },
        title:"The ladder reaches Z, and the loop closes.",
        because:"This is Parfit's mere addition argument. Each rung is a step you endorsed and said you would endorse again; transitivity chains them the whole way down; and the last judgement swings back from the bottom of the ladder to the top. The relation \u201Cbetter than\u201D now runs in a circle.",
        chain:true
    },
    {
        needs:["misery","neutral_mod","pareto","trans_eq","menu_eq"],
        when:function(a){ return a.misery==="equal" && a.neutral_mod==="equal"; },
        title:"Nadia cannot be worth nothing whichever way her life goes.",
        because:"You said K is exactly as good as the world where Nadia exists in agony, and exactly as good as the world where she exists with a decent life. Transitivity of equal-goodness makes those two worlds exactly as good as each other, even though Nadia is enormously better off in one of them. This is Broome's neutral-range argument in <em>Weighing Lives</em> ch. 10: if bringing someone into existence is never better or worse, it cannot matter how their life then goes \u2014 and it plainly does.",
        world:"If two carriers of the Tay-Sachs gene have a child, there's a one-in-four chance that the child develops normally for six months, then loses sight, hearing and movement, and dies by age four. Your answers say that conceiving that child makes the world no worse, and that conceiving a healthy one makes it no better.",
        // Same argument as the wonderful-life version below, just run at the
        // lower welfare level; if both trigger they should count once, not twice.
        group:"nadiaNeutralRange"
    },
    {
        needs:["misery","neutral_wond","pareto","trans_eq","menu_eq"],
        when:function(a){ return a.misery==="equal" && a.neutral_wond==="equal"; },
        title:"Nadia cannot be worth nothing whichever way her life goes.",
        because:"You said K is exactly as good as the world where Nadia exists in agony, and exactly as good as the world where she exists with a wonderful life. Transitivity of equal-goodness makes those two worlds exactly as good as each other, even though Nadia is enormously better off in one.",
        world:"If two carriers of the Tay-Sachs gene have a child, there's a one-in-four chance that the child develops normally for six months, then loses sight, hearing and movement, and dies by age four. Your answers say that conceiving that child makes the world no worse, and that conceiving a healthy one makes it no better.",
        group:"nadiaNeutralRange"
    },
    {
        needs:["neutral_mod","neutral_wond","trans_eq","menu_eq","pareto"],
        when:function(a){ return a.neutral_mod==="equal" && a.neutral_wond==="equal"; },
        title:"Nadia's life cannot be worth nothing twice over.",
        because:"You said K is exactly as good as the world with Nadia in it at welfare 7, and exactly as good as the world with Nadia in it at welfare 70. Transitivity of equal-goodness makes those two worlds exactly as good as each other, even though Nadia is far better off in one. This is Broome's argument in <em>Weighing Lives</em> ch. 10 that there can be no neutral <em>range</em> \u2014 at most a neutral point.",
        world:"Boonin's \"Wilma and Pebbles\" problem: Wilma is told that if she conceives a child today, her child (to be named Pebbles) will be born blind. If she takes a pill daily for the next two months, she will conceive a different, healthy child (named \"Rocks\"). Most people say she should wait. However, waiting is not better <em>for</em> anyone: Pebbles (the blind child) would not be born otherwise, and so is not made worse off if Wilma has a child now.<br /><br /> Your answers say that creating a positive life is morally neutral in either case, so there cannot be anything wrong with Wilma choosing to have a child now instead of taking the pill first."
    }
];
/* A support set does not fix the answers behind it: the same four answers can
   be jointly unsatisfiable for several different reasons, and a story written
   for one of them misdescribes the others - telling someone who declined to
   rank A against A+ that they called it an improvement. Each story therefore
   names the shape its prose describes, and a set that does not match falls
   through to the generic card, which says only what is true of every shape. */
function storyFor(set, ans){
    ans = ans || ANS;
    for(var i=0;i<STORIES.length;i++){
        var s=STORIES[i], ok=true;
        if(s.needs.length!==set.size) ok=false;
        else s.needs.forEach(function(n){ if(!set.has(n)) ok=false; });
        if(ok && s.when && !s.when(ans)) ok=false;
        if(ok) return s;
    }
    return null;
}

// Conflicts and bullets are settled by the diagrams alone; a world note aims
// the same point at a case outside them. Deliberately confined to the results
// and kept out of compile() and the closure: real cases carry confounders the
// diagrams do not — someone can resist the verdict on embryo selection for
// reasons having nothing to do with population ethics — so an answer to one
// could not be read as an edge in a betterness ordering without inventing
// conflicts that are not there. These say what a position implies; they are
// not further questions, and nothing here is scored.
function worldNote(s){
    return '<div class="world"><div class="tag"><div class="world-heading">Concrete Example</div></div><p>'+s+'</p></div>';
}

function bullets(){
    var out=[];
    if(ANS.trans_gt==="no") out.push({t:"You rejected transitivity of better-than.",b:"That is a live position \u2014 Temkin and Rachels both take it \u2014 and it defuses most of the paradoxes here at a stroke. The price is that \u201Cbetter than\u201D can now run in circles, which makes it hard to say what you should be aiming at: for any option there may be a better one that is in turn worse than where you started."});
    // Every other principle draws a bullet when rejected, and this one is not
    // the exception: it is only ever asked of someone the ladder has reached,
    // so declining it is always load-bearing.
    if(ANS.trans_none==="no") out.push({t:"You rejected transitivity of not-worse-than.",b:"This is Parfit\u2019s own resolution to the mere addition paradox: every rung leaves you not worse off, but \u201Cnot worse than\u201D does not chain, so the ladder never delivers Z. The move is open to you only because you deemed many pairs of outcomes incomparable.<br/><br/>What it costs: the final outcome Z is worse than where we started, even though no step along the way was the mistake."});

    if(ANS.menu_eq==="no"){
        // Naming the specific expansion failure is more use than the general
        // principle, so dig the actual pair of equalities out of the answers.
        var eqs=[];
        if(ANS.misery==="equal")       eqs.push({w:"K\u2212", q:"misery"});
        if(ANS.neutral_mod==="equal")  eqs.push({w:"K+",       q:"neutral_mod"});
        if(ANS.neutral_wond==="equal") eqs.push({w:"K++",      q:"neutral_wond"});
        var worked = eqs.length>=2
            ? " In your case it does specific work: you called both "+eqs[0].w+" and "+eqs[1].w+
              " exactly as good as K, and Pareto ranks them against each other, which together would be a contradiction. Denying menu independence is what lets all three stand, at the cost of saying that "+
              eqs[0].w+" and K are equally good only so long as "+eqs[1].w+" is not also on the table."
            : "";
        out.push({t:"You denied that a verdict survives a wider menu.",b:"Your pairwise judgements no longer cohere into a single ordering: each judgement depends on the pair it was made in, and putting a third option on the table can reverse it. This is a violation of Sen\u2019s property &beta;, which states that if two options are tied for best, then expanding the set of options cannot break the tie.<br/><br/>You are committed to there being no such thing as how good an outcome is <em>full stop</em>, only how good it is against a particular set of choices."});
    }

    if(ANS.trans_eq==="no") out.push({t:"You rejected transitivity of equal-goodness.",b:"This is the standard escape from the neutral-range argument, and it usually comes packaged as the claim that some outcomes are only <em>roughly</em> comparable rather than exactly equal. Be warned that it is not a way out of Broome generally: he devotes a later chapter to arguing that rough comparability cannot be a stable resting place either."});
    if(ANS.pareto==="no") out.push({t:"You rejected the Pareto principle.",b:"Denying that a world is better when the very same people are all better off in it is about as revisionary as population ethics gets. Almost every theory in the field takes this as a fixed point."});
    if(ANS.AvZ==="right") out.push({t:"You accepted the repugnant conclusion.",b:"You judged Z better than A: enough lives barely worth living outweigh a small number of superb ones. This is the totalist's answer and it is entirely consistent \u2014 Tännsjö, Huemer and others defend it explicitly. It also means there is in principle no quality of life so marginal that sheer numbers cannot compensate."});
    if(ANS.generalize==="no") out.push({t:"You said the verdict flips somewhere on the ladder.",b:"That leaves you owing an account of <em>where</em>. Every rung is qualitatively identical to every other; if rung 4 is fine and rung 5 is not, something must distinguish them. Critical-level and lexical views are attempts to say what."});
    // Revisionary pair verdicts. The principles all draw a comment when rejected;
    // without these, a verdict like "her agony is a gain" could pass in silence.
    if(ANS.misery==="right") out.push({t:"You counted a life of suffering as a gain.",b:"When Nadia\u2019s life holds far more suffering than good \u2014 a life it would have been better for her never to have had \u2014 you judged the world better for containing it."});

    if(ANS.neutral_mod==="left" || ANS.neutral_wond==="left") out.push({t:"You said a life worth living makes the world worse by being lived.",b:"This goes well past the Procreation Asymmetry, which claims only that creating a happy person is not <em>good</em>. You have said it is positively <em>bad</em>.",
        world:"Think of a couple who want a child, and would raise it well: you are committed to saying the child's birth is nonetheless bad for the world."});

    // Adding a better life should not be ranked below adding a worse one. Pareto
    // turns this into a conflict; without Pareto it is merely very hard to hold.
    var RANK={left:-1,equal:0,right:1};
    var NADIA=[["misery","a life of agony"],["neutral_mod","a modest good life"],["neutral_wond","a wonderful life"]];
    var inv=[];
    for(var i=0;i<NADIA.length;i++) for(var j=i+1;j<NADIA.length;j++){
        var ri=RANK[ANS[NADIA[i][0]]], rj=RANK[ANS[NADIA[j][0]]];
        if(ri===undefined||rj===undefined) continue;
        if(ri>rj) inv.push("adding "+NADIA[i][1]+" above adding "+NADIA[j][1]);
    }
    if(inv.length) out.push({t:"Nadia\u2019s life gets better and your verdict gets worse.",b:"You ranked "+inv.join(", and ")+" \u2014 the same woman, the same 500 people around her, and the only difference is how well her life goes. According to your choices, the value of bringing someone into existence <em>falls</em> as their life improves."});

    // The other horn of the greediness dilemma. Declining to rank K against K±
    // is perfectly consistent, and that is the trouble with it: a loss to
    // somebody who exists either way has gone unsayable.
    var HARM=K_BASE[0].w-K_BOTH[1].w;
    if(ANS.greedy==="none" && (ANS.neutral_wond==="none"||ANS.neutral_wond==="equal")){
        out.push({t:"A neutral addition made a harm unrankable.",
                  b:"Owen is one of the 500 people in K, and he's there in K± too, "+HARM+" points worse off. That is a loss to somebody who exists either way — not to a merely possible person. At the same time, you judged that adding Nadia's happy life alone did not constitute an improvement. This is Broome’s greediness objection. Your answer is not inconsistent, but the cost is that adding a new person \"swallows\" the harm to Owen – on this view, adding Nadia isn't good in isolation, but it causes the harm to Owen to stop being bad."});
    }
    // K± holds more welfare in total than K, so a totalist ranking it above K
    // is doing arithmetic rather than biting anything. It is the person who
    // says her arrival is not a gain, and then spends it on Owen's loss, who
    // owes an account - and only while it stays a bullet: with Pareto accepted
    // the same two answers are jointly unsatisfiable, and the conflict card
    // says it better than a bullet can.
    if(ANS.greedy==="right" && ANS.neutral_wond==="none" && ANS.pareto!=="yes"){
        out.push({t:"An addition you could not rank outweighed a harm you could.",
                  b:"You said that adding Nadia at "+K_WOND[1].w+" was incomparable to leaving her out, and then ranked K± above K — which takes her arrival to justify making Owen worse off, when he would have existed either way. An addition cannot be too indeterminate to compare against nothing and determinate enough to outweigh a named loss. If her arrival really is worth that much, the earlier question had an answer: it was better."});
    }
    if(ANS.greedy==="equal") out.push({t:"You priced Nadia’s life at exactly Owen’s loss.",
        b:"Two things separate K from K±: Owen loses "+HARM+" points, and Nadia arrives at "+K_WOND[1].w+
          ". Calling the two worlds exactly as good sets the two changes to cancel out — an oddly exact figure for a life, and one that would have to move if Owen’s loss moved."+
          ((ANS.neutral_mod==="none"||ANS.neutral_wond==="none")
            ? " You also said that adding Nadia cannot be ranked against leaving her out. The two verdicts pull opposite ways: one says her existence has no determinate value, the other says it exactly equals the negated value of the harm to Owen."
            : "")});

    if(ANS.benign==="left") out.push({t:"Everyone gains, good lives are added, and you called it worse.",b:"Every one of A\u2019s hundred is better off in A+, and a further hundred exist there with lives clearly worth living. Ranking that below A means the new lives are a cost heavy enough to outweigh a gain to every person who was already there.<br/><br/>Your answer does not force you to accept the mere addition paradox. However, the price is what it commits you to elsewhere: you would prefer the original hundred be worse off, so long as fewer people existed alongside them.",
                                      world:"Distributing malaria nets leaves recipients healthier and better off, and also means more children survive to adulthood, but with worse lives than the global average. Your answer holds that distributing malaria nets may therefore be a <em>bad</em> thing."});

    if(ANS.nae!=="right") out.push({t:"You denied that levelling up improves things.",b:"B holds the same "+CHAIN[0].to.n+" people as A+, with more welfare in total, more on average, and more equality. There is a consistent motive available \u2014 the better-off group does lose, falling from "+CHAIN[0].plus[0].w+" to "+CHAIN[0].to.w+", while the worse-off rise from "+CHAIN[0].plus[1].w+" \u2014 so a view that weighs losses to the well-off heavily can resist it. But it sets you against totalism, averagism and egalitarianism in one move."});

    // What the ladder gaps buy, stated without borrowing a premise nobody was
    // asked for. It is tempting to say the flip has to go downward, since a
    // flip to "better" would only carry you further down the ladder - but that
    // reasoning needs the rungs to chain, and here they do not: the gaps break
    // every path from A to Z on their own, whatever the flipped rung says. So
    // the flip's direction is not forced, and neither is any verdict further
    // down. What is forced is only the shape below, which needs nothing.
    // Never beside the conflict it is the consistent counterpart of: a profile
    // the engine has just called impossible is not one to price as a cost.
    if(ANS.AvZ==="left" && ANS.benign==="none" && !zRankCandidate(ANS)){
        /* REVISE_ME */
        out.push({t:"You ranked the two ends of the ladder but not a single step of it.",b:"A against Z you settled: two populations "+CHAIN.length+" rungs and "+(Z_POP[0].n-A_POP[0].n).toLocaleString()+" people apart. A against A+ you did not: one step, one small gain to each of a hundred people, one group of a hundred added. The larger comparison came out easier than the smaller one contained inside it.<br/><br/>That is not a contradiction, and the gaps are what make it work \u2014 an unrankable rung is a broken link, so no chain of steps ever carries you from A down to Z, and the two answers never meet. It is worth seeing what it says about the gaps themselves. Whatever generates them is not tracking how far apart two futures are, since it falls silent on the near comparison and speaks confidently on the distant one. Any account you give of <em>why</em> A and A+ cannot be ranked has to be one that stops applying by the time the ladder reaches Z."});
    }

    var noneCount=0, PAIRQS=["AvB","AvZ","misery","neutral_mod","neutral_wond","benign","nae","greedy","same_number"];
    PAIRQS.forEach(function(k){
        if(ANS[k]==="none") noneCount++;
    });
    if(noneCount>=3) out.push({
        t:noneCount===PAIRQS.length?"You judged none of the nine pairs rankable.":"You judged "+noneCount+" of the "+PAIRQS.length+" pairs unrankable.",b:"Among these pairs, you said neither choice was better, nor were they <em>equal</em> — they could not be ranked at all. An ordering with widespread incomparability cannot give much practical guidance \u2014 it will stay silent on most of the choices you would want it to settle.",
        world:"Parfit's Depletion problem. A country can burn through its natural resource reserves, raising living standards for a century but ruining the climate for future generations; or it can conserve resources and protect the environment. The choice changes who meets whom and when children are conceived, so the two futures are populated by entirely different people. No particular person is harmed by choosing to deplete resources, but it still seems that a wrong has been committed. <strong>Your answers force the conclusion that depleting the environment's resources is not wrong.</strong>"
    });
    // The second half of the asymmetry is a negative claim - creating a happy
    // person is not *better* - and "cannot be ranked" delivers that as squarely
    // as "exactly as good" does. The two routes differ in what they cost, not in
    // whether they get you there, so the bullet names which one was taken.
    var notBetter=function(v){ return v==="equal"||v==="none"; };
    if(ANS.misery==="left" && (notBetter(ANS.neutral_mod)||notBetter(ANS.neutral_wond))){
        var viaEq = ANS.neutral_mod==="equal"||ANS.neutral_wond==="equal";
        var viaNone = ANS.neutral_mod==="none"||ANS.neutral_wond==="none";
        var route = (viaEq&&viaNone)
            ? " You got there by both routes at once \u2014 calling one addition exactly as good as leaving her out, and the other unrankable against it. Those are different claims, and only the first is exposed to Broome\u2019s argument."
            : viaEq
            ? " You took it in the strong form: the addition is <em>exactly as good</em> as leaving her out. That is the form Broome\u2019s argument targets, and if you also kept Pareto and transitivity of equal-goodness it will have surfaced as a conflict above."
            : " You took it in the weak form: the addition is simply <em>not rankable</em> against leaving her out. Nothing is claimed to be exactly as good, so the neutral-range argument has nothing to chain through. That is the usual reason people retreat here \u2014 but it is not safety, only a different battlefield: Broome's collapsing principle is aimed squarely at it, which is what the boundary question was testing. What the retreat costs even if it works is silence: on a choice that plainly matters, your ordering declines to speak.";
        out.push({t:"You hold the Procreation Asymmetry.",b:"Creating a miserable life is bad; creating a happy one is not good. This matches most people's instincts, and it is not inconsistent on its own. It is, however, notoriously hard to ground: the obvious explanations of the first half tend to imply the opposite of the second."+route,
                  world:"By the Procreation Asymmetry, human extinction need not be a bad thing: if future generations never come to exist, then no one has been harmed so long as the currently-alive generations are happy."});
    }

    // The same-number, different-people probe. It emits no edge - the two
    // futures share no people with anything else in the quiz, so a betterness
    // link from it could never close into a cycle - and it is not meant to.
    // Its job is to make an ordering state, on the one comparison where
    // identity is the only variable, whether identity silences it. Every
    // answer here is a position with a price, so each draws a bullet.
    if(ANS.same_number==="none" || ANS.same_number==="equal"){
        var sroute = ANS.same_number==="none"
            ? "you declined to rank them at all"
            : "you called them exactly as good as each other";
        var scost = ANS.same_number==="none"
            ? "Declining is the more cautious-looking of the two, but it is not caution: your ordering has gone quiet on the comparison rather than judged it a tie."
            : "You did not merely decline — you returned a verdict, and the verdict is that a near-doubling of every life in the picture is worth precisely nothing.";
        // The ground this covers is the Depletion case, which the unrankable-pairs
        // bullet already carries as a world note; saying it twice for the people
        // who draw both is worse than saying it once well, so this one keeps to
        // what is peculiar to holding the number fixed.
        out.push({t:"When the people change, a world with uniformly better-off people is not judged better.",b:"Same headcount, every life in the second future far better than every life in the first, and not one person in both — and "+sroute+". This is the person-affecting thought in its strongest form: nothing is better or worse unless it is better or worse <em>for</em> somebody, and here there is nobody it could be better for.",
                  world:"Parfit's medical programmes:<br><br>"+
                  "A health service can afford only one of two programmes. Both prevent the same handicap, and each would prevent it in 1,000 children."+
                  "<ol><li><strong>Preconception testing</strong> screens women who have not yet conceived; those who test positive are advised to wait. If this programme is canceled, 1,000 handicapped children are born in place of 1,000 unhandicapped children. These are <strong>not the same children</strong> who would have been born otherwise.</li>"+
                  "<li><strong>Pregnancy testing</strong> screens women who are already pregnant; those who test positive are treated, and their children are born unharmed. Cancel this programme and 1,000 handicapped children are born — and they are <strong>the very same children</strong> who would otherwise have been born unharmed.</li></ol>"+
                  "Either way, 1,000 children are handicapped; many would say these programmes are equally good. But your answers require that <strong>only the pregnancy testing is good</strong>. According to your answers, canceling the preconception testing is not bad because no person is harmed."});
    }
    // Ranking the same-number case while ducking the different-number ones is
    // Parfit's shape rather than a slip, so it is named as such - and pressed
    // where it is weakest, which is that the line falls between one headcount
    // and the next.
    // Every pair whose two futures differ in headcount. K against K+- belongs
    // here too - 500 people against 501 - and was missed when that question
    // was added, which undercounted the very thing this bullet is counting.
    // nae is the one pair that does not belong: A+ and B hold the same 200.
    var duckedDiffN=["AvB","AvZ","benign","misery","neutral_mod","neutral_wond","greedy"]
        .filter(function(k){ return ANS[k]==="none"; });
    if(ANS.same_number==="right" && duckedDiffN.length){
        out.push({t:"Comparable when the numbers match, unrankable when they do not.",b:"You determinately ranked two futures when they each had 100 people, while leaving "+
            (duckedDiffN.length===1?"one comparison":duckedDiffN.length+" comparisons")+
                  " unrankable where the two futures held <em>different numbers</em> of people. Your answers match Parfit's Same Number Quality Claim: same-number choices are decided by how well the lives go, but different-number cases are left indeterminate.<br><br>"+
                  "What the view owes is an account of the line. On your answers, 100 people at 90 is determinately better than 100 different people at 50; put one more person into the better future and the comparison falls silent, though nothing about the original hundred lives has changed. That is Broome's collapsing-principle objection pointed at headcount rather than wellbeing."});
    }
    if(ANS.same_number==="left"){
        out.push({t:"You ranked the worse-off future above the better-off one.",b:"The two futures hold 100 people each, but no single person lives in both futures. Every life in both is worth living, and the only thing separating them is that the second group's lives go better. You ranked the first group above them. Totalism, averagism, maximin and egalitarianism all deliver the opposite verdict here, and the person-affecting views deliver a tie or a refusal rather than a reversal — this is an answer that no reasonable view gives."});
    }
    return out;
}

function profile(){
    if(ANS.AvZ==="right" && ANS.benign==="right" && ANS.nae==="right") return "Your answers sit closest to <strong>totalism</strong> \u2014 welfare summed across everyone who ever lives.";
    if(ANS.AvB==="left" && ANS.AvZ==="left" && ANS.benign==="left" && ANS.neutral_mod==="left" && ANS.nae==="right") return "Your answers sit closest to <strong>averagism</strong> \u2014 the view that aims to improve the <em>average</em> welfare of populations.";
    if((ANS.neutral_mod==="equal" || ANS.neutral_mod==="none") && (ANS.neutral_wond==="equal" || ANS.neutral_wond==="none") && ANS.misery==="left") return "Your answers sit closest to a <strong>person-affecting view</strong> with an asymmetry: creating a bad life is bad, but creating a good life is neutral.";
    if((ANS.neutral_mod==="equal" || ANS.neutral_mod==="none") && (ANS.neutral_wond==="equal" || ANS.neutral_wond==="none") && (ANS.misery==="equal"||ANS.misery==="none")) return "Your answers sit closest to a <strong>person-affecting view</strong> with symmetry: creating a new life (whether good or bad) is a neutral act. Something can only be good or bad <em>for</em> an existing person.";
    if(ANS.AvZ==="left" && ANS.benign==="right") return "Your answers pull toward a <strong>critical-level or lexical view</strong> \u2014 sufficiently good lives count, marginally good lives do not.";
    return "Your answers do not settle cleanly onto one of the standard views of population ethics.";
}

/* One card per check that fired, in EXTRA_CHECKS order. Each takes the check's
   own result and the number the card carries on the page, so no card knows how
   many came before it. */
var CARD_HTML={
    alpha:function(al, n){
        var h='';
        h+='<div class="hit"><div class="tag">Conflict '+n+' &middot; contraction inconsistency</div>';
        h+='<h3 style="margin-top:10px">Adding a third option changed your mind about the first two.</h3>';
        // The pair that was ranked is {pairWinner, picked} either way round:
        // the A/B question when the pick came from there, A against Z when the
        // pick was Z. The option left over is the one whose arrival is doing
        // the damage, and it differs between the two.
        h+='<ol class="claims"><li>Offered '+al.pairWinner+' and '+al.picked+
           ' alone, you judged '+al.pairWinner+' the better of the two.</li>';
        h+='<li>Offered A, B and Z together, you picked '+al.picked+' as best.</li></ol>';
        h+='<p class="because">This violates Sen\u2019s property &alpha;: if something is best in a set, it must still be best in any subset that contains it. '+al.third+'\u2019s presence cannot make '+al.picked+' beat '+al.pairWinner+' if it did not already.</p></div>';
        return h;
    },
    collapse:function(cp, n){
        var h='', vg=cp.vague, an=cp.anchor;
        h+='<div class="hit"><div class="tag">Conflict '+n+' &middot; collapsing principle</div>';
        h+='<h3 style="margin-top:10px">Your unrankable case has a determinate one right next to it.</h3>';
        h+='<ol class="claims"><li>'+claimText(vg.id)+'</li><li>'+claimText(an.id)+'</li><li>'+claimText("collapse")+'</li></ol>';
        h+='<p class="because">You judged '+vg.world+' unrankable against K, while '+an.world+
           ' \u2014 the same world with Nadia\u2019s life going '+(cp.dir==="up"?"better":"worse")+
           ' \u2014 you ranked determinately. Between welfare '+
           Math.min(vg.w,an.w)+' and '+Math.max(vg.w,an.w)+' for her, then, lies a point where one unit of wellbeing '+
           'converts \u201Cno fact of the matter\u201D into a settled verdict. You said that cannot happen. '+
           'This is Broome\u2019s collapsing principle (<em>Weighing Lives</em> ch. 12), his argument that incomparability '+
           'and vagueness cannot both live in one betterness ordering. Note it is a constraint on the <em>determinacy</em> '+
           'of your ordering rather than on its content, so it is listed apart from the conflicts above \u2014 and it is '+
           'contested: Carlson and others have argued the principle is too strong.</p></div>';
        return h;
    },
    /* REVISE_ME */
    zrank:function(zr, n){
        var h='';
        h+='<div class="hit"><div class="tag">Conflict '+n+' &middot; '+
           (zr.via==="ladder"?"chaining through the gap":"ranking below the gap")+'</div>';
        h+='<h3 style="margin-top:10px">'+(zr.via==="ladder"
            ? "Declining to rank the rungs does not stop the ladder."
            : "You ranked Z, having put the boundary of your indeterminacy underneath it.")+'</h3>';
        h+='<ol class="claims">';
        zr.ids.forEach(function(id){ h+='<li>'+claimText(id)+'</li>'; });
        h+='</ol>';
        h+= zr.via==="ladder"
          ? '<p class="because">This is Parfit\u2019s mere addition argument, but run on <em>not worse than</em> instead of <em>better than</em>. Being unrankable, A+ is not worse than A. B is better than A+, so B is not worse than A+ either. You said both verdicts repeat at every rung, and you said not-worse-than chains, so it chains all '+(2*CHAIN.length)+' steps down the ladder: Z is not worse than A. But you also judged A better than Z, which is to say Z <em>is</em> worse than A. Declining to rank the rungs did not stop the contradiction, because an unrankable pair is still a pair where neither is worse.</p></div>'
          : '<p class="because">Take a neutral range as Broome does: a range of levels, shared by every addition, with a comparison coming out determinate only when it holds at every level in the range. Judging <strong>A better than Z</strong> then says something definite \u2014 that every level you would entertain sits <em>above</em> '+Z_LEVEL+
            ', the level Z\u2019s '+Z_POP[0].n.toLocaleString()+' people live at. Below that, Z\u2019s numbers win: at any level under '+Z_LEVEL+
            ' those lives are a gain, and '+Z_POP[0].n.toLocaleString()+' of them swamp what A\u2019s hundred lose. But calling the addition of a life at welfare '+zr.level+
            ' unrankable puts a level down at '+zr.level+', which is not above '+Z_LEVEL+
            '. You cannot have the boundary in both places. Note that this one, unlike the others, assumes your gaps come from a neutral range at all \u2014 so if you reject that picture, this is the conflict to argue with.</p></div>';
        return h;
    },
    /* REVISE_ME */
    greedy:function(gr, n){
        var h='', gh=gr.from-gr.to;
        h+='<div class="hit"><div class="tag">Conflict '+n+
           ' &middot; the greediness of neutrality</div>';
        h+='<h3 style="margin-top:10px">Your gap is wider than the harm you put beside it.</h3>';
        h+='<ol class="claims"><li>'+claimText("neutral_mod")+'</li><li>'+claimText("neutral_wond")+
           '</li><li>'+claimText("pareto")+'</li><li>'+claimText("greedy")+'</li></ol>';
        h+='<p class="because">Pareto puts K++ above K± — the same 501 people, Owen better off in one of them and nobody worse — so Owen’s loss counts as a loss on your own accounting. '+
           'What you do not have is any comparison between K and a world Nadia is in. Read your gaps the way Broome does, as a range of critical levels with a comparison coming out determinate only when it holds at every level in the range, and your two neutrality answers fix how wide that range is: calling the life at '+
           gr.level+' unrankable puts a level at or above '+gr.level+', calling the life at '+gr.floor+
           ' unrankable puts one at or below '+gr.floor+'. Adding Nadia at '+gr.level+
           ' is therefore worth anywhere from nothing to '+(gr.level-gr.floor)+' by your own account — and Owen’s '+gh+
           ' sits inside that. Whether K± falls below K depends on where in your own range the answer lands, so there is no fact of the matter about it, and you gave one anyway. '+
           'This is what Broome calls the <em>greediness</em> of the intuition of neutrality: it does not stay confined to the person being added. The wider the range of lives you are willing to call neutral, the larger the harm that disappears into the gap beside one of them. '+
           'Note that this one, like the misery route, assumes your gaps come from a neutral range at all — if you reject that picture, this is the conflict to argue with. What it is not is a way out through caution: the consistent answer is that K and K± cannot be ranked either, and that is a harm to somebody who exists either way going unsaid.</p></div>';
        return h;
    }
};

function showResults(){
    pruneInactive();
    // No verdict without a full run. A deep link into a late question, a
    // hand-edited fragment, a "&q=r" bookmark from a run that was later
    // reopened and edited, and an edit that brings a conditional question into
    // play all arrive here with holes in them, so the check sits at the one
    // gate they share rather than at each of them. Leaving a question blank is
    // not a position, and scoring it as one would put a verdict in the person's
    // mouth: every gap is silently read as "no edge", which is exactly what a
    // considered "cannot be ranked" looks like to the closure.
    var miss=missingActive();
    if(miss.length){
        var given=activeIdx().length-miss.length;
        // A link with nothing answered at all is not an incomplete run, it is
        // just the quiz; explaining the gap would be explaining the thing they
        // are about to do anyway.
        NOTICE = !given ? "" : (miss.length===1
            ? "One question is "
            : miss.length+" questions are ")
            + "still unanswered. Please answer the question below.";
        RETURNING=true;
        IDX=miss[0];
        show("quiz"); renderQ(); window.scrollTo({top:0});
        return;
    }
    RETURNING=false;
    var R=analyse(ANS);
    // Some story pairs (see STORIES' "group" field) are the same underlying
    // conflict argued at two different welfare levels; if both of a pair's
    // sets appear, keep only the first so it is counted and shown once.
    var seenGroups={};
    R.sets=R.sets.filter(function(S){
        var st=storyFor(S);
        if(st && st.group){
            if(seenGroups[st.group]) return false;
            seenGroups[st.group]=true;
        }
        return true;
    });
    // Conflicts are numbered in one sequence: the closure's sets first, then
    // one card per check that fired. cardNo carries the count across both, so
    // adding a check cannot renumber anything by hand.
    var nHits=R.sets.length + R.extras.length, cardNo=R.sets.length;
    var B=bullets();
    var h='';
    h+='<div class="hero" style="padding:6vh 0 0">';
    if(SHARED) h+='<div class="shared">Shared results &middot; someone else\u2019s answers, replayed from the link</div>';
    h+='<div class="kicker">The verdict</div>';
    h+='<h2 class="verdict">'+(nHits===0?"No conflicts.":(nHits===1?"One conflict.":nHits+" conflicts."))+'</h2>';
    h+='<div class="tally"><div><b>'+nHits+'</b>conflict'+(nHits===1?'':'s')+'</div><div><b>'+B.length+'</b>bullet'+(B.length===1?'':'s')+' bitten</div></div>';
    h+='<hr class="rule"></div>';

    h+='<p class="qbody" style="max-width:62ch">A <strong>conflict</strong> is a set of your answers that cannot all be true together. A <strong>bullet</strong> is a position of yours that is perfectly consistent, but implies a result that many find unpleasant or counterintuitive.</p>';

    if(nHits===0){
        h+='<div class="clean"><div class="eyebrow" style="color:var(--blue)">Clean crossing</div><h3 style="margin-top:8px">Nothing you said conflicts with anything else you said.</h3><p class="qbody">That\'s rarer than you might think. But consistency in population ethics must be bought with counter-intuitive conclusions. The bullets you\'ve bitten are listed below.</p></div>';
    }

    R.sets.forEach(function(S,i){
        var st=storyFor(S);
        h+='<div class="hit"><div class="tag">Conflict '+(i+1)+' &middot; '+S.size+' answers, jointly unsatisfiable</div>';
        // title, like because, may be read off the answers when one support
        // set is reached from several shapes.
        h+='<h3 style="margin-top:10px">'+
           (st ? (typeof st.title==="function"?st.title(ANS):st.title)
               : "These answers cannot all hold.")+'</h3>';
        h+='<ol class="claims">';
        QUESTIONS.forEach(function(q){ if(S.has(q.id)) h+='<li>'+claimText(q.id)+'</li>'; });
        h+='</ol>';
        // A story whose answers can differ behind one support set reads its
        // prose off the answers, so because may be a function of them.
        if(st){ h+='<p class="because">'+(typeof st.because==="function"?st.because(ANS):st.because)+'</p>'; }
        else { h+='<p class="because">If the principles of transitivity and menu-independence hold \u2014 and your answers said they do \u2014 then your ranking of outcomes contradicts itself.</p>'; }
        if(st&&st.chain){ h+='<div class="chainwrap">'+chainSVG(true)+'</div>'; }
        if(st&&st.world){ h+=worldNote(st.world); }
        h+='</div>';
    });

    R.extras.forEach(function(x){
        h+=CARD_HTML[x.id](x.data, ++cardNo);
    });

    if(B.length){
        h+='<hr class="rule thin" style="margin-top:44px"><div class="eyebrow">Bullets bitten</div>';
        B.forEach(function(b){ h+='<div class="bullet"><div class="tag">Consistent, but costly</div><h3 style="margin-top:8px">'+b.t+'</h3><p class="qbody" style="font-size:17px">'+b.b+'</p>'+(b.world?worldNote(b.world):'')+'</div>'; });
    }

    h+='<hr class="rule" style="margin-top:44px"><div class="eyebrow">Where you landed</div>';
    h+='<p class="qbody" style="font-size:19px">'+profile()+'</p>';

    h+='<hr class="rule thin"><div class="eyebrow">Your answers in full</div><table class="rev">';
    QUESTIONS.forEach(function(q){
        if(q.id==="menu" || ANS[q.id]===undefined) return;
        h+='<tr><td class="a">'+q.label+'</td><td>'+claimText(q.id)+'</td></tr>';
    });
    if(ANS.menu) h+='<tr><td class="a">Choosing from three</td><td>'+(
        ANS.menu==="none"    ? "None of A, B and Z is best." :
            ANS.menu==="abstain" ? "No view offered on which of A, B and Z is best." :
            ANS.menu+" is the best of A, B and Z.")+'</td></tr>';
    h+='</table>';

    h+='<hr class="rule thin" style="margin-top:44px"><div class="eyebrow">Save or share</div>';
    h+='<p class="qbody" style="font-size:17px">This link carries every answer you gave. Bookmark it to keep this page, or send it to someone and they will see exactly what you see.</p>';
    h+='<div class="sharebox"><input id="sharelink" readonly spellcheck="false" value="'+
        shareURL().replace(/&/g,"&amp;").replace(/"/g,"&quot;")+'"><button class="btn" id="copylink">Copy</button></div>';

    h+='<div class="nav" style="margin-top:38px">';
    // Nothing to go back to on a shared run: you landed here directly, and
    // stepping into question 12 would mean editing someone else's answers.
    h+= SHARED ? '<span></span>' : '<button class="btn ghost" id="rback">&larr; Back</button>';
    h+='<button class="btn ghost" id="again">'+
        (SHARED?"Take the test yourself":"Start over")+'</button></div>';

    var el=$("#results"); el.innerHTML=h;
    show("results"); syncHash();
    window.scrollTo({top:0,behavior:"smooth"});

    $("#again").addEventListener("click",function(){
        ANS={}; IDX=0; SHARED=false; RETURNING=false; NAME=""; show("quiz"); renderQ(); window.scrollTo({top:0});
    });
    if(!SHARED) $("#rback").addEventListener("click",function(){
        IDX=stepTo(QUESTIONS.length-1,-1); show("quiz"); renderQ(); window.scrollTo({top:0});
    });
    $("#copylink").addEventListener("click",copyLink);
}

function copyLink(){
    var inp=$("#sharelink"), btn=$("#copylink");
    inp.focus(); inp.select(); inp.setSelectionRange(0,inp.value.length);
    function say(ok){
        btn.textContent = ok ? "Copied" : "Press \u2318/Ctrl+C";
        setTimeout(function(){ btn.textContent="Copy"; },1800);
    }
    function legacy(){ try{ return document.execCommand("copy"); }catch(e){ return false; } }
    if(navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(inp.value).then(function(){ say(true); },function(){ say(legacy()); });
    } else say(legacy());
}

// Last, not earlier: restoring a finished run needs LABELS and STORIES, which
// are plain assignments further down the file.
boot();
