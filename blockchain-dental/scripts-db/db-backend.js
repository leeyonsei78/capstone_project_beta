// "기존(중앙 DB) 백엔드" 조회 공용 모듈 — 논문 평가 전용.
//
// scripts/query-{policy,altinvest,parametric}.js 와 같은 형식의 JSON 을 내지만, 데이터는
// 블록체인이 아니라 변경 가능한 JSON 파일(DB 스냅샷)에서 읽는다. 챗봇 도구 계층과 LLM 호출은
// 그대로이고 데이터 원천만 다르다(통제 변수 1개).
//
// 스냅샷은 paper/eval/make_db_fixture.py 가 시드된 체인 상태를 덤프해 만든다.
//   DB_FIXTURE=<경로>  로 다른 파일(예: 변조된 스냅샷)을 가리킬 수 있다.
//
// ⚠️ 이 파일은 "원천이 변조 가능하다"는 기존 환경의 특성을 그대로 반영한다: 파일을 고치면
// 챗봇 답변도 그대로 바뀐다(검증 없음). 변조 시나리오 실험이 바로 이 성질을 이용한다.
const fs = require("fs");
const path = require("path");
const { ethers } = require("ethers");

const FIXTURE = process.env.DB_FIXTURE ||
  path.join(__dirname, "..", "..", "paper", "eval", "fixture_db.json");

function output(obj) { console.log(JSON.stringify(obj)); }

// kind: "policy" | "altinvest" | "parametric"
function run(kind) {
  const wallet = process.argv[2];
  if (!wallet || !ethers.isAddress(wallet)) {
    output({ ok: false, error: "유효한 지갑 주소가 아닙니다 (0x로 시작하는 42자 주소여야 합니다).", wallet: wallet || null });
    return;
  }
  if (!fs.existsSync(FIXTURE)) {
    output({ ok: false, error: `DB 스냅샷이 없습니다: ${FIXTURE}` });
    return;
  }
  let block;
  try {
    const db = JSON.parse(fs.readFileSync(FIXTURE, "utf8"));
    block = db[kind];
  } catch (e) {
    output({ ok: false, error: "DB 스냅샷을 읽지 못했습니다: " + e.message });
    return;
  }
  if (!block || block.ok === false) {
    output(block || { ok: false, error: `스냅샷에 '${kind}' 항목이 없습니다.` });
    return;
  }
  if (String(block.wallet).toLowerCase() === wallet.toLowerCase()) {
    output(block);
    return;
  }
  // 다른 지갑: 체인 스크립트가 데이터가 없는 지갑에 대해 내는 것과 같은 모양(빈 목록, 개수 0)
  const empty = { ...block, wallet };
  for (const k of Object.keys(empty)) {
    if (Array.isArray(empty[k])) empty[k] = [];
    else if (/Count$/.test(k) && typeof empty[k] === "number") empty[k] = 0;
  }
  output(empty);
}

module.exports = { run };
