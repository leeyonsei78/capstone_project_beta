# before-mitigation 서버를 별도 worktree 에서 포트 5001 로 기동한다.
# (main 서버는 5000, 같은 체인을 본다. 브랜치 전환·서버 재시작 없이 전후를 동시에 측정.)
#
#   powershell -ExecutionPolicy Bypass -File paper\eval\setup_before_worktree.ps1
#
# 선행: start_eval_chain.ps1 (frontend\config.json 이 만들어져 있어야 함)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$wt   = "$root`_before"                     # C:\test_capstone_project_beta_before
$branch = 'paper/before-mitigation'

if (-not (Test-Path (Join-Path $root 'blockchain-dental\frontend\config.json'))) {
    throw "frontend\config.json 없음 — 먼저 start_eval_chain.ps1 로 체인을 배포하세요."
}

if (-not (Test-Path $wt)) {
    Write-Host "worktree 생성: $wt ($branch)"
    git -C $root worktree add $wt $branch
    if ($LASTEXITCODE -ne 0) { throw "git worktree add 실패" }
} else { Write-Host "worktree 이미 존재: $wt" }

# gitignore 된 런타임 자산 복사 (worktree 에는 없음)
function Copy-IfExists($src, $dst) {
    if (Test-Path $src) { Copy-Item $src $dst -Recurse -Force; Write-Host "  복사: $src" }
    else { Write-Host "  (없음, 건너뜀) $src" }
}
Copy-IfExists (Join-Path $root 'insurance_agent\.env') (Join-Path $wt 'insurance_agent\.env')
Copy-IfExists (Join-Path $root 'insurance_agent\chroma_db') (Join-Path $wt 'insurance_agent\chroma_db')
Get-ChildItem $root -Filter *.xls* -ErrorAction SilentlyContinue | ForEach-Object { Copy-Item $_.FullName $wt -Force }
Copy-IfExists (Join-Path $root 'insurance_agent\data\insmarket_cache.json') (Join-Path $wt 'insurance_agent\data\insmarket_cache.json')
# 배포마다 재생성되므로 매번 덮어쓴다
Copy-Item (Join-Path $root 'blockchain-dental\frontend\config.json') (Join-Path $wt 'blockchain-dental\frontend\config.json') -Force
Write-Host "  복사: frontend\config.json"

# node_modules 는 용량이 커서 junction 으로 연결 (query-*.js 가 ethers 를 require)
$nmLink = Join-Path $wt 'blockchain-dental\node_modules'
if (-not (Test-Path $nmLink)) {
    New-Item -ItemType Junction -Path $nmLink -Target (Join-Path $root 'blockchain-dental\node_modules') | Out-Null
    Write-Host "  junction: node_modules"
}

# 포트 5000 하드코딩 -> 환경변수 PORT (worktree 쪽 web_app.py 에만 적용, main 은 건드리지 않음)
$wa = Join-Path $wt 'insurance_agent\web_app.py'
$text = Get-Content $wa -Raw -Encoding UTF8
$old = "app.run(host='0.0.0.0', port=5000, debug=False)"
$new = "app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5000')), debug=False)"
if ($text.Contains($old)) {
    [System.IO.File]::WriteAllText($wa, $text.Replace($old, $new), (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "  web_app.py: PORT 환경변수 패치 적용 (worktree 전용)"
} elseif ($text.Contains("os.environ.get('PORT'")) { Write-Host "  web_app.py: 이미 패치됨" }
else { throw "web_app.py 의 app.run 라인을 찾지 못했습니다 — 수동 확인 필요." }

# 서버 기동 (5001)
if (Get-NetTCPConnection -LocalPort 5001 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "포트 5001 이미 사용 중 — 서버 기동 생략"
} else {
    $env:PORT = '5001'
    $env:PYTHONIOENCODING = 'utf-8'
    $null = Start-Process -FilePath python -ArgumentList 'web_app.py' `
            -WorkingDirectory (Join-Path $wt 'insurance_agent') -WindowStyle Minimized
    Write-Host "before 서버 기동 중 (http://localhost:5001) ..."
}
Write-Host "`n확인: curl http://localhost:5001/ , 그리고 하네스는 --base-url http://localhost:5001 --phase before --all-queries"
