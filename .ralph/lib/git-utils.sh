#!/bin/bash
# git-utils.sh - Git commit and push helpers
# Source this file: source lib/git-utils.sh

MAIN_BRANCH="${MAIN_BRANCH:-main}"

# Commit changes
commit_changes() {
    local message="$1"

    [ -z "$(git status --porcelain 2>/dev/null)" ] && return 0

    git add -A
    git commit -m "$message" >/dev/null 2>&1 || true
}

# Push to remote
push_changes() {
    local branch="${1:-$MAIN_BRANCH}"

    git push origin "$branch" >/dev/null 2>&1 || true
}

# Commit and push
commit_and_push() {
    local message="$1"
    local branch="${2:-$MAIN_BRANCH}"

    commit_changes "$message"
    push_changes "$branch"
}

# Check for dangerous patterns in diff
check_dangerous() {
    local diff_content
    diff_content=$(git diff 2>/dev/null) || return 0

    local dangerous=(
        "rm -rf /"
        "rm -rf ~"
        "sudo rm -rf"
        "chmod -R 777 /"
    )

    for pattern in "${dangerous[@]}"; do
        if echo "$diff_content" | grep -qF "$pattern"; then
            echo "[DANGER] Found: $pattern"
            return 1
        fi
    done

    return 0
}

# Check for secrets in staged files
check_secrets() {
    local patterns=(
        "sk-ant-[a-zA-Z0-9]{20,}"
        "sk-[a-zA-Z0-9]{40,}"
        "ghp_[a-zA-Z0-9]{30,}"
    )

    for pattern in "${patterns[@]}"; do
        if git diff --cached 2>/dev/null | grep -qE "$pattern"; then
            echo "[DANGER] Secret pattern found: $pattern"
            return 1
        fi
    done

    return 0
}
