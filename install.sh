#!/usr/bin/env bash
# dooservice agent — installer
# Usage: curl -fsSL https://raw.githubusercontent.com/ORG/REPO/main/install.sh | sudo bash
set -euo pipefail

# ══════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════
GITHUB_REPO="dooservice/dooservice-agent"
BINARY_NAME="dooservice-agent"
INSTALL_DIR="/usr/local/bin"
DATA_DIR="/var/lib/dooservice"
CONFIG_PATH="${DATA_DIR}/agent.toml"
SERVICE_USER="dooservice"
SERVICE_UID=1500

# ══════════════════════════════════════════════════════════════════════════════
# Output helpers
# ══════════════════════════════════════════════════════════════════════════════
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}${BOLD}→${RESET} $*"; }
success() { echo -e "${GREEN}${BOLD}✓${RESET} $*"; }
warn()    { echo -e "${YELLOW}${BOLD}!${RESET} $*"; }
error()   { echo -e "${RED}${BOLD}✗${RESET} $*" >&2; exit 1; }
section() { echo -e "\n${BOLD}── $* ──${RESET}"; }

ask() {
    local prompt="$1" var="$2" default="${3:-}"
    read -rp "$(echo -e "${CYAN}${prompt}${default:+ [${default}]}: ${RESET}")" value
    printf -v "$var" '%s' "${value:-$default}"
}

ask_secret() {
    local prompt="$1" var="$2"
    read -rsp "$(echo -e "${CYAN}${prompt}: ${RESET}")" value; echo
    printf -v "$var" '%s' "$value"
}

ask_optional() {
    local prompt="$1" var="$2"
    read -rp "$(echo -e "${YELLOW}${prompt} (Enter to skip): ${RESET}")" value
    printf -v "$var" '%s' "$value"
}

# ══════════════════════════════════════════════════════════════════════════════
# Header
# ══════════════════════════════════════════════════════════════════════════════
print_header() {
    echo -e "${BOLD}"
    echo "  ██████╗  ██████╗  ██████╗ ███████╗███████╗██████╗ ██╗   ██╗██╗ ██████╗███████╗"
    echo "  ██╔══██╗██╔═══██╗██╔═══██╗██╔════╝██╔════╝██╔══██╗██║   ██║██║██╔════╝██╔════╝"
    echo "  ██║  ██║██║   ██║██║   ██║███████╗█████╗  ██████╔╝██║   ██║██║██║     █████╗  "
    echo "  ██║  ██║██║   ██║██║   ██║╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██║██║     ██╔══╝  "
    echo "  ██████╔╝╚██████╔╝╚██████╔╝███████║███████╗██║  ██║ ╚████╔╝ ██║╚██████╗███████╗"
    echo "  ╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝"
    echo -e "${RESET}"
    echo -e "  ${BOLD}Agent Installer${RESET}\n"
}

# ══════════════════════════════════════════════════════════════════════════════
# Phase 1 — Preflight checks
# ══════════════════════════════════════════════════════════════════════════════
check_preflight() {
    section "Preflight"
    [[ $EUID -eq 0 ]]          || error "Run as root: sudo bash install.sh"
    command -v curl &>/dev/null || error "curl is required"
    grep -qi ubuntu /etc/os-release 2>/dev/null || error "Ubuntu is required"
    success "Preflight passed"
}

# ══════════════════════════════════════════════════════════════════════════════
# Phase 2 — Detect server specs
# ══════════════════════════════════════════════════════════════════════════════
detect_server_specs() {
    section "Detecting server specs"
    CPU_CORES=$(nproc)
    TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    TOTAL_RAM_GB=$(( TOTAL_RAM_KB / 1024 / 1024 ))
    info "CPU cores: ${CPU_CORES}  |  RAM: ${TOTAL_RAM_GB} GB"
}

