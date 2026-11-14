# 평가용 체인 기동: 새 Hardhat 노드 -> deploy.js -> seed-eval.js -> evm_snapshot
#
#   powershell -ExecutionPolicy Bypass -File paper\eval\start_eval_chain.ps1
#
# run.bat 은 쓰지 않는다: run.bat 은 premium-scheduler/oracle/maturity-watcher 등 상태를
# 바꾸는 백그라운드 서비스까지 띄워서, 평가 도중 정답이 달라진다.
# 이 스크립트가 띄우는 것은 노드 하나뿐이다(챗봇은 query-*.js 로 노드를 직접 읽는다).
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # paper\eval -> repo root
$bc   = Join-Path $root 'blockchain-dental'

function Test-Port($port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

if (Test-Port 8545) {
    throw "포트 8545 가 이미 사용 중입니다. 기존 Hardhat 노드/run.bat 창을 먼저 종료하세요 (새 체인에서 시작해야 합니다)."
}

Write-Host "[1/4] Hardhat 노드 기동 ..."
$null = Start-Process -FilePath cmd.exe -ArgumentList '/c', 'npx hardhat node' `
        -WorkingDirectory $bc -WindowStyle Minimized -PassThru
for ($i = 0; $i -lt 90 -and -not (Test-Port 8545); $i++) { Start-Sleep -Seconds 1 }
if (-not (Test-Port 8545)) { throw "노드가 90초 안에 뜨지 않았습니다." }

Push-Location $bc
try {
    Write-Host "[2/4] deploy.js ..."
    npx hardhat run scripts/deploy.js --network localhost
    if ($LASTEXITCODE -ne 0) { throw "deploy.js 실패 (exit $LASTEXITCODE)" }

    Write-Host "[3/4] seed-eval.js ..."
    npx hardhat run scripts/seed-eval.js --network localhost
    if ($LASTEXITCODE -ne 0) { throw "seed-eval.js 실패 (exit $LASTEXITCODE)" }

    Write-Host "[4/4] evm_snapshot ..."
    $body = '{"jsonrpc":"2.0","method":"evm_snapshot","params":[],"id":1}'
    $r = Invoke-RestMethod -Uri 'http://127.0.0.1:8545' -Method Post -Body $body -ContentType 'application/json'
    Set-Content -Path (Join-Path $PSScriptRoot 'snapshot_id.txt') -Value $r.result
    Write-Host "snapshot id = $($r.result)  (paper\eval\snapshot_id.txt)"
}
finally { Pop-Location }

Write-Host "`n평가용 체인 준비 완료. 이어서: paper\eval\setup_before_worktree.ps1 (before 서버, 5001) 와 start.bat 대신 main 서버(5000)를 직접 기동."
