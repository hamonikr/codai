#!/bin/bash

# Define colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check actual script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Project root directory (parent of script directory)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Move to project root directory
cd "$PROJECT_ROOT"

echo -e "${YELLOW}Project directory: ${NC}$PROJECT_ROOT"

# Check current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "dev" ]; then
    echo -e "${RED}Error: Can only be executed from dev branch.${NC}"
    echo -e "${YELLOW}Current branch: ${NC}$CURRENT_BRANCH"
    exit 1
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}Error: There are uncommitted changes. Please commit all changes first.${NC}"
    exit 1
fi

# Check differences between main and dev branches
git fetch origin main dev
MAIN_HEAD=$(git rev-parse origin/main)
DEV_HEAD=$(git rev-parse origin/dev)

if [ "$MAIN_HEAD" == "$DEV_HEAD" ]; then
    echo -e "${RED}Error: main branch and dev branch are identical.${NC}"
    echo -e "${YELLOW}No new changes to release.${NC}"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(git describe --tags `git rev-list --tags --max-count=1` 2>/dev/null || echo "v0.0.0")

# Version increment function
increment_version() {
    local version=$1
    local increment_type=$2
    
    # Remove v prefix
    version=${version#v}
    
    # Split version by .
    IFS='.' read -ra VERSION_PARTS <<< "$version"
    
    major=${VERSION_PARTS[0]:-0}
    minor=${VERSION_PARTS[1]:-0}
    patch=${VERSION_PARTS[2]:-0}
    
    case $increment_type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch|*)
            patch=$((patch + 1))
            ;;
    esac
    
    echo "v$major.$minor.$patch"
}

# Check version type (default: patch)
VERSION_TYPE=${1:-patch}
if [[ ! "$VERSION_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo -e "${RED}Error: Version type must be one of: major, minor, patch${NC}"
    exit 1
fi

# Generate new version
NEW_VERSION=$(increment_version $CURRENT_VERSION $VERSION_TYPE)

# Update Cargo.toml version
echo -e "\n${YELLOW}Updating Cargo.toml version...${NC}"
# Print version before update
echo -e "${YELLOW}Cargo.toml version before update:${NC}"
grep "^version = " Cargo.toml

# Use appropriate sed command based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/^version = \".*\"/version = \"${NEW_VERSION#v}\"/" Cargo.toml
else
    # Linux and others
    sed -i "s/^version = \".*\"/version = \"${NEW_VERSION#v}\"/" Cargo.toml
fi

# Print version after update
echo -e "${YELLOW}Cargo.toml version after update:${NC}"
grep "^version = " Cargo.toml

# Show changes summary
echo -e "\n${YELLOW}Changes summary:${NC}"
git --no-pager log --oneline origin/main..origin/dev

echo -e "\n${YELLOW}Current version: ${NC}$CURRENT_VERSION"
echo -e "${YELLOW}New version: ${NC}$NEW_VERSION"
echo -e "\n${GREEN}Starting release process...${NC}"

# User confirmation
echo -e "\n${YELLOW}Please enter 'y' or 'n' (영문으로 입력해주세요):${NC}"
read -p "Do you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Release cancelled.${NC}"
    # Revert Cargo.toml and Cargo.lock changes
    echo -e "${YELLOW}Reverting Cargo.toml and Cargo.lock changes...${NC}"
    git checkout -- Cargo.toml Cargo.lock
    echo -e "${GREEN}Changes reverted successfully.${NC}"
    exit 1
fi

# Commit Cargo.toml changes
echo -e "\n${YELLOW}Updating Cargo.toml and Cargo.lock${NC}"
cargo build
git add Cargo.toml Cargo.lock
git commit -m "chore: bump version to ${NEW_VERSION}"

# Execute release process
echo -e "\n${YELLOW}1. Switching to main branch${NC}"
git checkout main

echo -e "\n${YELLOW}2. Updating main branch${NC}"
git pull origin main

echo -e "\n${YELLOW}3. Merging dev branch${NC}"
git merge dev

echo -e "\n${YELLOW}4. Creating new tag${NC}"
git tag -a $NEW_VERSION -m "Release $NEW_VERSION"

echo -e "\n${YELLOW}5. Pushing changes${NC}"
git push origin main

echo -e "\n${YELLOW}6. Pushing tag${NC}"
git push origin $NEW_VERSION

echo -e "\n${YELLOW}7. Returning to dev branch${NC}"
git checkout dev

echo -e "\n${YELLOW}8. Syncing main changes to dev branch${NC}"
git merge main
git push origin dev

echo -e "\n${GREEN}✨ Release completed! ($NEW_VERSION)${NC}"
echo -e "${YELLOW}GitHub Actions will automatically build binaries and create the release.${NC}"