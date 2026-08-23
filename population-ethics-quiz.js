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
        id:"trans_gt", kind:"principle", label:"Transitivity of better-than",
        title:"Better than, and better than again.",
        body:"Take any three futures. Suppose the first is better than the second, and the second is better than the third.",
        ask:"Does it follow that the first is better than the third?",
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
    var E=[]; // {type:'gt'|'eq', a, b, sup:[ids]}
    function edge(type,a,b,sup){ E.push({type:type,a:a,b:b,sup:sup}); }
    function fromPair(qid,A,B,sup){
        var v=ans[qid]; if(!v||v==="none"||v==="abstain") return;
        if(v==="left")  edge("gt",A,B,sup);
        if(v==="right") edge("gt",B,A,sup);
        if(v==="equal") edge("eq",A,B,sup);
    }

    fromPair("AvB","A","B",["AvB"]);
    fromPair("AvZ","A","Z",["AvZ"]);
    fromPair("misery","K","K-",["misery"]);
    fromPair("neutral_mod","K","K+",["neutral_mod"]);
    fromPair("neutral_wond","K","K++",["neutral_wond"]);

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

    var N=names.length, gt=[], eq=[], i, j, k;
    for(i=0;i<N;i++){
        gt.push(new Array(N).fill(null));
        eq.push(new Array(N).fill(null));
    }
    function better(cur,cand){ return !cur || cand.size<cur.size; }

    edges.forEach(function(e){
        if(!supOK(e.sup)) return;
        var a=idx[e.a], b=idx[e.b];
        if(e.type==="gt"){
            var s=new Set(e.sup); if(better(gt[a][b],s)) gt[a][b]=s;
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
    return {gt:gt,eq:eq,names:names,N:N};
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

    // Contraction consistency (Sen's property alpha), checked separately:
    // it is a constraint on choice, not on the betterness ordering.
    var alpha=null;
    var declined=function(v){ return !v||v==="none"||v==="abstain"; };
    if(!declined(ans.menu) && !declined(ans.AvB)){
        var pick=ans.menu;
        var pairWinner = ans.AvB==="left" ? "A" : ans.AvB==="right" ? "B" : "tie";
        if((pick==="A"||pick==="B") && pairWinner!=="tie" && pick!==pairWinner){
            alpha={picked:pick, pairWinner:pairWinner};
        }
        if(pick==="Z" && ans.AvZ==="left") alpha={picked:"Z", pairWinner:"A", viaZ:true};
    }
    // Broome's collapsing principle (Weighing Lives ch. 12), checked separately
    // for the same reason as alpha: "cannot be ranked" emits no edge, so the
    // closure machinery can never see it. Without this, an incomparabilist is
    // unfalsifiable here no matter what else they say.
    var collapse = ans.collapse==="yes" ? collapseCandidate(ans) : null;

    return {sets:sets, alpha:alpha, collapse:collapse, clashes:clashes};
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
    var SC=1.75, baseGap=90, basePad=34;
    opts=opts||{};
    var hasTag=popsList.some(function(p){ return p.some(function(g){ return g.tag; }); });

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
    var nameY  = baseY + drop + (hasTag? 60:30);
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
        var bx=x;
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
                s+='<line x1="'+cx.toFixed(1)+'" y1="'+(pos? baseY+4 : baseY+h+26).toFixed(1)+
                    '" x2="'+cx.toFixed(1)+'" y2="'+(tagY-13)+'" stroke="var(--ink)" stroke-width="1"/>';
                s+='<text x="'+cx.toFixed(1)+'" y="'+tagY+'" text-anchor="middle" font-family="Space Mono, monospace" '+
                    'font-size="'+FS.tag+'" letter-spacing=".06em" fill="var(--ink)">'+g.tag+'</text>';
            }
            bx+=gw;
        });
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
    AvB:function(a){ return "A is "+({left:"better than",right:"worse than",equal:"exactly as good as",none:"not rankable against"}[a])+" B."; },
    AvZ:function(a){ return "A is "+({left:"better than",right:"worse than",equal:"exactly as good as",none:"not rankable against"}[a])+" Z."; },
    misery:function(a){ return "Adding Nadia with a life of suffering makes the outcome "+({left:"worse",right:"better",equal:"neither better nor worse",none:"incomparable"}[a])+"."; },
    neutral_mod:function(a){ return "Adding Nadia with a modest good life makes the outcome "+({left:"worse",right:"better",equal:"neither better nor worse",none:"incomparable"}[a])+"."; },
    neutral_wond:function(a){ return "Adding Nadia with a wonderful life makes the outcome "+({left:"worse",right:"better",equal:"neither better nor worse",none:"incomparable"}[a])+"."; },
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
    trans_eq:function(a){ return {
        yes:"\u201CExactly as good as\u201D is transitive.",
        no:"\u201CExactly as good as\u201D is not always transitive.",
        abstain:"No view on whether \u201Cexactly as good as\u201D is transitive."}[a]; }
};
function claimText(id){
    var v=LABELS[id];
    return (typeof v==="function") ? v(ANS[id]) : v;
}

