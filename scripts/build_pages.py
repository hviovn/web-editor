import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

TIMELINE_URL = "https://github.com/kreier/timeline.git"
ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


def build_data(db):
    languages = pd.read_csv(db / "supported_languages.csv")
    languages = languages[languages["dict"] == True][["key", "language_str"]]
    result = languages.to_dict(orient="records")
    (SITE / "data").mkdir(parents=True, exist_ok=True)
    (SITE / "data" / "languages.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

    for lang in languages["key"]:
        path = db / f"dictionary_{lang}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if "checked" not in df.columns:
            df["checked"] = False
        # Keep only the columns needed by the browser and normalize NaN values.
        columns = [c for c in ["key", "text", "english", "tag", "checked"] if c in df]
        rows = df[columns].fillna("").to_dict(orient="records")
        (SITE / "data" / f"{lang}.json").write_text(
            json.dumps(rows, ensure_ascii=False), encoding="utf-8"
        )


def write_index():
    (SITE / "index.html").write_text(r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dictionary Editor</title>
<style>body{font:16px Arial;margin:20px}button,select{margin:3px;padding:6px 10px}table{border-collapse:collapse;width:100%;margin-top:12px}th,td{border:1px solid #ccc;padding:6px}th{background:#eee}.active{background:#4caf50;color:#fff}.badge{background:red;color:white;border-radius:12px;padding:2px 8px}</style>
<h2>Dictionary Editor <span id="unsaved" class="badge">0</span></h2>
<select id="lang"></select><span id="tags"></span>
<button id="changes">Check changes</button><button id="undo">Undo</button><button id="export">Export dictionary</button>
<div id="message"></div><table><thead><tr><th>Key</th><th>Text</th><th>English</th><th>Checked</th></tr></thead><tbody id="table"></tbody></table>
<script>
const groups={text:['text'],bible:['bible'],b9:['b9'],a6:['a6-a','a6-b'],wiki:['wiki'],others:['deprecated','scripture','span_bc','span_bce','span_ce']};
const labels={text:'Text',bible:'Bible',b9:'B9',a6:'A6',wiki:'Wiki',others:'Other'};let rows=[],original=[],tag='text',history=[];
const $=id=>document.getElementById(id), lang=()=>$('lang').value;
function save(){localStorage.setItem('dictionary-'+lang(),JSON.stringify(rows));localStorage.setItem('history-'+lang(),JSON.stringify(history));$('unsaved').textContent=history.length}
function load(){let saved=localStorage.getItem('dictionary-'+lang());rows=saved?JSON.parse(saved):JSON.parse(JSON.stringify(original));history=JSON.parse(localStorage.getItem('history-'+lang())||'[]');$('unsaved').textContent=history.length}
function filtered(){return rows.filter(r=>(groups[tag]||[tag]).includes(String(r.tag).toLowerCase()))}
function render(){let t=$('table');t.innerHTML='';filtered().forEach(r=>{let tr=document.createElement('tr');tr.innerHTML='<td>'+r.key+'</td><td contenteditable></td><td></td><td><input type="checkbox"></td>';tr.children[1].textContent=r.text||'';tr.children[2].textContent=r.english||'';tr.children[3].firstChild.checked=!!r.checked;tr.children[1].onblur=e=>edit(r.key,'text',e.target.textContent);tr.children[3].firstChild.onchange=e=>edit(r.key,'checked',e.target.checked);t.appendChild(tr)})}
function edit(key,col,value){let r=rows.find(x=>x.key===key),old=r[col];if(String(old)!==String(value)){history.push({key:key,col:col,old:old});r[col]=value;save();renderTags()}}
function renderTags(){let c=$('tags');c.innerHTML='';Object.keys(labels).forEach(k=>{let b=document.createElement('button');b.textContent=labels[k];b.className=k===tag?'active':'';b.onclick=()=>{tag=k;renderTags();render()};c.appendChild(b)})}
$('undo').onclick=()=>{let h=history.pop();if(h){rows.find(x=>x.key===h.key)[h.col]=h.old;save();render();renderTags()}};
$('changes').onclick=()=>{$('message').textContent=history.length?history.map(h=>h.key+': '+h.col).join(', '):'No changes'};
$('export').onclick=()=>{let blob=new Blob([JSON.stringify(rows,null,2)],{type:'application/json'});let a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='dictionary_'+lang()+'.json';a.click()};
fetch('data/languages.json').then(r=>r.json()).then(ls=>{ls.forEach(l=>$('lang').add(new Option(l.language_str,l.key)));$('lang').value='de';$('lang').onchange=init;init()});
function init(){fetch('data/'+lang()+'.json').then(r=>r.json()).then(d=>{original=d;load();renderTags();render()})}
</script></html>''', encoding="utf-8")


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    with tempfile.TemporaryDirectory() as temp:
        checkout = Path(temp) / "timeline"
        subprocess.run(["git", "clone", "--depth", "1", "--branch", "main", TIMELINE_URL, str(checkout)], check=True)
        build_data(checkout / "db")
    write_index()


if __name__ == "__main__":
    main()
