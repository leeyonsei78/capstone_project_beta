"""
Build the self-contained HTML review sheet that several raters fill in (offline, one file, no server).

  python paper/eval/review/make_review_html.py          ->  cases/review_blind.html

Data comes ONLY from the blind CSVs (cases/review_claims_blind.csv, review_apps_blind.csv), which carry no planted
anomaly, no planted label and neutral shuffled ids -- so the HTML cannot leak the answer. blind_key.json and the
full case JSON files are never read here. Each rater opens the same file, enters an anonymous rater code, labels
cases (approve / investigate), optionally rates realism, leaves a memo; time per case is measured automatically.
Raters see the cases in an order shuffled per rater code (reduces order effects). A third tab lets a rater author
UNSTRUCTURED cases (disclosure breaches, exclusion clauses, prior treatment history for applications, ...) using the
same fields as cases/expert_cases_template.csv. Results are exported as JSON and merged by import_rater_results.py.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
CASES = HERE / "cases"
LABEL_COLS = {"전문가라벨(approve/investigate)", "전문가메모", "현실성(1-5)", "소요시간(초)"}


def read_sheet(path):
    raw = path.read_bytes()
    rows = list(csv.reader(raw.decode("utf-8-sig").splitlines()))
    head = rows[0]
    keep = [i for i, h in enumerate(head) if i > 0 and h not in LABEL_COLS]   # drop id + rater-entry columns
    cols = [head[i] for i in keep]
    out = [{"id": r[0], "cells": [r[i] for i in keep]} for r in rows[1:]]
    return raw, {"cols": cols, "rows": out}


def build(cases_dir=CASES):
    raw_c, claims = read_sheet(cases_dir / "review_claims_blind.csv")
    raw_a, apps = read_sheet(cases_dir / "review_apps_blind.csv")
    dataset_id = hashlib.sha256(raw_c + raw_a).hexdigest()[:12]
    data = {"dataset_id": dataset_id, "claims": claims, "apps": apps}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return TEMPLATE.replace("__DATA__", blob), dataset_id


def main():
    html, dataset_id = build()
    out = CASES / "review_blind.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html) // 1024} KB), dataset_id {dataset_id}")


TEMPLATE = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>보험 심사 라벨링 시트</title>
<style>
:root{--bg:#f5f6f8;--fg:#1c2330;--muted:#596579;--card:#fff;--line:#d8dde6;--accent:#2457c5;--okc:#1d7a46;--invc:#b4531a;--soft:#eef1f6}
@media (prefers-color-scheme:dark){:root{--bg:#12161d;--fg:#e6e9ef;--muted:#9aa5b8;--card:#1b212b;--line:#2d3644;--accent:#7aa2ff;--okc:#5ec98b;--invc:#f0a066;--soft:#232b37}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,"Malgun Gothic","Apple SD Gothic Neo",sans-serif}
header{padding:12px 20px;border-bottom:1px solid var(--line);background:var(--card);display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header h1{font-size:17px;margin:0}
header .sp{flex:1}
main{max-width:1180px;margin:0 auto;padding:16px 20px 60px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin-bottom:14px}
button{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--fg);padding:7px 14px;border-radius:8px;cursor:pointer}
button:hover{border-color:var(--accent)}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
button.sel-ok{background:var(--okc);border-color:var(--okc);color:#fff}
button.sel-inv{background:var(--invc);border-color:var(--invc);color:#fff}
input,select,textarea{font:inherit;color:var(--fg);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:7px 10px;width:100%}
textarea{min-height:70px;resize:vertical}
label{display:block;font-size:13px;color:var(--muted);margin:10px 0 4px}
.tabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
.tabs button.on{background:var(--accent);border-color:var(--accent);color:#fff}
.layout{display:grid;grid-template-columns:200px 1fr;gap:14px}
@media (max-width:820px){.layout{grid-template-columns:1fr}}
.list{display:flex;flex-wrap:wrap;gap:4px;align-content:flex-start;max-height:70vh;overflow:auto}
.list button{padding:3px 0;width:44px;font-size:12px}
.list button.done-ok{border-color:var(--okc);color:var(--okc)}
.list button.done-inv{border-color:var(--invc);color:var(--invc)}
.list button.cur{outline:2px solid var(--accent)}
table.f{border-collapse:collapse;width:100%}
table.f td{border-top:1px solid var(--line);padding:8px 10px;vertical-align:top}
table.f td:first-child{width:130px;color:var(--muted);white-space:nowrap}
.muted{color:var(--muted);font-size:13px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.timer{font-variant-numeric:tabular-nums;background:var(--soft);padding:4px 10px;border-radius:8px}
.warn{background:var(--soft);border-left:4px solid var(--invc);padding:10px 12px;border-radius:6px;font-size:13px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media (max-width:820px){.grid2{grid-template-columns:1fr}}
.hide{display:none}
.ac{border-top:1px solid var(--line);padding:8px 0;font-size:13px}
</style>
</head>
<body>
<header>
  <h1>보험 심사 라벨링 시트</h1>
  <span class="muted" id="hdrInfo"></span>
  <span class="sp"></span>
  <span id="hdrProg" class="muted"></span>
  <button id="btnExport" class="primary hide">결과 내보내기 (JSON)</button>
</header>
<main>

<section id="start" class="card">
  <h2 style="margin-top:0">시작하기</h2>
  <div class="warn">
    <b>이 시트는 블라인드입니다.</b> 사례가 어떻게 만들어졌는지(정답)는 들어 있지 않습니다. 사례에 적힌 정보만으로 실무 판단을 내려 주세요.
    판단하는 동안 다른 자료·AI 도구·다른 심사자와 상의하지 마세요(독립 판단이 필요합니다).
  </div>
  <div class="grid2">
    <div><label>심사자 코드 (실명 금지, 예: R01)</label><input id="raterId" maxlength="20" placeholder="R01"></div>
    <div><label>보험 심사 경력 (년)</label><input id="raterYears" type="number" min="0" max="60"></div>
    <div><label>주 담당 분야</label>
      <select id="raterField"><option value="">선택</option><option>보험금 심사(청구)</option><option>계약 심사(언더라이팅)</option><option>둘 다</option><option>기타</option></select></div>
  </div>
  <h3>판단 기준</h3>
  <ul>
    <li><b>approve (승인)</b>: 추가 조사 없이 그대로 처리해도 된다고 판단.</li>
    <li><b>investigate (조사)</b>: 지급·승인 전에 사람이 추가로 확인하거나 보완을 요청해야 한다고 판단.</li>
    <li>애매하면 실무에서 하시듯 판단하고, 이유를 메모에 짧게 적어 주세요. 사례가 비현실적이면 현실성 점수를 낮게 주세요.</li>
    <li><b>시간은 자동으로 측정됩니다.</b> 사례를 열면 시작되고, 다른 창으로 가거나 3분간 입력이 없으면 자동 일시정지됩니다. 자리를 비울 때는 일시정지를 눌러 주세요.</li>
    <li>중간에 브라우저를 닫아도 이 브라우저에 자동 저장됩니다. 그래도 <b>수시로 "결과 내보내기"로 파일을 저장</b>해 두세요.</li>
  </ul>
  <div class="row">
    <button id="btnStart" class="primary">시작</button>
    <label style="margin:0">이전에 내보낸 결과 이어서 하기:</label>
    <input id="fileLoad" type="file" accept=".json" style="width:auto">
  </div>
  <p id="startMsg" class="muted"></p>
</section>

<section id="work" class="hide">
  <div class="tabs" id="tabs">
    <button data-tab="claims">보험금 청구 (<span id="nClaims"></span>)</button>
    <button data-tab="apps">청약 (<span id="nApps"></span>)</button>
    <button data-tab="author">비정형 사례 작성</button>
  </div>

  <div id="reviewPane" class="layout">
    <div class="card"><div class="list" id="caseList"></div></div>
    <div>
      <div class="card">
        <div class="row" style="justify-content:space-between">
          <b id="caseTitle"></b>
          <span class="row"><span class="timer" id="timer">00:00</span><button id="btnPause">일시정지</button></span>
        </div>
        <div id="pausedMsg" class="warn hide" style="margin-top:8px"></div>
        <table class="f" id="caseTable"></table>
      </div>
      <div class="card">
        <div class="row">
          <button id="bOk">approve (승인)</button>
          <button id="bInv">investigate (조사)</button>
          <span class="muted" id="labelState"></span>
        </div>
        <div class="grid2">
          <div><label>현실성 (1~5, 선택)</label>
            <select id="realism"><option value="">-</option><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></div>
        </div>
        <label>메모 (판단 이유, 선택)</label>
        <textarea id="memo"></textarea>
        <div class="row" style="margin-top:12px">
          <button id="bPrev">이전</button><button id="bNext" class="primary">다음</button>
          <button id="bNextTodo">다음 미완료</button>
        </div>
      </div>
    </div>
  </div>

  <div id="authorPane" class="hide">
    <div class="card">
      <div class="warn">
        규칙(금액·건수)으로는 결정하기 어렵고 <b>사람이 읽고 판단해야 하는 사례</b>를 직접 써 주세요. 청약 사례에는 <b>기존 치료이력과 고지 답변</b>을 함께 쓰면 좋습니다.
        <b>실제 고객 정보(이름·주민번호·병원명·사내 건 번호)는 절대 넣지 마세요.</b> 실제 건을 바탕으로 했다면 사내 규정을 확인한 뒤 완전히 익명화·변형해서 쓰세요.
        작성한 정답은 다른 심사자에게 배포되는 이 파일에는 들어가지 않고, 본인 내보내기 파일에만 들어갑니다.
      </div>
      <form id="authForm"></form>
      <div class="row" style="margin-top:12px"><button id="btnAddAuth" class="primary" type="button">사례 추가</button><span class="muted" id="authMsg"></span></div>
    </div>
    <div class="card"><b>작성한 사례</b><div id="authList" class="muted">아직 없음</div></div>
  </div>
</section>
</main>

<script>
const DATA = __DATA__;
const LS_PREFIX = 'review_state_v1:';
const IDLE_MS = 180000;
const $ = id => document.getElementById(id);

let S = null;                 // state: {rater, rec:{id:{label,memo,realism,seconds,first_seconds,changes}}, authored:[]}
let tab = 'claims';
let order = {claims: [], apps: []};
let cur = null;               // current case id
let manualPause = false, idlePaused = false, lastInput = Date.now(), lastTick = performance.now();

/* ---------- storage ---------- */
function save() {
  if (!S) return;
  try { localStorage.setItem(LS_PREFIX + S.rater.id, JSON.stringify(S)); } catch (e) { /* storage may be blocked */ }
}
function loadSaved(id) {
  try { const t = localStorage.getItem(LS_PREFIX + id); return t ? JSON.parse(t) : null; } catch (e) { return null; }
}

/* ---------- per-rater shuffle ---------- */
function hash32(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
function rng(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function shuffled(ids, key) { const a = ids.slice(), r = rng(hash32(key)); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

/* ---------- helpers ---------- */
const sheetOf = t => DATA[t];
const rowById = {}; ['claims', 'apps'].forEach(t => DATA[t].rows.forEach(r => rowById[r.id] = {t, r}));
function rec(id) { return S.rec[id] || (S.rec[id] = {label: null, memo: '', realism: null, seconds: 0, first_seconds: null, changes: 0}); }
function fmt(sec) { sec = Math.floor(sec); const m = Math.floor(sec / 60), s = sec % 60; return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0'); }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c])); }
function counts() {
  const out = {};
  ['claims', 'apps'].forEach(t => { out[t] = sheetOf(t).rows.filter(r => S.rec[r.id] && S.rec[r.id].label).length; });
  return out;
}

/* ---------- timer ---------- */
['mousemove', 'keydown', 'click', 'scroll', 'touchstart'].forEach(ev => document.addEventListener(ev, () => {
  lastInput = Date.now();
  if (idlePaused) { idlePaused = false; showPaused(); }
}, true));
document.addEventListener('visibilitychange', () => { lastTick = performance.now(); });
setInterval(() => {
  const now = performance.now(), dt = (now - lastTick) / 1000; lastTick = now;
  if (!S || !cur || tab === 'author') return;
  if (!idlePaused && Date.now() - lastInput > IDLE_MS) { idlePaused = true; showPaused(); }
  if (document.hidden || manualPause || idlePaused) return;
  rec(cur).seconds += Math.min(dt, 2);          // cap one tick so a sleeping laptop cannot add hours
  $('timer').textContent = fmt(rec(cur).seconds);
}, 500);
function showPaused() {
  const m = $('pausedMsg');
  if (manualPause) { m.textContent = '일시정지 중입니다. 재개하려면 "재개"를 누르세요.'; m.classList.remove('hide'); }
  else if (idlePaused) { m.textContent = '3분간 입력이 없어 시간 측정이 자동으로 멈췄습니다. 아무 키나 누르면 재개됩니다.'; m.classList.remove('hide'); }
  else m.classList.add('hide');
  $('btnPause').textContent = manualPause ? '재개' : '일시정지';
}

/* ---------- review pane ---------- */
function buildList() {
  const box = $('caseList'); box.innerHTML = '';
  order[tab].forEach((id, i) => {
    const b = document.createElement('button'); b.textContent = i + 1; b.dataset.id = id;
    const r = S.rec[id];
    if (r && r.label === 'approve') b.classList.add('done-ok');
    if (r && r.label === 'investigate') b.classList.add('done-inv');
    if (id === cur) b.classList.add('cur');
    b.onclick = () => openCase(id);
    box.appendChild(b);
  });
}
function openCase(id) {
  cur = id; const {t, r} = rowById[id]; const sh = sheetOf(t);
  const idx = order[t].indexOf(id) + 1;
  $('caseTitle').textContent = (t === 'claims' ? '청구 사례 ' : '청약 사례 ') + idx + ' / ' + order[t].length;
  const tb = $('caseTable'); tb.innerHTML = '';
  sh.cols.forEach((c, i) => {
    let v = r.cells[i];
    const tr = document.createElement('tr');
    const td1 = document.createElement('td'); td1.textContent = c;
    const td2 = document.createElement('td');
    if ((c === '과거청구' || c === '과거청약') && v.includes(' / ')) td2.innerHTML = v.split(' / ').map(esc).join('<br>');
    else td2.textContent = v;
    tr.appendChild(td1); tr.appendChild(td2); tb.appendChild(tr);
  });
  const x = rec(id);
  $('memo').value = x.memo || ''; $('realism').value = x.realism || '';
  paintLabel(); $('timer').textContent = fmt(x.seconds);
  buildList(); lastTick = performance.now(); lastInput = Date.now(); idlePaused = false; showPaused();
  updateProg(); save();
}
function paintLabel() {
  const x = rec(cur);
  $('bOk').className = x.label === 'approve' ? 'sel-ok' : '';
  $('bInv').className = x.label === 'investigate' ? 'sel-inv' : '';
  $('labelState').textContent = x.label ? '선택됨: ' + x.label : '아직 선택하지 않음';
}
function setLabel(l) {
  const x = rec(cur);
  if (x.label && x.label !== l) x.changes += 1;
  if (!x.label) x.first_seconds = Math.round(x.seconds * 10) / 10;
  x.label = l; paintLabel(); buildList(); updateProg(); save();
}
function move(d) {
  const ids = order[tab], i = ids.indexOf(cur), j = Math.min(ids.length - 1, Math.max(0, i + d));
  openCase(ids[j]);
}
function nextTodo() {
  const ids = order[tab], i = ids.indexOf(cur);
  for (let k = 1; k <= ids.length; k++) { const id = ids[(i + k) % ids.length]; if (!(S.rec[id] && S.rec[id].label)) return openCase(id); }
  $('labelState').textContent = '이 탭은 모두 완료했습니다.';
}
function updateProg() {
  const c = counts();
  $('hdrProg').textContent = '완료: 청구 ' + c.claims + '/' + DATA.claims.rows.length + ' · 청약 ' + c.apps + '/' + DATA.apps.rows.length + ' · 작성 ' + S.authored.length + '건';
}

/* ---------- authoring pane ---------- */
const AUTH_FIELDS = [
  ['type', '유형', 'select', ['claim', 'app'], true],
  ['contract', '상품·담보 요약', 'textarea', null, true, '담보명, 보장한도, 가입 경과일, 면책/감액 기간 등 판단에 필요한 계약 사실'],
  ['facts', '이번 건 사실', 'textarea', null, true, '청구: 치료코드·명, 청구액 / 청약: 연령, 월보험료, 담보 수'],
  ['narrative', '서술(비정형)', 'textarea', null, true, '진단서 요지, 치료 경위, 고지사항 답변, 청구 사유 등 자유 서술 (3~8문장)'],
  ['clause', '관련 약관 발췌', 'textarea', null, false, '판단에 쓰이는 약관 조항을 짧게 (없으면 공란). 가상 약관 권장'],
  ['history', '과거 이력 (기존 치료이력 포함)', 'textarea', null, true, '날짜(며칠 전)·코드·금액·처리상태 / 청약이면 기존 치료이력과 고지 답변도 여기에. 없으면 "없음"'],
  ['label', '정답', 'select', ['approve', 'investigate'], true],
  ['action', '세부처리 (참고)', 'select', ['', '지급', '부분지급', '부지급', '보완요청', '계약인수', '조건부인수', '거절'], false],
  ['rationale', '판단근거', 'textarea', null, true, '정답을 낸 핵심 이유 한두 문장'],
  ['why_rules_fail', '규칙으로 못 잡는 이유', 'textarea', null, true, '예: 서술-코드 의미 불일치, 고지의무 해석, 면책 요건 해당 여부'],
  ['evidence_level', '필요한 근거 수준', 'select', ['summary', 'detail', 'narrative'], true, 'summary=이력 요약만으로 판단 가능 / detail=이력 상세 필요 / narrative=서술 해석 필요'],
  ['difficulty', '난이도 (1~5)', 'select', ['1', '2', '3', '4', '5'], true],
  ['realism', '현실성 (1~5)', 'select', ['1', '2', '3', '4', '5'], true],
  ['provenance', '출처', 'select', ['fictional', 'adapted'], true, 'fictional=완전 가상 / adapted=실제 건을 익명화·변형(사내 규정 확인함)'],
  ['seconds', '소요시간(초, 정답을 내리기까지)', 'number', null, false],
];
function buildAuthForm() {
  const f = $('authForm'); f.innerHTML = '';
  AUTH_FIELDS.forEach(([k, label, kind, opts, req, hint]) => {
    const wrap = document.createElement('div');
    const lb = document.createElement('label'); lb.textContent = label + (req ? ' *' : '') + (hint ? '  — ' + hint : ''); wrap.appendChild(lb);
    let inp;
    if (kind === 'textarea') inp = document.createElement('textarea');
    else if (kind === 'select') { inp = document.createElement('select'); (opts || []).forEach(o => { const op = document.createElement('option'); op.value = o; op.textContent = o || '-'; inp.appendChild(op); }); if (req) inp.insertAdjacentHTML('afterbegin', '<option value="">선택</option>'); inp.value = ''; }
    else { inp = document.createElement('input'); inp.type = kind; }
    inp.id = 'au_' + k; wrap.appendChild(inp); f.appendChild(wrap);
  });
}
function addAuthored() {
  const o = {}, miss = [];
  AUTH_FIELDS.forEach(([k, label, , , req]) => { const v = $('au_' + k).value.trim(); o[k] = v; if (req && !v) miss.push(label); });
  if (miss.length) { $('authMsg').textContent = '필수 항목을 채워 주세요: ' + miss.join(', '); return; }
  o.created_at = new Date().toISOString(); o.n = S.authored.length + 1;
  S.authored.push(o); save(); buildAuthForm(); renderAuthList(); updateProg();
  $('authMsg').textContent = '추가되었습니다. (총 ' + S.authored.length + '건) 내보내기 파일에 포함됩니다.';
}
function renderAuthList() {
  const box = $('authList');
  if (!S.authored.length) { box.textContent = '아직 없음'; return; }
  box.innerHTML = '';
  S.authored.forEach((a, i) => {
    const d = document.createElement('div'); d.className = 'ac';
    d.innerHTML = '<b>' + (i + 1) + '. [' + esc(a.type) + '] ' + esc(a.facts.slice(0, 60)) + '</b> — 정답 ' + esc(a.label) + ' / 난이도 ' + esc(a.difficulty) + ' ';
    const b = document.createElement('button'); b.textContent = '삭제'; b.onclick = () => { S.authored.splice(i, 1); save(); renderAuthList(); updateProg(); };
    d.appendChild(b); box.appendChild(d);
  });
}

/* ---------- tabs / start / export ---------- */
function setTab(t) {
  tab = t;
  document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('on', b.dataset.tab === t));
  $('reviewPane').classList.toggle('hide', t === 'author'); $('authorPane').classList.toggle('hide', t !== 'author');
  if (t === 'author') { cur = null; renderAuthList(); return; }
  const ids = order[t]; const first = ids.find(id => !(S.rec[id] && S.rec[id].label)) || ids[0];
  openCase(first);
}
function exportJSON() {
  const out = {
    format: 'review_rater_v1', dataset_id: DATA.dataset_id, exported_at: new Date().toISOString(),
    rater: S.rater, labels: {}, authored: S.authored
  };
  Object.keys(S.rec).forEach(id => { const x = S.rec[id]; if (x.label) out.labels[id] = {label: x.label, memo: x.memo || '', realism: x.realism ? Number(x.realism) : null, seconds: Math.round(x.seconds * 10) / 10, first_seconds: x.first_seconds, changes: x.changes}; });
  const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '');
  const blob = new Blob([JSON.stringify(out, null, 1)], {type: 'application/json'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'rater_' + S.rater.id + '_' + stamp + '.json';
  document.body.appendChild(a); a.click(); a.remove();
}
function begin(state) {
  S = state;
  order.claims = shuffled(DATA.claims.rows.map(r => r.id), S.rater.id + ':claims');
  order.apps = shuffled(DATA.apps.rows.map(r => r.id), S.rater.id + ':apps');
  $('start').classList.add('hide'); $('work').classList.remove('hide'); $('btnExport').classList.remove('hide');
  $('hdrInfo').textContent = '심사자 ' + S.rater.id + ' · 데이터 ' + DATA.dataset_id;
  $('nClaims').textContent = DATA.claims.rows.length; $('nApps').textContent = DATA.apps.rows.length;
  buildAuthForm(); updateProg(); setTab('claims');
}
$('btnStart').onclick = () => {
  const id = $('raterId').value.trim().replace(/[^A-Za-z0-9_-]/g, '');
  if (!id) { $('startMsg').textContent = '심사자 코드를 영문/숫자로 입력해 주세요.'; return; }
  const saved = loadSaved(id);
  if (saved && saved.dataset_id === DATA.dataset_id) { begin(saved); return; }
  begin({dataset_id: DATA.dataset_id, rater: {id: id, years: $('raterYears').value, field: $('raterField').value}, rec: {}, authored: []});
};
$('fileLoad').onchange = ev => {
  const f = ev.target.files[0]; if (!f) return;
  const rd = new FileReader();
  rd.onload = () => {
    try {
      const o = JSON.parse(rd.result);
      if (o.format !== 'review_rater_v1') throw new Error('형식이 다릅니다.');
      if (o.dataset_id !== DATA.dataset_id) throw new Error('다른 버전의 시트에서 만든 파일입니다(데이터 ID 불일치).');
      const st = {dataset_id: DATA.dataset_id, rater: o.rater, rec: {}, authored: o.authored || []};
      Object.keys(o.labels || {}).forEach(id => { const x = o.labels[id]; st.rec[id] = {label: x.label, memo: x.memo || '', realism: x.realism, seconds: x.seconds || 0, first_seconds: x.first_seconds, changes: x.changes || 0}; });
      begin(st);
    } catch (e) { $('startMsg').textContent = '불러오기 실패: ' + e.message; }
  };
  rd.readAsText(f, 'utf-8');
};
$('tabs').onclick = ev => { const t = ev.target.dataset && ev.target.dataset.tab; if (t) setTab(t); };
$('bOk').onclick = () => cur && setLabel('approve');
$('bInv').onclick = () => cur && setLabel('investigate');
$('bPrev').onclick = () => move(-1); $('bNext').onclick = () => move(1); $('bNextTodo').onclick = nextTodo;
$('btnPause').onclick = () => { manualPause = !manualPause; lastTick = performance.now(); showPaused(); };
$('memo').oninput = () => { if (cur) { rec(cur).memo = $('memo').value; save(); } };
$('realism').onchange = () => { if (cur) { rec(cur).realism = $('realism').value; save(); } };
$('btnExport').onclick = exportJSON;
$('btnAddAuth').onclick = addAuthored;
window.addEventListener('beforeunload', save);
</script>
</body>
</html>
'''

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