var STORIES=[
    {
        needs:["benign","nae","trans_gt","AvB"],
        title:"The ladder reaches B, but you say B is worse.",
        because:"Two rungs are all it takes. If A+ improves on A, and B improves on A+, then transitivity delivers B over A. You also judged A over B directly. One of those four has to go — and notice how little the argument needed: no vast numbers, no lives barely worth living, just one application of each move.",
        world:"Because it takes only two rungs, this one does not need a distant future to bite. A country that raises living standards for everyone already in it while a further cohort arrives or is born who live somewhat less well has taken the first step; a redistribution that levels the two groups is the second. Both are ordinary decades of policy. Your answers call each move an improvement and the destination worse than the start."
    },
    {
        needs:["benign","nae","generalize","trans_gt","AvZ"],
        title:"The ladder reaches Z, and the loop closes.",
        because:"This is Parfit's mere addition argument. Each rung is a step you endorsed and said you would endorse again; transitivity chains them the whole way down; and the last judgement swings back from the bottom of the ladder to the top. The relation \u201Cbetter than\u201D now runs in a circle.",
        world:"The ladder is the shape of the long-run question: how large humanity should aim to become. Every rung is the trade a growth-maximising trajectory keeps making — more people, each with somewhat less — and each one taken singly looks like a gain. Endorsing every step while rejecting where they lead leaves you with no principled place to stop, which is the practical problem rather than the formal one.",
        chain:true
    },
    {
        needs:["misery","neutral_mod","pareto","trans_eq","menu_eq"],
        title:"Nadia cannot be worth nothing whichever way her life goes.",
        because:"You said K is exactly as good as the world where Nadia exists in agony, and exactly as good as the world where she exists with a decent life. Transitivity of equal-goodness makes those two worlds exactly as good as each other. But they contain the same 501 people, and Nadia is enormously better off in one of them. This is Broome's neutral-range argument run downwards: if bringing someone into existence is never better or worse, it cannot matter how their life then goes \u2014 and it plainly does.",
        world:"Held outside the diagram, the neutrality says this: a couple who knowingly conceive a child destined for a short life of unrelieved pain make the world no worse by doing it, and a couple who conceive a child with every prospect of a decent life make it no better. Chain the two and the acts come out exactly equivalent. Nearly everyone treats the first as a serious wrong and the second as unobjectionable, which is a sign that the neutrality is not really being held at both ends.",
        // Same argument as the wonderful-life version below, just run at the
        // lower welfare level; if both trigger they should count once, not twice.
        group:"nadiaNeutralRange"
    },
    {
        needs:["misery","neutral_wond","pareto","trans_eq","menu_eq"],
        title:"Nadia cannot be worth nothing whichever way her life goes.",
        because:"You said K is exactly as good as the world where Nadia exists in agony, and exactly as good as the world where she exists with a wonderful life. Transitivity of equal-goodness makes those two worlds exactly as good as each other, yet they contain the same 501 people and Nadia is enormously better off in one. Whatever is attractive about \u201Cmerely possible people do not count\u201D, it cannot survive being applied at both ends of the scale at once.",
        world:"Held outside the diagram, the neutrality says this: a couple who knowingly conceive a child destined for a short life of unrelieved pain make the world no worse by doing it, and a couple who conceive a child with every prospect of flourishing make it no better. Chain the two and the acts come out exactly equivalent. Nearly everyone treats the first as a serious wrong and the second as unobjectionable, which is a sign that the neutrality is not really being held at both ends.",
        group:"nadiaNeutralRange"
    },
    {
        needs:["neutral_mod","neutral_wond","trans_eq","menu_eq","pareto"],
        title:"Nadia's life cannot be worth nothing twice over.",
        because:"You said K is exactly as good as the world with Nadia in it at welfare 7, and exactly as good as the world with Nadia in it at welfare 70. Transitivity of equal-goodness makes those two worlds exactly as good as each other. But they contain the same people, and Nadia is far better off in one. This is Broome's argument in <em>Weighing Lives</em> ch. 10 that there can be no neutral <em>range</em> \u2014 at most a neutral point.",
        world:"The non-identity problem, in Boonin's version of it. Wilma is told that a child conceived now will be born blind, and that if she takes a pill daily for two months first, she will conceive a different child, who will see. Almost everyone says she should wait. It cannot be better <em>for</em> anyone: the child conceived now would otherwise never have existed, and so is not made worse off by the wait. The verdict has to come from the difference between two possible lives, and your answers say that difference carries no weight, because a created life is worth neither more nor less than no life at whatever level it goes. Notice how little the case turns on besides the population question: no screening, no selection among embryos, no judgement about who deserves to exist — only which month. Parfit puts the same point as a policy choice, in the Medical Programmes of <em>Reasons and Persons</em>: a health service must cancel either preconception testing or pregnancy testing, and a thousand children are affected either way."
    }
];
function storyFor(set){
    for(var i=0;i<STORIES.length;i++){
        var s=STORIES[i], ok=true;
        if(s.needs.length!==set.size) ok=false;
        else s.needs.forEach(function(n){ if(!set.has(n)) ok=false; });
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
    return '<div class="world"><div class="tag">Where this bites</div><p>'+s+'</p></div>';
}

function bullets(){
    var out=[];
    if(ANS.trans_gt==="no") out.push({t:"You rejected transitivity of better-than.",b:"That is a live position \u2014 Temkin and Rachels both take it \u2014 and it defuses most of the paradoxes here at a stroke. The price is that \u201Cbetter than\u201D can now run in circles, which makes it hard to say what you should be aiming at: for any option there may be a better one that is in turn worse than where you started.",
        world:"Policy moves in steps, and this is where the price is paid. A view that ranks each step an improvement without ranking the destination above the start can be walked, one defensible move at a time, to a place it calls worse than where it began — and it has no principled objection to lodge against any individual step along the way."});
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
        out.push({t:"You denied that a verdict survives a wider menu.",b:"Your pairwise judgements no longer have to cohere into a single ordering: each one is indexed to the pair it was made in, and putting a third option on the table can revise it. This blocks the chaining that most of the conflicts here run on."+worked+" The cost is a known one: it is a violation of Sen\u2019s property &beta;, expansion consistency \u2014 the companion of the property &alpha; that the three-way choice tests. An option tied for best in a pair drops below its rival the moment a third arrives. You are also committed to there being no such thing as how good an outcome is <em>full stop</em>, only how good it is against a particular field."});
    }

    if(ANS.trans_eq==="no") out.push({t:"You rejected transitivity of equal-goodness.",b:"This is the standard escape from the neutral-range argument, and it usually comes packaged as the claim that some outcomes are only <em>roughly</em> comparable rather than exactly equal. Be warned that it is not a way out of Broome generally: he devotes a later chapter to arguing that rough comparability cannot be a stable resting place either."});
    if(ANS.pareto==="no") out.push({t:"You rejected the Pareto principle.",b:"Denying that a world is better when the very same people are all better off in it is about as revisionary as population ethics gets. Almost every theory in the field takes this as a fixed point."});
    if(ANS.AvZ==="right") out.push({t:"You accepted the repugnant conclusion.",b:"You judged Z better than A: enough lives barely worth living outweigh a small number of superb ones. This is the totalist's answer and it is entirely consistent \u2014 Tännsjö, Huemer and others defend it explicitly. It also means there is in principle no quality of life so marginal that sheer numbers cannot compensate.",
        world:"Taken as a guide to the long run, this says that a future of tens of billions living at bare subsistence is an improvement on a smaller humanity that is thriving, provided the numbers run high enough. Trajectories that maximise headcount — settle everything settleable, run every population up to what it can carry — come out ahead of trajectories that keep a smaller humanity rich. Totalists generally accept this openly rather than looking for a way around it."});
    if(ANS.generalize==="no") out.push({t:"You said the verdict flips somewhere on the ladder.",b:"That blocks the argument, but it leaves you owing an account of <em>where</em>. Every rung is qualitatively identical to every other; if rung 4 is fine and rung 5 is not, something must distinguish them. Critical-level and lexical views are attempts to say what.",
        world:"In practice this resolves into a number. If more people with decent lives is a gain now and stops being one later, there is some population size, or some quality of life, at which the verdict turns over. Whatever fixes that threshold is then the thing actually doing the work in your view of growth, migration and fertility — so it is worth knowing what it is, rather than leaving it to be settled case by case."});
    // Revisionary pair verdicts. The principles all draw a comment when rejected;
    // without these, a verdict like "her agony is a gain" could pass in silence.
    if(ANS.misery==="right") out.push({t:"You counted a life of suffering as a gain.",b:"When Nadia\u2019s life holds far more suffering than good \u2014 a life it would have been better for her never to have had \u2014 you judged the world better for containing it.",
        world:"Outside the diagram this is a reason — slight, and outweighable, but a reason all the same — to bring into existence children whose lives will hold far more suffering than good, and to regret it when such a birth is prevented."});

    if(ANS.neutral_mod==="left" || ANS.neutral_wond==="left") out.push({t:"You said a life worth living makes the world worse by being lived.",b:"This goes well past the Procreation Asymmetry, which claims only that creating a happy person is not <em>good</em>. You have said it is positively <em>bad</em>.",
        world:"This is the antinatalist's conclusion, in a stronger form than the one usually defended. It says a happy child is a cost the world bears rather than a gain it makes, and that there is reason — outweighable by the interests of the parents, but real — to prevent the birth of people with good lives ahead of them."});

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

    if(ANS.benign==="left") out.push({t:"Everyone gains, good lives are added, and you called it worse.",b:"Every one of A\u2019s hundred is better off in A+, and a further hundred exist there with lives clearly worth living. Ranking that below A means the new lives are a cost heavy enough to outweigh a gain to every person who was already there. It does block Parfit\u2019s argument at the first rung, which is more than most escapes manage. The price is what it commits you to elsewhere: you would prefer the original hundred be worse off, so long as fewer people existed alongside them.",
        world:"Consider a public health programme that makes everyone it reaches better off and, by reducing child mortality, also results in more people growing up alongside them at a lower standard of living. Your answer allows that combination to be a change for the worse — not because anyone alive loses anything, but because of who else ends up existing. Notice this is a verdict about the outcome, quite apart from the familiar worries about resources and capacity, which would be reasons to expect the first group not to gain at all."});

    if(ANS.nae!=="right") out.push({t:"You denied that levelling up improves things.",b:"B holds the same "+CHAIN[0].to.n+" people as A+, with more welfare in total, more on average, and more equality. There is a consistent motive available \u2014 the better-off group does lose, falling from "+CHAIN[0].plus[0].w+" to "+CHAIN[0].to.w+", while the worse-off rise from "+CHAIN[0].plus[1].w+" \u2014 so a view that weighs losses to the well-off heavily can resist it. But it sets you against totalism, averagism and egalitarianism in one move.",
        world:"The move has an everyday form: a transfer that more than pays for itself, where the same people are involved throughout, the badly-off rise further than the well-off fall, and there is more to go round afterwards than before. Declining to call that an improvement is a commitment you will meet again well outside population ethics, in tax policy and in almost any argument about redistribution."});

    var noneCount=0;
    ["AvB","AvZ","misery","neutral_mod","neutral_wond","benign","nae"].forEach(function(k){
        if(ANS[k]==="none") noneCount++;
    });
    if(noneCount>=3) out.push({t:noneCount===7?"You judged none of the seven pairs rankable.":"You judged "+noneCount+" of the 7 pairs unrankable.",b:"You said that these pairs were not <em>equal</em>, but that no betterness relation holds either way. An ordering with widespread incomparability cannot do much practical work \u2014 it will stay silent on most of the choices you would want it to settle.",
        world:"Climate policy is the clearest case, along with anything else whose horizon is long enough to change who gets born. Emissions paths do not merely leave future people better or worse off; over a century or two they alter which future people there are, down to the individual. Ranking those futures is the whole of the argument, so a view that declines to rank them does not take a cautious position in the debate — it withdraws from it."});
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
        out.push({t:"You hold the Procreation Asymmetry.",b:"Creating a miserable life is bad; creating a happy one is not good. This is what most people say, and it is not formally inconsistent on its own \u2014 which is why it is not scored as a conflict here. It is, however, notoriously hard to ground: the obvious explanations of the first half tend to imply the opposite of the second."+route,
            world:"The sharpest case is human extinction. If creating a happy life is not good, then the people who would have lived in the centuries after a catastrophe are no part of what that catastrophe destroys, and human extinction is exactly as bad as a disaster that kills the same number and leaves a remnant to carry on — no worse, because the difference between the two is entirely a difference in who never gets born. Most people who hold the asymmetry do not believe that, and the gap between the two judgements is where the pressure on this view actually shows up."});
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
    var nHits=R.sets.length + (R.alpha?1:0) + (R.collapse?1:0);
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
        h+='<div class="clean"><div class="eyebrow" style="color:var(--blue)">Clean crossing</div><h3 style="margin-top:8px">Nothing you said collides with anything else you said.</h3><p class="qbody">That is rarer than it sounds, and it is worth knowing how you managed it. Look at the bullets below: consistency in population ethics is always bought somewhere, and those are the places you spent.</p></div>';
    }

    R.sets.forEach(function(S,i){
        var st=storyFor(S);
        h+='<div class="hit"><div class="tag">Conflict '+(i+1)+' &middot; '+S.size+' answers, jointly unsatisfiable</div>';
        h+='<h3 style="margin-top:10px">'+(st?st.title:"These answers cannot all hold.")+'</h3>';
        h+='<ol class="claims">';
        QUESTIONS.forEach(function(q){ if(S.has(q.id)) h+='<li>'+claimText(q.id)+'</li>'; });
        h+='</ol>';
        if(st){ h+='<p class="because">'+st.because+'</p>'; }
        else { h+='<p class="because">Closing your judgements under the transitivity principles you accepted produces a pair of outcomes ranked in both directions at once. Dropping any one of the answers above dissolves it; keeping all of them does not.</p>'; }
        if(st&&st.chain){ h+='<div class="chainwrap">'+chainSVG(true)+'</div>'; }
        if(st&&st.world){ h+=worldNote(st.world); }
        h+='</div>';
    });

    if(R.alpha){
        h+='<div class="hit"><div class="tag">Conflict '+(R.sets.length+1)+' &middot; contraction inconsistency</div>';
        h+='<h3 style="margin-top:10px">Adding a third option changed your mind about the first two.</h3>';
        h+='<ol class="claims"><li>Offered A and B alone, you judged '+R.alpha.pairWinner+' the better of the two.</li>';
        h+='<li>Offered A, B and Z together, you picked '+R.alpha.picked+' as best.</li></ol>';
        h+='<p class="because">This violates Sen\u2019s property &alpha;: if something is best in a set, it must still be best in any subset that contains it. Z\u2019s presence cannot make '+R.alpha.picked+' beat '+R.alpha.pairWinner+' if it did not already. Note that this is a constraint on <em>choice</em> rather than on the betterness ordering \u2014 the choice-theoretic cousin of independence of irrelevant alternatives \u2014 so it is listed separately from the conflicts above.</p>'+
           worldNote('This is the structure of a spoiler on a ballot. If a third option can reverse how you rank the first two simply by being present, then which future you favour depends on what else happens to be under discussion — and an option nobody would ever choose can still decide the outcome. In population ethics the tabled-but-unchosen option is usually the extreme case, Z or something like it, raised in argument by someone who has no intention of advocating it.')+'</div>';
    }

    if(R.collapse){
        var vg=R.collapse.vague, an=R.collapse.anchor;
        h+='<div class="hit"><div class="tag">Conflict '+(R.sets.length+(R.alpha?1:0)+1)+' &middot; collapsing principle</div>';
        h+='<h3 style="margin-top:10px">Your unrankable case has a determinate one right next to it.</h3>';
        h+='<ol class="claims"><li>'+claimText(vg.id)+'</li><li>'+claimText(an.id)+'</li><li>'+claimText("collapse")+'</li></ol>';
        h+='<p class="because">You placed '+vg.world+' beyond ranking against K, while '+an.world+
           ' \u2014 the same world with Nadia\u2019s life going '+(R.collapse.dir==="up"?"better":"worse")+
           ' \u2014 you ranked determinately. Between welfare '+
           Math.min(vg.w,an.w)+' and '+Math.max(vg.w,an.w)+' for her, then, lies a point where one unit of wellbeing '+
           'converts \u201Cno fact of the matter\u201D into a settled verdict. You said that cannot happen. '+
           'This is Broome\u2019s collapsing principle (<em>Weighing Lives</em> ch. 12), his argument that incomparability '+
           'and vagueness cannot both live in one betterness ordering. Note it is a constraint on the <em>determinacy</em> '+
           'of your ordering rather than on its content, so it is listed apart from the conflicts above \u2014 and it is '+
           'contested: Carlson and others have argued the principle is too strong.</p></div>';
    }

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