# ══════════════════════════════════════════════════════════════════════════════
# Phase 3 — Install Docker
# ══════════════════════════════════════════════════════════════════════════════
install_docker() {
    section "Docker"

    if command -v docker &>/dev/null; then
        success "Docker already installed ($(docker --version | cut -d' ' -f3 | tr -d ','))"
        return
    fi

    info "Removing legacy Docker packages..."
    # shellcheck disable=SC2046
    apt remove -y $(dpkg --get-selections docker.io docker-compose docker-compose-v2 \
        docker-doc podman-docker containerd runc 2>/dev/null | cut -f1) 2>/dev/null || true

    info "Installing Docker prerequisites..."
    apt update -q
    apt install -y -q ca-certificates curl

    info "Adding Docker GPG key and repository..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

    info "Installing Docker Engine..."
    apt update -q
    apt install -y -q docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin

    systemctl enable --now docker
    success "Docker installed ($(docker --version | cut -d' ' -f3 | tr -d ','))"
}

# ══════════════════════════════════════════════════════════════════════════════
# Phase 4 — Install agent binary
# ══════════════════════════════════════════════════════════════════════════════
install_binary() {
    section "Downloading agent"
    local url="https://github.com/${GITHUB_REPO}/releases/latest/download/${BINARY_NAME}"
    info "Fetching from GitHub Releases..."
    curl -fsSL "${url}" -o "${INSTALL_DIR}/${BINARY_NAME}"
    chmod +x "${INSTALL_DIR}/${BINARY_NAME}"
    success "Installed to ${INSTALL_DIR}/${BINARY_NAME}"
}

# ══════════════════════════════════════════════════════════════════════════════
# Phase 5 — System user and data directory
# ══════════════════════════════════════════════════════════════════════════════
setup_system() {
    section "System setup"

    if ! id "${SERVICE_USER}" &>/dev/null; then
        useradd --uid "${SERVICE_UID}" --system --no-create-home \
            --shell /usr/sbin/nologin "${SERVICE_USER}"
        usermod -aG docker "${SERVICE_USER}"
        success "Created user '${SERVICE_USER}' (uid=${SERVICE_UID})"
    else
        success "User '${SERVICE_USER}' already exists"
    fi

    mkdir -p "${DATA_DIR}"
    chown "${SERVICE_USER}:${SERVICE_USER}" "${DATA_DIR}"
    success "Data directory: ${DATA_DIR}"
}

# ══════════════════════════════════════════════════════════════════════════════
# Phase 6 — Interactive configuration
# ══════════════════════════════════════════════════════════════════════════════
collect_nats_config() {
    section "NATS connection"
    ask        "NATS URL (e.g. nats://nats.example.com:4222)" NATS_URL
    ask        "NATS user"                                     NATS_USER "agent"
    ask_secret "NATS password"                                 NATS_PASSWORD
    ask        "Agent region (e.g. eu-west)"                   REGION
}

collect_proxy_config() {
    section "Proxy & TLS"
    ask "Base domain (e.g. clientes.example.com)" BASE_DOMAIN
    ask "Server public IP"                        SERVER_IP
    ask "ACME email for Let's Encrypt"            ACME_EMAIL

    echo -e "\n${CYAN}DNS provider for TLS:${RESET}"
    echo "  1) None — HTTP-01 (manual DNS)"
    echo "  2) cloudflare_token"
    echo "  3) cloudflare_global_key"
    echo "  4) route53"
    echo "  5) digitalocean"
    echo "  6) hetzner"
    echo "  7) linode"
    echo "  8) godaddy"
    echo "  9) namecheap"
    read -rp "$(echo -e "${CYAN}Choice [1]: ${RESET}")" DNS_CHOICE
    DNS_CHOICE="${DNS_CHOICE:-1}"
}

