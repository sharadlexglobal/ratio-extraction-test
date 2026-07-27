#!/usr/bin/env python3
"""
Full pipeline on ONE real judgment, end to end, inside Render:
  PDF (AWS open data) -> text -> case metadata -> Acts & Sections
  -> precedents -> the holding/ratio, using a detector trained here at start-up
     on the BUILD corpus (OpenNyAI / EkStep, CC BY-SA 4.0).
Prints the complete structured response.
"""
import json, re, os, sys, time, subprocess, urllib.request
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from scipy.sparse import hstack, csr_matrix

PDF = os.environ.get("PDF_KEY",
    "data/pdf/year=2017/court=7_26/bench=dhcdb/DLHC011844242017_1_2017-07-03.pdf")
S3  = "https://indian-high-court-judgments.s3.ap-south-1.amazonaws.com/"
BUILD = ("https://storage.googleapis.com/indianlegalbert/OPEN_SOURCED_FILES/"
         "Rhetorical_Role_Benchmark/Data/train.json")
TARGET = {"RATIO", "RPC"}

def log(*a): print(time.strftime("[%H:%M:%S]"), *a, flush=True)
def sq(s): return re.sub(r"\s+", " ", s).strip()

# ---------- ratio detector ----------
def feats(sents, pos):
    f = []
    for s, p in zip(sents, pos):
        f.append([p, p*p, min(len(s), 600)/600,
                  1.0 if re.search(r'\b(held|hold|holds)\b', s, re.I) else 0.0,
                  1.0 if re.search(r'\ballowed|dismissed|disposed|set aside|quashed\b', s, re.I) else 0.0,
                  1.0 if re.search(r'\b(?:accordingly|therefore|thus|hence|in view of)\b', s, re.I) else 0.0,
                  1.0 if re.search(r'\bappeal|petition|application|suit\b', s, re.I) else 0.0])
    return csr_matrix(np.array(f))

def train():
    log("training the ratio detector on judge-annotated judgments ...")
    docs = json.load(urllib.request.urlopen(BUILD, timeout=180))
    X, y, pos = [], [], []
    for d in docs:
        res = sorted(d["annotations"][0]["result"], key=lambda r: r["value"]["start"])
        ss = [(sq(r["value"]["text"]), r["value"]["labels"][0]) for r in res]
        ss = [(a, b) for a, b in ss if len(a) >= 25]
        n = len(ss)
        for i, (a, b) in enumerate(ss):
            X.append(a); y.append(1 if b in TARGET else 0); pos.append(i/max(n-1, 1))
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=60000,
                          sublinear_tf=True, strip_accents="unicode")
    A = hstack([vec.fit_transform(X), feats(X, np.array(pos))]).tocsr()
    clf = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced").fit(A, np.array(y))
    log(f"trained on {len(X)} annotated sentences ({sum(y)} of them ratio)")
    return vec, clf

# ---------- structure ----------
COURT = re.compile(r'IN THE (HIGH COURT OF [A-Z ,&]+?|SUPREME COURT[A-Z ]*)\n', re.I)
CASENO= re.compile(r'\b((?:CRL\.?\s?[A-Z.()]*|W\.?P\.?\(?[A-Z]{0,4}\)?|CS\(OS\)|LPA|RFA|FAO|CM|ITA)\.?\s*(?:No\.?s?\.?)?\s*\d+\s*/\s*\d{4})', re.I)
JUDGE = re.compile(r"HON'?BLE\s+(?:MR\.?|MS\.?|MRS\.?|DR\.?)?\s*JUSTICE\s+([A-Z][A-Z.\s]+?)(?:\n|$)")
RES   = re.compile(r'RESERVED ON\s*:?\s*([\d./-]{6,12})', re.I)
PRO   = re.compile(r'(?:PRONOUNCED|DECIDED) ON\s*:?\s*([\d./-]{6,12})', re.I)
MARK  = re.compile(r'\.{3,}\s*(Petitioner|Appellant|Respondent|Defendant|Complainant)s?\b', re.I)
ACTSEC= re.compile(r'(?:[Ss]ections?|[Rr]ules?|[Aa]rticles?)\s+([0-9A-Z()\s,and&/-]{1,40}?)\s+of\s+(?:the\s+)?([A-Z][A-Za-z\s,.\'()-]{4,80}?(?:Act|Code|Rules|Constitution)(?:,?\s*\d{4})?)')
CITE  = re.compile(r'\b([A-Z][A-Za-z&.\s]{2,60}?\s+v(?:s|\.)?\.?\s+[A-Z][A-Za-z&.\s]{2,60}?)[,\s]*(?:[\(\[]?(\d{4})[\)\]]?\s*[\(\[]?(\d{0,3})[\)\]]?)\s*(SCC|AIR|SCR|SCALE|DLT|Del|Cri\.?\s?L\.?\s?J\.?)\s*(\d{1,4})')

