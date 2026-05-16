#!/bin/bash
# ============================================================
# EasyInvoiceMgr 一键更新脚本
# 用法: ./update.sh [--no-backup] [--force] [--timeout N]
# ============================================================
set -o pipefail

# ---- 配置 ----
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$PROJECT_DIR/update.log"
STATUS_FILE="$PROJECT_DIR/update_status.json"
LOCK_FILE="$PROJECT_DIR/.update.lock"
BACKUP_DIR="$PROJECT_DIR/backups"
HEALTH_MAX_RETRIES=30
HEALTH_INTERVAL=2
GIT_TIMEOUT=120
BUILD_TIMEOUT=600
DEFAULT_TIMEOUT=900
NO_BACKUP=false
FORCE=false

# ---- 参数解析 ----
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-backup) NO_BACKUP=true; shift ;;
        --force)    FORCE=true; shift ;;
        --timeout)  DEFAULT_TIMEOUT="$2"; shift 2 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# ---- 基础函数 ----
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

set_status() {
    local status="$1" message="$2" progress="$3"
    printf '{"status":"%s","message":"%s","progress":%d,"time":"%s"}\n' \
        "$status" "$message" "$progress" "$(date -Iseconds)" > "$STATUS_FILE"
}

fail() {
    local msg="$1"
    log "❌ 更新失败: $msg"
    set_status "failed" "$msg" "${2:-0}"
    unlock
    exit 1
}

cleanup() {
    log "⚠️ 收到中断信号，正在清理..."
    set_status "failed" "更新被中断" 0
    unlock
    exit 1
}
trap cleanup SIGINT SIGTERM

