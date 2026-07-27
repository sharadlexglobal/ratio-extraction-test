#!/usr/bin/env python3
"""
Head-to-head on judge-annotated ground truth:
  A) the pattern rules I wrote
  B) the ready-made OpenNyAI rhetorical-role model
Both are scored on the SAME sentences from the BUILD dataset (CC-BY-SA 4.0),
where law students annotated every sentence of 247 Indian judgments.
"""
import json, re, os, sys, time, urllib.request

LIMIT   = int(os.environ.get("RATIO_TEST_DOCS", "40"))
TARGET  = {"RATIO", "RPC"}          # the holding, and the ruling of the present court
DATA    = ("https://storage.googleapis.com/indianlegalbert/OPEN_SOURCED_FILES/"
           "Rhetorical_Role_Benchmark/Data/dev.json")

def log(*a): print(time.strftime("[%H:%M:%S]"), *a, flush=True)

# ---- A) my rules ----
HOLD = re.compile(r'\b(?:is|are)\s+held\s+|we\s+(?:hold|are of the (?:considered )?(?:view|opinion))|'
                  r'it\s+is\s+held|held\s+entitled|this\s+court\s+holds|'
                  r'for\s+the\s+foregoing\s+reasons|in\s+the\s+light\s+of\s+the\s+above', re.I)

def rules_predict(sents):
    """A sentence is ratio if it carries a holding phrase and sits in the back half."""
    n = len(sents)
    return [bool(HOLD.search(s)) and (i / max(n - 1, 1)) > 0.5 for i, s in enumerate(sents)]

# ---- scoring ----
def score(name, gold, pred):
    tp = sum(1 for g, p in zip(gold, pred) if g and p)
    fp = sum(1 for g, p in zip(gold, pred) if not g and p)
    fn = sum(1 for g, p in zip(gold, pred) if g and not p)
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
    log(f"{name:34} precision {pr:.2f}  recall {rc:.2f}  F1 {f1:.2f}   (tp={tp} fp={fp} fn={fn})")
    return {"name": name, "precision": round(pr, 3), "recall": round(rc, 3),
            "f1": round(f1, 3), "tp": tp, "fp": fp, "fn": fn}

def main():
    log("downloading judge-annotated ground truth ...")
    docs = json.load(urllib.request.urlopen(DATA, timeout=180))
    docs = [d for d in docs
            if any(r["value"]["labels"][0] in TARGET for r in d["annotations"][0]["result"])][:LIMIT]
    log(f"{len(docs)} annotated judgments in this test")

    all_sents, all_gold, doc_bounds = [], [], []
    for d in docs:
        res = sorted(d["annotations"][0]["result"], key=lambda r: r["value"]["start"])
        s0 = len(all_sents)
        for r in res:
            v = r["value"]
            txt = re.sub(r"\s+", " ", v["text"]).strip()
            if len(txt) < 25:
                continue
            all_sents.append(txt)
            all_gold.append(v["labels"][0] in TARGET)
        doc_bounds.append((s0, len(all_sents)))
    log(f"{len(all_sents)} sentences | {sum(all_gold)} of them labelled RATIO/RPC by humans")

    results = []
    # A) rules
    pred_rules = []
    for a, b in doc_bounds:
        pred_rules += rules_predict(all_sents[a:b])
    results.append(score("A) my pattern rules", all_gold, pred_rules))

    # B) ready-made model
    try:
        log("loading the ready-made OpenNyAI rhetorical-role model ...")
        t0 = time.time()
        import opennyai
        from opennyai import Pipeline
        from opennyai.utils import Data
        pipe = Pipeline(components=['Rhetorical_Role'], use_gpu=False, verbose=False)
        log(f"model loaded in {time.time()-t0:.0f}s")
        pred_model = [False] * len(all_sents)
        t0 = time.time()
        for di, (a, b) in enumerate(doc_bounds, 1):
            text = " ".join(all_sents[a:b])
            out = pipe(Data([text]))
            got = out[0] if isinstance(out, list) else out
            spans = (got.get("annotations") or got.get("rhetorical_roles") or [])
            marked = []
            for sp in spans:
                lab = (sp.get("labels") or [sp.get("label")])[0]
                if lab in TARGET:
                    marked.append(re.sub(r"\s+", " ", sp.get("text", "")).strip().lower())
            for i in range(a, b):
                s = all_sents[i].lower()
                if any(s[:70] in m or m[:70] in s for m in marked if m):
                    pred_model[i] = True
            if di % 10 == 0:
                log(f"   model: {di}/{len(doc_bounds)} judgments, {time.time()-t0:.0f}s")
        el = time.time() - t0
        log(f"model finished {len(doc_bounds)} judgments in {el:.0f}s "
            f"({len(doc_bounds)/max(el,1):.2f} judgments/sec)")
        results.append(score("B) ready-made OpenNyAI model", all_gold, pred_model))
    except Exception as e:
        log("MODEL FAILED:", type(e).__name__, str(e)[:400])
        results.append({"name": "B) ready-made OpenNyAI model",
                        "error": f"{type(e).__name__}: {str(e)[:300]}"})

    log("")
    log("==== RESULT ====")
    log(json.dumps(results, indent=1))

if __name__ == "__main__":
    main()