collect_dns_credentials() {
    DNS_PROVIDER=""
    CF_TOKEN=""; CF_EMAIL=""; CF_GLOBAL_KEY=""
    R53_KEY=""; R53_SECRET=""; R53_REGION=""; R53_ZONE=""
    DO_TOKEN=""; HZ_KEY=""; LN_TOKEN=""
    GD_KEY=""; GD_SECRET=""; NC_USER=""; NC_KEY=""

    case "$DNS_CHOICE" in
        2) DNS_PROVIDER="cloudflare_token"
           ask_secret "Cloudflare API token" CF_TOKEN ;;
        3) DNS_PROVIDER="cloudflare_global_key"
           ask        "Cloudflare email"      CF_EMAIL
           ask_secret "Cloudflare global key" CF_GLOBAL_KEY ;;
        4) DNS_PROVIDER="route53"
           ask        "Route53 access key ID"     R53_KEY
           ask_secret "Route53 secret access key" R53_SECRET
           ask        "Route53 region"            R53_REGION "us-east-1"
           ask_optional "Route53 hosted zone ID"  R53_ZONE ;;
        5) DNS_PROVIDER="digitalocean"
           ask_secret "DigitalOcean API token" DO_TOKEN ;;
        6) DNS_PROVIDER="hetzner"
           ask_secret "Hetzner API key" HZ_KEY ;;
        7) DNS_PROVIDER="linode"
           ask_secret "Linode token" LN_TOKEN ;;
        8) DNS_PROVIDER="godaddy"
           ask        "GoDaddy API key"    GD_KEY
           ask_secret "GoDaddy API secret" GD_SECRET ;;
        9) DNS_PROVIDER="namecheap"
           ask        "Namecheap API user" NC_USER
           ask_secret "Namecheap API key"  NC_KEY ;;
        *) DNS_PROVIDER="" ;;
    esac
}

collect_s3_config() {
    section "S3 backups (optional)"
    warn "Leave blank to keep backups on local disk."
    ask_optional "S3 endpoint (e.g. https://s3.amazonaws.com)" S3_ENDPOINT

    S3_KEY=""; S3_SECRET=""; S3_BUCKET="dooservice-backups"; S3_REGION="us-east-1"
    if [[ -n "$S3_ENDPOINT" ]]; then
        ask_secret "S3 access key"   S3_KEY
        ask_secret "S3 secret key"   S3_SECRET
        ask        "S3 bucket"       S3_BUCKET "dooservice-backups"
        ask        "S3 region"       S3_REGION "us-east-1"
    fi
}

# ══════════════════════════════════════════════════════════════════════════════
# Phase 7 — Calculate postgres & pgdog settings from server specs
# ══════════════════════════════════════════════════════════════════════════════
calculate_postgres_settings() {
    # shared_buffers = 25% of RAM
    PG_SHARED_BUFFERS="${TOTAL_RAM_GB}GB"
    # effective_cache_size = 75% of RAM
    PG_EFFECTIVE_CACHE_SIZE="$(( TOTAL_RAM_GB * 3 ))GB"
    # work_mem — conservative: keeps memory sane under many parallel queries
    if   (( TOTAL_RAM_GB < 8  )); then PG_WORK_MEM="4MB"
    elif (( TOTAL_RAM_GB < 16 )); then PG_WORK_MEM="8MB"
    elif (( TOTAL_RAM_GB < 32 )); then PG_WORK_MEM="16MB"
    elif (( TOTAL_RAM_GB < 64 )); then PG_WORK_MEM="24MB"
    else                               PG_WORK_MEM="32MB"
    fi
    # maintenance_work_mem — generous: speeds up VACUUM, index builds
    if   (( TOTAL_RAM_GB < 8  )); then PG_MAINTENANCE_WORK_MEM="64MB"
    elif (( TOTAL_RAM_GB < 16 )); then PG_MAINTENANCE_WORK_MEM="256MB"
    elif (( TOTAL_RAM_GB < 32 )); then PG_MAINTENANCE_WORK_MEM="512MB"
    elif (( TOTAL_RAM_GB < 64 )); then PG_MAINTENANCE_WORK_MEM="1GB"
    else                               PG_MAINTENANCE_WORK_MEM="2GB"
    fi
    # max_wal_size scales with RAM (more RAM = heavier writes expected)
    if   (( TOTAL_RAM_GB < 8  )); then PG_MAX_WAL_SIZE="1GB";  PG_MIN_WAL_SIZE="256MB"
    elif (( TOTAL_RAM_GB < 16 )); then PG_MAX_WAL_SIZE="2GB";  PG_MIN_WAL_SIZE="512MB"
    elif (( TOTAL_RAM_GB < 32 )); then PG_MAX_WAL_SIZE="4GB";  PG_MIN_WAL_SIZE="1GB"
    elif (( TOTAL_RAM_GB < 64 )); then PG_MAX_WAL_SIZE="8GB";  PG_MIN_WAL_SIZE="2GB"
    else                               PG_MAX_WAL_SIZE="16GB"; PG_MIN_WAL_SIZE="4GB"
    fi
    # autovacuum workers = half of CPU cores, capped at 8
    PG_AUTOVACUUM_WORKERS=$(( CPU_CORES / 2 ))
    (( PG_AUTOVACUUM_WORKERS > 8 )) && PG_AUTOVACUUM_WORKERS=8
    (( PG_AUTOVACUUM_WORKERS < 2 )) && PG_AUTOVACUUM_WORKERS=2

    info "Postgres: shared_buffers=${PG_SHARED_BUFFERS}, work_mem=${PG_WORK_MEM}, autovacuum_workers=${PG_AUTOVACUUM_WORKERS}"
}