def parties(h, want):
    out = []
    for m in MARK.finditer(h):
        if m.group(1).lower() not in want: continue
        for cand in reversed([sq(x) for x in h[:m.start()].split("\n") if sq(x)][-4:]):
            if re.match(r'^(versus|vs\.?|through|coram|\+|\*|%|\$~)', cand, re.I): continue
            if len(cand) > 1: out.append(cand); break
    return out[:3]

def main():
    vec, clf = train()
    log(f"fetching judgment: {PDF}")
    data = urllib.request.urlopen(S3 + PDF, timeout=120).read()
    txt = subprocess.run(["pdftotext", "-q", "-", "-"], input=data,
                         capture_output=True).stdout.decode("utf8", "ignore")
    log(f"extracted {len(txt):,} characters")
    head = txt[:3500]
    body = re.sub(r'\n?Page \d+ of \d+\n?', '\n', txt)
    body = re.split(r'\n\s*(?:JUDGMENT|ORDER)\s*\n', body, maxsplit=1, flags=re.I)[-1]

    sents = [sq(s) for s in re.split(r'(?<=[.;])\s+(?=[A-Z“"])', body)]
    sents = [s for s in sents if len(s) >= 40]
    n = len(sents)
    pos = np.array([i/max(n-1, 1) for i in range(n)])
    P = clf.predict_proba(hstack([vec.transform(sents), feats(sents, pos)]).tocsr())[:, 1]

    sa = {}
    for sec, act in ACTSEC.findall(txt):
        for s in re.split(r'[,&]|\band\b', sec):
            s = s.strip(" .")
            if re.match(r'^\d', s): sa.setdefault(sq(act), set()).add(s)
    seen, prec = set(), []
    for c, yr, vol, rep, pg in CITE.findall(txt):
        c = sq(re.sub(r'^(?:in|see|per|and|the|of)\s+', '', sq(c), flags=re.I))
        if c.lower() in seen or len(c) > 90: continue
        seen.add(c.lower())
        prec.append({"case": c, "citation": sq(f"({yr}) {vol} {rep} {pg}" if vol else f"{yr} {rep} {pg}")})

    m = COURT.search(txt)
    out = {
      "source_pdf": S3 + PDF,
      "court": sq(m.group(1)) if m else None,
      "case_numbers": sorted({sq(x) for x in CASENO.findall(head)})[:5],
      "bench": [sq(x) for x in JUDGE.findall(head)][:3],
      "reserved_on": (RES.search(txt).group(1) if RES.search(txt) else None),
      "pronounced_on": (PRO.search(txt).group(1) if PRO.search(txt) else None),
      "appellants": parties(head, {"appellant", "petitioner", "complainant"}),
      "respondents": parties(head, {"respondent", "defendant"}),
      "statutes_applied": [{"act": a, "sections": sorted(v)} for a, v in sorted(sa.items())][:10],
      "precedents_cited": prec[:10],
      "sentences_analysed": n,
      "ratio_and_holding": [
          {"confidence": f"{P[i]*100:.0f}%", "sentence_no": int(i)+1, "text": sents[i][:600]}
          for i in np.argsort(-P)[:8] if P[i] >= 0.70
      ],
    }
    print("\n" + "="*78)
    print("COMPLETE STRUCTURED RESPONSE FOR ONE CRIMINAL JUDGMENT")
    print("="*78)
    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
