# 스크립트 위치 확인
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
# 프로젝트 루트 디렉토리 (스크립트 디렉토리의 상위)
$PROJECT_ROOT = (Get-Item $SCRIPT_DIR).Parent.FullName

# 프로젝트 루트 디렉토리로 이동
Set-Location $PROJECT_ROOT

Write-Host "Project directory: $PROJECT_ROOT"

# 현재 브랜치 확인
$CURRENT_BRANCH = git rev-parse --abbrev-ref HEAD
if ($CURRENT_BRANCH -ne "dev") {
    Write-Host "Error: Can only be executed from dev branch."
    Write-Host "Current branch: $CURRENT_BRANCH"
    exit 1
}

# 커밋되지 않은 변경사항 확인
if ($(git status --porcelain)) {
    Write-Host "Error: There are uncommitted changes. Please commit all changes first."
    exit 1
}

# main과 dev 브랜치 간의 차이 확인
git fetch origin main dev
$MAIN_HEAD = git rev-parse origin/main
$DEV_HEAD = git rev-parse origin/dev

if ($MAIN_HEAD -eq $DEV_HEAD) {
    Write-Host "Error: main branch and dev branch are identical."
    Write-Host "No new changes to release."
    exit 1
}

# 현재 버전 가져오기
$CURRENT_VERSION = $(try { 
    git describe --tags $(git rev-list --tags --max-count=1) 
} catch { 
    "v0.0.0" 
})

# 버전 증가 함수
function Increment-Version {
    param (
        [string]$version,
        [string]$increment_type
    )
    
    # v 접두사 제거
    $version = $version -replace '^v', ''
    
    # 버전을 점으로 분리
    $VERSION_PARTS = $version -split '\.'
    
    $major = if ($VERSION_PARTS.Length -gt 0) { [int]$VERSION_PARTS[0] } else { 0 }
    $minor = if ($VERSION_PARTS.Length -gt 1) { [int]$VERSION_PARTS[1] } else { 0 }
    $patch = if ($VERSION_PARTS.Length -gt 2) { [int]$VERSION_PARTS[2] } else { 0 }
    
    switch ($increment_type) {
        "major" {
            $major++
            $minor = 0
            $patch = 0
        }
        "minor" {
            $minor++
            $patch = 0
        }
        default {
            $patch++
        }
    }
    
    return "v$major.$minor.$patch"
}

# 버전 타입 확인 (기본값: patch)
$VERSION_TYPE = if ($args[0]) { $args[0] } else { "patch" }
if ($VERSION_TYPE -notmatch '^(major|minor|patch)$') {
    Write-Host "Error: Version type must be one of: major, minor, patch"
    exit 1
}

# 새 버전 생성
$NEW_VERSION = Increment-Version $CURRENT_VERSION $VERSION_TYPE

# Cargo.toml 버전 업데이트
Write-Host "`nUpdating Cargo.toml version..."
# 업데이트 전 버전 출력
Write-Host "Cargo.toml version before update:"
Select-String -Path "Cargo.toml" -Pattern "^version = "

# Cargo.toml 파일 업데이트
$content = Get-Content Cargo.toml
$content = $content -replace 'version = ".*"', "version = `"$($NEW_VERSION.Substring(1))`""
$content | Set-Content Cargo.toml -Encoding UTF8

# 업데이트 후 버전 출력
Write-Host "Cargo.toml version after update:"
Select-String -Path "Cargo.toml" -Pattern "^version = "

# 변경사항 요약
Write-Host "`nChanges summary:"
git --no-pager log --oneline origin/main..origin/dev

Write-Host "`nCurrent version: $CURRENT_VERSION"
Write-Host "New version: $NEW_VERSION"
Write-Host "`nStarting release process..."

# 사용자 확인
Write-Host "`nPlease enter 'y' or 'n':"
$REPLY = Read-Host "Do you want to continue? (y/N)"
if ($REPLY -notmatch '^[Yy]$') {
    Write-Host "Release cancelled."
    # Cargo.toml과 Cargo.lock 변경사항 되돌리기
    Write-Host "Reverting Cargo.toml and Cargo.lock changes..."
    git checkout -- Cargo.toml Cargo.lock
    Write-Host "Changes reverted successfully."
    exit 1
}

# Cargo.toml 변경사항 커밋
Write-Host "`nUpdating Cargo.toml and Cargo.lock"
cargo build
git add Cargo.toml Cargo.lock
git commit -m "chore: bump version to ${NEW_VERSION}"

# 릴리스 프로세스 실행
Write-Host "`n1. Switching to main branch"
git checkout main

Write-Host "`n2. Updating main branch"
git pull origin main

Write-Host "`n3. Merging dev branch"
git merge dev

Write-Host "`n4. Creating new tag"
git tag -a $NEW_VERSION -m "Release $NEW_VERSION"

Write-Host "`n5. Pushing changes"
git push origin main

Write-Host "`n6. Pushing tag"
git push origin $NEW_VERSION

Write-Host "`n7. Returning to dev branch"
git checkout dev

Write-Host "`n8. Syncing main changes to dev branch"
git merge main
git push origin dev

Write-Host "`n✨ Release completed! ($NEW_VERSION)"
Write-Host "GitHub Actions will automatically build binaries and create the release." 