calculate_pgdog_settings() {
    # PgDog workers = one per CPU core
    PGDOG_WORKERS="${CPU_CORES}"
    info "PgDog: workers=${PGDOG_WORKERS}"
}

# ══════════════════════════════════════════════════════════════════════════════
# Phase 8 — Write /var/lib/dooservice/agent.toml
# ══════════════════════════════════════════════════════════════════════════════
write_config() {
    section "Writing configuration"

    cat > "${CONFIG_PATH}" <<TOML
# dooservice agent — generated by installer on $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# Server: ${CPU_CORES} CPU cores, ${TOTAL_RAM_GB} GB RAM

nats_url      = "${NATS_URL}"
nats_user     = "${NATS_USER}"
nats_password = "${NATS_PASSWORD}"
region        = "${REGION}"
heartbeat_interval     = 30
max_concurrent_backups = 3

[sdk]
data_dir = "${DATA_DIR}"
debug    = false

[sdk.postgres]
superuser_password           = "${PG_PASSWORD}"
max_connections              = 200
shared_buffers               = "${PG_SHARED_BUFFERS}"
effective_cache_size         = "${PG_EFFECTIVE_CACHE_SIZE}"
work_mem                     = "${PG_WORK_MEM}"
maintenance_work_mem         = "${PG_MAINTENANCE_WORK_MEM}"
random_page_cost             = "1.1"
effective_io_concurrency     = 256
wal_compression              = "on"
checkpoint_completion_target = "0.9"
max_wal_size                 = "${PG_MAX_WAL_SIZE}"
min_wal_size                 = "${PG_MIN_WAL_SIZE}"
autovacuum_max_workers         = ${PG_AUTOVACUUM_WORKERS}
autovacuum_naptime             = "15s"
autovacuum_vacuum_scale_factor = "0.05"
tcp_keepalives_idle            = 60
tcp_keepalives_interval        = 10
tcp_keepalives_count           = 6
idle_in_transaction_session_timeout = "300s"
idle_session_timeout                = "0"
statement_timeout                   = "0"

[sdk.pgdog]
workers           = ${PGDOG_WORKERS}
pooler_mode       = "session"
default_pool_size = 12
min_pool_size     = 2
connect_timeout   = 5000
checkout_timeout  = 10000
idle_timeout      = 600000
server_lifetime   = 3600000

[sdk.proxy]
base_domain       = "${BASE_DOMAIN}"
server_ip         = "${SERVER_IP}"
acme_email        = "${ACME_EMAIL}"
dns_provider      = "${DNS_PROVIDER}"
acme_staging      = false
acme_use_wildcard = false
dashboard_enabled = false
dashboard_domain  = ""
TOML

    # [sdk.dns] — only the credentials for the chosen provider
    if [[ -n "$DNS_PROVIDER" ]]; then
        echo -e "\n[sdk.dns]" >> "${CONFIG_PATH}"
        case "$DNS_PROVIDER" in
            cloudflare_token)
                echo "cloudflare_api_token = \"${CF_TOKEN}\"" >> "${CONFIG_PATH}" ;;
            cloudflare_global_key)
                echo "cloudflare_email      = \"${CF_EMAIL}\""      >> "${CONFIG_PATH}"
                echo "cloudflare_global_key = \"${CF_GLOBAL_KEY}\"" >> "${CONFIG_PATH}" ;;
            route53)
                echo "route53_access_key_id     = \"${R53_KEY}\""    >> "${CONFIG_PATH}"
                echo "route53_secret_access_key = \"${R53_SECRET}\"" >> "${CONFIG_PATH}"
                echo "route53_region            = \"${R53_REGION}\"" >> "${CONFIG_PATH}"
                [[ -n "$R53_ZONE" ]] && echo "route53_hosted_zone_id = \"${R53_ZONE}\"" >> "${CONFIG_PATH}" ;;
            digitalocean)
                echo "digitalocean_api_token = \"${DO_TOKEN}\"" >> "${CONFIG_PATH}" ;;
            hetzner)
                echo "hetzner_api_key = \"${HZ_KEY}\"" >> "${CONFIG_PATH}" ;;
            linode)
                echo "linode_token = \"${LN_TOKEN}\"" >> "${CONFIG_PATH}" ;;
            godaddy)
                echo "godaddy_api_key    = \"${GD_KEY}\""    >> "${CONFIG_PATH}"
                echo "godaddy_api_secret = \"${GD_SECRET}\"" >> "${CONFIG_PATH}" ;;
            namecheap)
                echo "namecheap_api_user = \"${NC_USER}\"" >> "${CONFIG_PATH}"
                echo "namecheap_api_key  = \"${NC_KEY}\""  >> "${CONFIG_PATH}" ;;
        esac
    fi

    # [sdk.s3] — only if S3 was configured
    if [[ -n "$S3_ENDPOINT" ]]; then
        cat >> "${CONFIG_PATH}" <<TOML

