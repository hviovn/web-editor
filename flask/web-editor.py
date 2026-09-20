import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# A disposable checkout is kept inside this repository and refreshed when the
# process starts. Override these values for deployments that use another URL
# or work directory.
TIMELINE_URL = os.environ.get("TIMELINE_REPO_URL", "https://github.com/kreier/timeline.git")
WORK_DIR = Path(os.environ.get(
    "TIMELINE_WORK_DIR",
    Path(__file__).resolve().parent.parent / "workfolder" / "timeline",
)).resolve()
BASE_DIR = WORK_DIR / "db"
SUPPORTED_LANG_FILE = BASE_DIR / "supported_languages.csv"

DATA_CACHE, ORIGINAL_CACHE, HISTORY = {}, {}, {}


def git(*args):
    return subprocess.run(["git", *args], check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def prepare_timeline_checkout():
    """Clone or refresh the timeline checkout used by this server.

    Only the timeline working copy is changed; the web-editor repository is
    never used as the data source and no files are copied into its tree except
    the ignored workfolder checkout.
    """
    WORK_DIR.parent.mkdir(parents=True, exist_ok=True)
    git_dir = WORK_DIR / ".git"
    if not git_dir.is_dir():
        if WORK_DIR.exists():
            shutil.rmtree(WORK_DIR)
        git("clone", "--depth", "1", "--branch", "main", TIMELINE_URL,
            str(WORK_DIR))
    else:
        git("-C", str(WORK_DIR), "fetch", "--depth", "1", "origin", "main")
        git("-C", str(WORK_DIR), "reset", "--hard", "origin/main")
    if not SUPPORTED_LANG_FILE.is_file():
        raise RuntimeError(f"timeline checkout has no db directory: {BASE_DIR}")


# Pull the data once before serving requests. A deployment can fail early
# rather than silently presenting an empty editor.
prepare_timeline_checkout()


def load_supported_languages():
    df = pd.read_csv(SUPPORTED_LANG_FILE)
    return df[df["dict"] == True][["key", "language_str"]].to_dict("records")


def dict_path(lang):
    return BASE_DIR / f"dictionary_{lang}.csv"


def load_dict(lang):
    if lang not in DATA_CACHE:
        path = dict_path(lang)
        df = pd.read_csv(path) if path.is_file() else pd.DataFrame(
            columns=["key", "text", "english", "tag", "checked"])
        if "checked" not in df.columns:
            df["checked"] = False
        DATA_CACHE[lang] = df.copy()
        ORIGINAL_CACHE[lang] = df.copy()
        HISTORY[lang] = []
    return DATA_CACHE[lang]


def save_dict(lang):
    DATA_CACHE[lang].to_csv(dict_path(lang), index=False)
    ORIGINAL_CACHE[lang] = DATA_CACHE[lang].copy()
    HISTORY[lang] = []


def filter_df(df, tag):
    tags = {"a6": ["a6-a", "a6-b"], "b9": ["b9"], "wiki": ["wiki"],
            "others": ["deprecated", "scripture", "span_bc", "span_bce", "span_ce"]}
    values = tags.get(tag.lower(), [tag.lower()])
    return df[df["tag"].fillna("").str.lower().isin(values)]


def record_history(lang, key, column, old, new):
    HISTORY.setdefault(lang, []).append({"key": key, "col": column, "old": old, "new": new})


@app.route("/api/languages")
def api_languages():
    return jsonify(load_supported_languages())


@app.route("/api/data")
def api_data():
    df = filter_df(load_dict(request.args.get("lang", "de")), request.args.get("tag", "text"))
    return jsonify(df[["key", "text", "english", "checked"]].to_dict("records"))


@app.route("/api/toggle", methods=["POST"])
def api_toggle():
    d, df = request.json, load_dict(request.json["lang"])
    idx = df.index[df["key"] == d["key"]][0]
    old, new = df.at[idx, "checked"], bool(d["checked"])
    if old != new:
        record_history(d["lang"], d["key"], "checked", old, new)
        df.at[idx, "checked"] = new
    return jsonify(ok=True)


@app.route("/api/edit_text", methods=["POST"])
def api_edit_text():
    d, df = request.json, load_dict(request.json["lang"])
    idx = df.index[df["key"] == d["key"]][0]
    old, new = df.at[idx, "text"], d["text"]
    if str(old) != str(new):
        record_history(d["lang"], d["key"], "text", old, new)
        df.at[idx, "text"] = new
    return jsonify(ok=True)


@app.route("/api/undo", methods=["POST"])
def api_undo():
    lang = request.json["lang"]
    if not HISTORY.get(lang):
        return jsonify(ok=False)
    last = HISTORY[lang].pop()
    load_dict(lang).loc[lambda x: x["key"] == last["key"], last["col"]] = last["old"]
    return jsonify(ok=True)


@app.route("/api/stats")
def api_stats():
    df = load_dict(request.args.get("lang", "de")).copy()
    df["tag"] = df["tag"].fillna("").str.lower()
    groups = {"text": ["text"], "bible": ["bible"], "b9": ["b9"],
              "a6": ["a6-a", "a6-b"], "wiki": ["wiki"],
              "others": ["deprecated", "scripture", "span_bc", "span_bce", "span_ce"]}
    return jsonify({k: 0 if not len(s := df[df["tag"].isin(v)]) else
                    round(100 * s["checked"].astype(bool).sum() / len(s), 1)
                    for k, v in groups.items()})


@app.route("/api/changes")
def api_changes():
    lang = request.args.get("lang", "de")
    if lang not in DATA_CACHE:
        return jsonify([])
    m = DATA_CACHE[lang].merge(ORIGINAL_CACHE[lang], on="key", suffixes=("_new", "_old"))
    c = m[(m["checked_new"] != m["checked_old"]) | (m["text_new"] != m["text_old"])]
    return jsonify(c[["key", "checked_old", "checked_new", "text_old", "text_new"]].to_dict("records"))


@app.route("/api/export", methods=["POST"])
def api_export():
    save_dict(request.json["lang"])
    return jsonify(saved=True)


@app.route("/api/unsaved")
def api_unsaved():
    return jsonify(count=len(HISTORY.get(request.args.get("lang", "de"), [])))


HTML = """<!doctype html><title>Dictionary Editor</title>
<h2>Dictionary Editor <span id=unsaved>0</span></h2>
<select id=lang></select><span id=tags></span>
<button onclick=showChanges()>Check changes</button><button onclick=undo()>Undo</button>
<button onclick=exportFile()>Export dictionary</button><div id=changes></div>
<table border=1><thead><tr><th>Key</th><th>Text</th><th>English</th><th>Checked</th></tr></thead><tbody id=table></tbody></table>
<script>
let currentTag='text';const tags=[['Text','text'],['Bible','bible'],['B9','b9'],['A6','a6'],['wiki','wiki'],['Other','others']];
const lang=()=>document.getElementById('lang').value;
async function badge(){document.getElementById('unsaved').innerText=(await fetch('/api/unsaved?lang='+lang()).then(r=>r.json())).count}
async function buttons(){let s=await fetch('/api/stats?lang='+lang()).then(r=>r.json()),c=document.getElementById('tags');c.innerHTML='';tags.forEach(([label,value])=>{let b=document.createElement('button');b.innerText=label;b.className=value==currentTag?'active':'';b.onclick=()=>{currentTag=value;buttons();reload()};c.append(b,document.createTextNode(' '+(s[value]||0)+'% '))})}
async function reload(){let rows=await fetch(`/api/data?lang=${lang()}&tag=${currentTag}`).then(r=>r.json()),t=document.getElementById('table');t.innerHTML='';rows.forEach(r=>{let tr=document.createElement('tr');tr.innerHTML=`<td>${r.key}</td><td contenteditable>${r.text||''}</td><td>${r.english||''}</td><td><input type=checkbox ${r.checked?'checked':''}></td>`;tr.querySelector('input').onchange=e=>fetch('/api/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lang:lang(),key:r.key,checked:e.target.checked})}).then(()=>{buttons();badge()});tr.querySelector('[contenteditable]').onblur=e=>fetch('/api/edit_text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lang:lang(),key:r.key,text:e.target.innerText})}).then(badge);t.append(tr)})}
async function showChanges(){let d=await fetch('/api/changes?lang='+lang()).then(r=>r.json());document.getElementById('changes').innerText=d.length?JSON.stringify(d):'No changes'}
async function undo(){await fetch('/api/undo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lang:lang()})});reload();buttons();badge()}
async function exportFile(){await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lang:lang()})});badge();alert('Saved.')}
fetch('/api/languages').then(r=>r.json()).then(ls=>{let s=document.getElementById('lang');ls.forEach(l=>s.add(new Option(l.language_str,l.key)));s.value='de';s.onchange=()=>{buttons();reload();badge()};buttons();reload();badge()})
</script>"""


@app.route("/")
def index():
    return render_template_string(HTML)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