# ---- 锁机制 ----
lock() {
    if [ -f "$LOCK_FILE" ]; then
        local pid
        pid=$(cat "$LOCK_FILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            log "❌ 已有更新进程正在运行 (PID: $pid)"
            return 1
        fi
        log "⚠️ 发现残留锁文件，强制清除"
        rm -f "$LOCK_FILE"
    fi
    echo $$ > "$LOCK_FILE"
    return 0
}

unlock() {
    rm -f "$LOCK_FILE"
}

# ---- Docker Compose 检测 ----
detect_docker_compose() {
    if docker compose version &>/dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif docker-compose version &>/dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        fail "未找到 docker compose，请安装 Docker Compose v2" 0
    fi
    log "使用: $DOCKER_COMPOSE"
}

# ---- 预检查 ----
preflight() {
    log "========== 预检查 =========="

    if [ ! -f "$PROJECT_DIR/docker-compose.yml" ]; then
        fail "未找到 docker-compose.yml，请确认 PROJECT_DIR 正确: $PROJECT_DIR" 0
    fi

    if ! docker info &>/dev/null; then
        fail "Docker 未运行或无权限访问 Docker socket" 0
    fi

    detect_docker_compose

    # 检查 git 仓库状态
    cd "$PROJECT_DIR"
    if ! git rev-parse --git-dir &>/dev/null; then
        fail "当前目录不是 Git 仓库" 0
    fi

    # 检查是否有本地未提交的更改
    if [ "$FORCE" != true ]; then
        if ! git diff --quiet 2>/dev/null; then
            log "⚠️ 检测到本地未暂存的更改，使用 --force 强制更新"
            fail "本地有未提交的更改，请先提交或使用 --force" 5
        fi
        if ! git diff --cached --quiet 2>/dev/null; then
            log "⚠️ 检测到本地已暂存但未提交的更改"
            fail "本地有已暂存的更改，请先提交或使用 --force" 5
        fi
    fi

    # 记录当前版本（用于回滚）
    CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    log "当前 Git commit: ${CURRENT_COMMIT:0:8}"

    # 检查磁盘空间
    local available_mb
    available_mb=$(df -m "$PROJECT_DIR" 2>/dev/null | awk 'NR==2 {print $4}')
    if [ -n "$available_mb" ] && [ "$available_mb" -lt 500 ]; then
        log "⚠️ 磁盘可用空间不足 500MB (当前: ${available_mb}MB)，可能影响更新"
    fi

    log "预检查通过"
}

# ---- 数据库备份 ----
backup_database() {
    if [ "$NO_BACKUP" = true ]; then
        log "步骤 1/5: 跳过数据库备份 (--no-backup)"
        set_status "running" "跳过数据库备份" 10
        return 0
    fi

    log "步骤 1/5: 备份数据库..."
    set_status "running" "正在备份数据库..." 5

    mkdir -p "$BACKUP_DIR"

    local backup_file="$BACKUP_DIR/pre_update_$(date +%Y%m%d_%H%M%S).sql"
    local containers
    containers=$($DOCKER_COMPOSE -f "$PROJECT_DIR/docker-compose.yml" ps -q postgres 2>/dev/null)

    if [ -z "$containers" ]; then
        log "⚠️ postgres 容器未运行，尝试启动后备份..."
        $DOCKER_COMPOSE -f "$PROJECT_DIR/docker-compose.yml" up -d postgres 2>&1 | tee -a "$LOG_FILE"
        sleep 3
    fi

    if $DOCKER_COMPOSE -f "$PROJECT_DIR/docker-compose.yml" exec -T postgres \
        pg_dump -U postgres easy_invoice_mgr > "$backup_file" 2>>"$LOG_FILE"; then
        local size
        size=$(du -h "$backup_file" | cut -f1)
        log "✅ 数据库备份完成: $backup_file (大小: $size)"
        # 记录备份文件路径用于回滚
        echo "$backup_file" > "$PROJECT_DIR/.last_backup"
        # 清理 30 天前的备份
        find "$BACKUP_DIR" -name "pre_update_*.sql" -mtime +30 -delete 2>/dev/null
        set_status "running" "数据库备份完成" 15
    else
        log "⚠️ 数据库备份失败，将继续更新（已有 Docker volume 持久化）"
        set_status "running" "数据库备份失败，继续更新" 15
    fi
}

# ---- Git 拉取 ----
git_pull() {
    log "步骤 2/5: 拉取最新代码..."
    set_status "running" "正在拉取最新代码..." 20

    cd "$PROJECT_DIR"

    # 获取远程分支信息
    if ! git fetch origin --prune 2>>"$LOG_FILE"; then
        fail "无法连接到远程仓库，请检查网络" 20
    fi

    # 获取当前分支
    local branch
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

    # 尝试 rebase（保留本地更改）或直接 pull
    local pull_output
    if pull_output=$(git pull --ff-only origin "$branch" 2>&1); then
        log "✅ 代码拉取完成 (fast-forward)"
        echo "$pull_output" >> "$LOG_FILE"
    else
        # 检查是否是 merge conflict
        if echo "$pull_output" | grep -qi "conflict\|CONFLICT"; then
            fail "代码合并冲突，请手动解决后重试" 25
        fi

        # 非 fast-forward，尝试 rebase
        log "⚠️ 无法 fast-forward，尝试 rebase..."
        if git pull --rebase origin "$branch" 2>>"$LOG_FILE"; then
            log "✅ rebase 成功"
        else
            # rebase 失败，回滚
            log "❌ rebase 失败，执行 git rebase --abort"
            git rebase --abort 2>/dev/null || true
            fail "代码拉取失败: 无法合并。请手动 git pull 查看冲突" 25
        fi
    fi

    local new_commit
    new_commit=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    log "新 Git commit: ${new_commit:0:8}"

    set_status "running" "代码拉取完成" 40
}

# ---- 构建镜像 ----
build_images() {
    log "步骤 3/5: 构建 Docker 镜像..."
    set_status "running" "正在构建 Docker 镜像 (可能需要几分钟)..." 45

    cd "$PROJECT_DIR"

    local build_args=""
    if [ "$FORCE" = true ]; then
        build_args="--no-cache"
        log "使用 --no-cache 构建"
    fi

    if $DOCKER_COMPOSE -f "$PROJECT_DIR/docker-compose.yml" build $build_args 2>&1 | tee -a "$LOG_FILE"; then
        log "✅ 镜像构建完成"
    else
        log "❌ 镜像构建失败，正在回滚 git..."
        cd "$PROJECT_DIR"
        if [ "$CURRENT_COMMIT" != "unknown" ]; then
            git reset --hard "$CURRENT_COMMIT" 2>/dev/null || true
            log "已回滚到 commit: ${CURRENT_COMMIT:0:8}"
        fi
        fail "Docker 镜像构建失败" 50
    fi

    set_status "running" "镜像构建完成" 70
}

# ---- 重启服务 ----
restart_services() {
    log "步骤 4/5: 重启服务..."
    set_status "running" "正在重启服务..." 75

    cd "$PROJECT_DIR"

    # 重启前先将状态标记为 restarting 并释放锁。
    # 因为 docker compose up -d 会重启后端容器，导致本脚本进程被杀死，
    # 如果保持 running 状态，后续更新请求会被 409 阻塞。
    set_status "restarting" "服务正在重启，更新脚本即将退出..." 80
    unlock

    if $DOCKER_COMPOSE -f "$PROJECT_DIR/docker-compose.yml" up -d 2>&1 | tee -a "$LOG_FILE"; then
        log "✅ 服务已重启（脚本进程可能在此处被终止）"
    else
        # 重启失败时尝试重新加锁并报告失败
        lock 2>/dev/null || true
        fail "Docker 服务启动失败" 80
    fi

    # 如果脚本进程幸存（未使用 docker compose 或容器未被重启），继续健康检查
    lock 2>/dev/null || true
    set_status "running" "服务已重启，等待健康检查..." 85
}

# ---- 健康检查 ----
health_check() {
    log "步骤 5/5: 健康检查..."
    set_status "running" "正在健康检查..." 88

    local retries=0
    local all_healthy=false

    while [ $retries -lt $HEALTH_MAX_RETRIES ]; do
        local unhealthy=""
        local containers
        containers=$($DOCKER_COMPOSE -f "$PROJECT_DIR/docker-compose.yml" ps --format json 2>/dev/null)

        # 检查所有服务是否都在运行
        local backend_running=false
        local frontend_running=false
        local postgres_running=false

        if $DOCKER_COMPOSE -f "$PROJECT_DIR/docker-compose.yml" ps | grep -q "backend.*Up"; then
            backend_running=true
        fi
        if $DOCKER_COMPOSE -f "$PROJECT_DIR/docker-compose.yml" ps | grep -q "frontend.*Up"; then
            frontend_running=true
        fi
        if $DOCKER_COMPOSE -f "$PROJECT_DIR/docker-compose.yml" ps | grep -q "postgres.*Up\|healthy"; then
            postgres_running=true
        fi

        if $backend_running && $frontend_running && $postgres_running; then
            all_healthy=true
            break
        fi

        [ -z "$backend_running" ] || [ "$backend_running" = false ] && unhealthy="$unhealthy backend"
        [ -z "$frontend_running" ] || [ "$frontend_running" = false ] && unhealthy="$unhealthy frontend"
        [ -z "$postgres_running" ] || [ "$postgres_running" = false ] && unhealthy="$unhealthy postgres"

        retries=$((retries + 1))
        log "等待服务就绪... ($retries/$HEALTH_MAX_RETRIES) 未就绪:$unhealthy"
        sleep $HEALTH_INTERVAL
    done

    if [ "$all_healthy" = true ]; then
        log "✅ 所有服务健康"
        set_status "completed" "更新完成，所有服务正常运行" 100
    else
        log "⚠️ 部分服务未能在 ${HEALTH_MAX_RETRIES} 次重试内就绪"
        log "请手动检查: $DOCKER_COMPOSE ps"
        set_status "completed" "更新完成，部分服务可能需要手动检查" 95
    fi
}

# ---- 清理 ----
post_cleanup() {
    log "清理旧的 Docker 镜像..."
    docker image prune -f 2>&1 | tee -a "$LOG_FILE" || true

    # 清理旧的构建缓存
    docker builder prune -f --filter "until=72h" 2>&1 | tee -a "$LOG_FILE" || true

    log "========== 更新流程结束 =========="
    log "当前 Git commit: $(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
}

# ---- 主流程 ----
main() {
    log "========== 开始系统更新 $(date) =========="

    lock || exit 1
    set_status "running" "开始更新..." 2

    preflight
    backup_database
    git_pull
    build_images
    restart_services
    health_check
    post_cleanup

    unlock
    log "✅ 更新成功完成"
}

main "$@"