[sdk.s3]
endpoint   = "${S3_ENDPOINT}"
access_key = "${S3_KEY}"
secret_key = "${S3_SECRET}"
bucket     = "${S3_BUCKET}"
region     = "${S3_REGION}"
TOML
    fi

    chown "${SERVICE_USER}:${SERVICE_USER}" "${CONFIG_PATH}"
    chmod 600 "${CONFIG_PATH}"
    success "Configuration written to ${CONFIG_PATH}"
}

# ══════════════════════════════════════════════════════════════════════════════
# Phase 9 — Install service and bootstrap infrastructure
# ══════════════════════════════════════════════════════════════════════════════
install_service() {
    section "Installing systemd service"
    "${INSTALL_DIR}/${BINARY_NAME}" agent install --config "${CONFIG_PATH}"
    systemctl enable dooservice-agent
    success "Service installed and enabled"
}

bootstrap_infrastructure() {
    section "Bootstrapping infrastructure"
    info "Configuring proxy..."
    "${INSTALL_DIR}/${BINARY_NAME}" bootstrap configure --config "${CONFIG_PATH}"
    info "Starting stack (Postgres → PgDog → Traefik)..."
    "${INSTALL_DIR}/${BINARY_NAME}" bootstrap start --config "${CONFIG_PATH}"
    success "Stack running"
}

start_agent() {
    section "Starting agent"
    systemctl start dooservice-agent
    sleep 2
    if systemctl is-active --quiet dooservice-agent; then
        success "Agent is running"
    else
        warn "Agent failed to start — check: journalctl -u dooservice-agent -n 50"
    fi
}

# ══════════════════════════════════════════════════════════════════════════════
# Phase 10 — Summary
# ══════════════════════════════════════════════════════════════════════════════
print_summary() {
    echo -e "\n${GREEN}${BOLD}Installation complete!${RESET}\n"
    echo -e "  Config:   ${CONFIG_PATH}"
    echo -e "  Data:     ${DATA_DIR}"
    echo -e "  Logs:     journalctl -u dooservice-agent -f"
    echo -e "  Status:   dooservice-agent agent status"
    echo -e "  CLI:      dooservice-agent --help\n"
}

# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
main() {
    print_header
    check_preflight
    detect_server_specs
    install_docker
    install_binary
    setup_system

    collect_nats_config
    collect_proxy_config
    collect_dns_credentials
    collect_s3_config

    section "PostgreSQL"
    PG_PASSWORD="$(openssl rand -hex 32)"
    info "Postgres superuser password auto-generated"
    calculate_postgres_settings
    calculate_pgdog_settings

    write_config
    install_service
    bootstrap_infrastructure
    start_agent
    print_summary
}

main
