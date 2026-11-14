// 논문 평가용 고정 체인 시드 (deploy.js 실행 직후에 1회 실행).
//
//   npx hardhat run scripts/deploy.js   --network localhost
//   npx hardhat run scripts/seed-eval.js --network localhost
//
// 목적: 평가 쿼리가 실제로 오류를 "구별"할 수 있게 평가 지갑(Hardhat Account #1)의
// 상태를 고정한다. deploy.js는 수정하지 않는다(제품 시드와 평가 시드를 분리).
//
//  * 증권 4개(E1 배열 누락 검출용). 월 보험료·보장한도를 서로 다르게 해서, 채점기가
//    응답에 나온 금액으로 "어느 증권이 빠졌는지" 구별할 수 있게 한다.
//  * 첫 증권(policies[0])만 만기를 약 3시간 뒤로 둔다 — E2는 "오늘/내일" 구간의
//    사전계산 문자열을 검증하므로 당일 안 만기가 필요하다.
//  * 납입 이력·처리된 청구 4건, 금액 모두 다름(E4 시각 검증, E1 청구 나열용).
//  * 대체투자 포지션 2개, 파라메트릭 커버리지 2개(E1 나열 검증용).
//
// 참고: query-*.js는 "현재 시각"으로 최신 블록의 timestamp를 쓴다. 이 시드 이후
// 새 트랜잭션이 없으면 체인 시각이 멈춰 있어 카운트다운 문자열도 고정된다
// (평가 중 정답이 흔들리지 않음). 평가 중에는 premium-scheduler 등 상태를 바꾸는
// 서비스를 켜지 말 것.
const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

const H = 3600, D = 86400;
const usd = (n) => ethers.parseUnits(String(n), 6);

async function main() {
  const cfgPath = path.join(__dirname, "..", "frontend", "config.json");
  if (!fs.existsSync(cfgPath)) throw new Error("frontend/config.json 없음 — 먼저 deploy.js를 실행하세요.");
  const cfg = JSON.parse(fs.readFileSync(cfgPath, "utf8"));
  const c = cfg.contracts;

  const accounts = await ethers.getSigners();
  const owner = accounts[0];
  const cust = accounts[1];        // 평가 지갑 0x7099...79C8 (harness.py WALLET)
  const ins = await ethers.getContractAt("DentalInsurance", c.DentalInsurance);
  const usdc = await ethers.getContractAt("MockUSDC", c.MockUSDC);
  const alt = await ethers.getContractAt("AltInvestmentFund", c.AltInvestmentFund);
  const param = await ethers.getContractAt("ParametricInsurance", c.ParametricInsurance);

  const now = Number((await ethers.provider.getBlock("latest")).timestamp);

  // 평가 지갑에 충분한 USDC + 보험사 컨트랙트 자동이체 승인
  await (await usdc.connect(cust).faucet(usd(5000))).wait();
  await (await usdc.connect(cust).approve(c.DentalInsurance, ethers.MaxUint256)).wait();

  // ── 증권 #1 (deploy.js가 만든 김덴탈, $50/한도 $1000): 만기 3시간 뒤 ──
  const ids = (await ins.getPatientPolicies(cust.address)).map(Number);
  if (ids.length < 1) throw new Error("평가 지갑에 deploy.js 증권이 없습니다.");
  const first = ids[0];
  await (await ins.setMaturityDate(first, now + 3 * H)).wait();
  // 다음 납입일까지 3일 12시간 — 사전계산 문자열이 "3일 11시간 후"로 고정(반올림 모호성 방지)
  await (await ins.setPremiumInterval(first, 3 * D + 12 * H)).wait();
  await (await ins.connect(cust).payPremium(first)).wait();          // 납입 이력 1건
  await (await ins.connect(cust).submitClaim(first, usd(100), "D0120", "정기검진")).wait(); // 한도 20% 이하 → 자동 지급

  // ── 추가 증권 3개: 월 보험료·한도가 모두 서로 다름 (E1 구별용) ──
  const extra = [
    { premium: 120, limit: 3000, matureIn: 3 * D,  claim: 250 },   // 두 번째 증권에 청구 1건
    { premium: 90,  limit: 1500, matureIn: 7 * D,  claim: 60 },    // distinct amounts: E1 can tell which claim is missing
    { premium: 150, limit: 2500, matureIn: 14 * D, claim: 80 },
  ];
  for (const e of extra) {
    const tx = await ins.createPolicy(cust.address, "김덴탈", usd(e.premium), usd(e.limit),
                                      now + e.matureIn, 70, false);
    await tx.wait();
    const all = (await ins.getPatientPolicies(cust.address)).map(Number);
    const pid = all[all.length - 1];
    await (await ins.connect(cust).payPremium(pid)).wait();
    if (e.claim) {
      await (await ins.connect(cust).submitClaim(pid, usd(e.claim), "D2140", "아말감충전")).wait();
    }
  }

  // ── 대체투자: deploy.js가 fund 0(그린인프라) 포지션을 이미 만들어 둠 → fund 1 추가 ──
  await (await usdc.connect(cust).approve(c.AltInvestmentFund, ethers.MaxUint256)).wait();
  await (await alt.connect(cust).invest(1, usd(300))).wait();

  // ── 파라메트릭: deploy.js가 상품 0(항공편 지연) 커버리지를 이미 만들어 둠 → 상품 1 추가 ──
  await (await usdc.connect(cust).approve(c.ParametricInsurance, ethers.MaxUint256)).wait();
  await (await param.connect(cust).purchaseCoverage(1)).wait();

  // ── 요약 ──
  const finalIds = (await ins.getPatientPolicies(cust.address)).map(Number);
  const claimIds = (await ins.getPatientClaims(cust.address)).map(Number);
  const covIds = (await param.getHolderCoverages(cust.address)).map(Number);
  const block = await ethers.provider.getBlock("latest");
  console.log("=".repeat(60));
  console.log("  평가용 시드 완료");
  console.log("=".repeat(60));
  console.log(`  평가 지갑        : ${cust.address}`);
  console.log(`  증권             : ${finalIds.length}개 (ids=${finalIds.join(",")})`);
  for (const id of finalIds) {
    const p = await ins.getPolicy(id);
    console.log(`    #${id} 월 $${ethers.formatUnits(p.monthlyPremium, 6)} / 한도 $${ethers.formatUnits(p.coverageLimit, 6)}`
      + ` / 만기 +${((Number(p.maturityDate) - Number(block.timestamp)) / H).toFixed(1)}h / 납입 $${ethers.formatUnits(p.totalPaid, 6)}`);
  }
  console.log(`  청구             : ${claimIds.length}건`);
  console.log(`  파라메트릭 커버리지: ${covIds.length}개`);
  console.log(`  체인 시각(최신 블록): ${new Date(Number(block.timestamp) * 1000).toISOString()}`);
  if (finalIds.length < 3 || claimIds.length < 4 || covIds.length < 2) {
    throw new Error("시드가 기대한 개수에 못 미칩니다 — 위 요약을 확인하세요.");
  }
}

main().then(() => process.exit(0)).catch((e) => { console.error("시드 실패:", e); process.exit(1); });
