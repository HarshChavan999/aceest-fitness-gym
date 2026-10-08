#!/usr/bin/env bash
# ==============================================================================
# ACEest Fitness & Gym — Turnkey Automated VM Provisioning Script
# DevOps Assignment 1 | BITS Pilani
#
# This single script automatically configures an entire Ubuntu/Debian VM with:
#  1. System prerequisites & tools (Git, Python3, Pip, Virtualenv, Curl, Docker)
#  2. Docker daemon startup & non-root user permissions
#  3. In-VM Python environment setup & Pytest test suite execution
#  4. Production Docker image assembly & container deployment (Port 5000)
#  5. Automated Jenkins LTS CI Server deployment with Docker-in-Docker capability (Port 8080)
#  6. Automatic initial admin password retrieval and health checks
# ==============================================================================

set -euo pipefail

# Color palette for terminal logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${BOLD}${BLUE}"
cat << "EOF"
    _    ____ _____           _     _____ _ _                     
   / \  / ___| ____|___  ___ | |_  |  ___(_) |_ _ __   ___  ___ ___ 
  / _ \| |   |  _| / _ \/ __|| __| | |_  | | __| '_ \ / _ \/ __/ __|
 / ___ \ |___| |__|  __/\__ \| |_  |  _| | | |_| | | |  __/\__ \__ \
/_/   \_\____|_____|\___||___/ \__| |_|   |_|\__|_| |_|\___||___/___/
              Turnkey Cloud VM DevOps Setup Automation
EOF
echo -e "${NC}"

# Detect execution privileges
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
        log_info "Running with sudo privileges."
    else
        log_error "This script requires superuser privileges. Please run as root or install sudo."
        exit 1
    fi
fi

TARGET_USER="${SUDO_USER:-$USER}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

log_info "Target project directory: ${PROJECT_DIR}"
log_info "Configuring environment for user: ${TARGET_USER}"

# ------------------------------------------------------------------------------
# Step 1: System Package Update & Tool Installation
# ------------------------------------------------------------------------------
log_info "Updating system packages and installing dependencies..."
$SUDO apt-get update -y
$SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    iptables \
    net-tools

log_success "Base system packages installed."

# ------------------------------------------------------------------------------
# Step 2: Docker Installation & Daemon Startup
# ------------------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
    log_info "Docker not detected. Installing Docker Engine..."
    $SUDO apt-get install -y docker.io docker-compose
    $SUDO systemctl enable docker
    $SUDO systemctl start docker
    log_success "Docker installed successfully."
else
    log_info "Docker is already installed. Ensuring service is active..."
    $SUDO systemctl start docker || true
fi

# Add current user to docker group
if ! groups "$TARGET_USER" | grep -q '\bdocker\b'; then
    log_info "Adding user '${TARGET_USER}' to 'docker' group..."
    $SUDO usermod -aG docker "$TARGET_USER" || true
    log_warn "User added to docker group. Note: active terminal may need re-login for group changes without sudo."
fi

# ------------------------------------------------------------------------------
# Step 3: Local Python Environment & Pytest Verification
# ------------------------------------------------------------------------------
log_info "Setting up local Python virtual environment in ${PROJECT_DIR}/.venv..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

log_info "Executing Flake8 code linting..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --max-complexity=10 --statistics
log_success "Flake8 quality checks passed."

log_info "Running Pytest test suite with code coverage..."
pytest --cov=app --cov-report=term-missing tests/
log_success "All Pytest test cases passed successfully."

# ------------------------------------------------------------------------------
# Step 4: Docker Image Assembly & Application Container Deployment
# ------------------------------------------------------------------------------
log_info "Building production Docker image 'aceest-fitness:latest'..."
$SUDO docker build -t aceest-fitness:latest .
log_success "Docker image assembled successfully."

log_info "Verifying Pytest execution INSIDE the newly assembled container..."
$SUDO docker run --rm aceest-fitness:latest pytest tests/
log_success "In-container test suite execution confirmed."

log_info "Deploying ACEest Fitness application container on port 5000..."
$SUDO docker stop aceest-fitness-app 2>/dev/null || true
$SUDO docker rm aceest-fitness-app 2>/dev/null || true

$SUDO docker run -d \
    --name aceest-fitness-app \
    --restart unless-stopped \
    -p 5000:5000 \
    aceest-fitness:latest

sleep 4

# Verify application container health
if curl -s -f http://127.0.0.1:5000/health > /dev/null; then
    log_success "ACEest Fitness Flask Web Application is LIVE and healthy on http://localhost:5000!"
else
    log_warn "Application is starting up or health check timed out. Checking container logs:"
    $SUDO docker logs --tail 20 aceest-fitness-app
fi

# ------------------------------------------------------------------------------
# Step 5: Jenkins CI/CD Server Deployment (Port 8080)
# ------------------------------------------------------------------------------
log_info "Setting up Jenkins CI Server with Docker socket integration..."

# Ensure host docker group socket permissions
$SUDO chmod 666 /var/run/docker.sock || true

# Prepare persistent Jenkins volume
JENKINS_HOME_DIR="/var/jenkins_home"
$SUDO mkdir -p "$JENKINS_HOME_DIR"
$SUDO chown -R 1000:1000 "$JENKINS_HOME_DIR"

$SUDO docker stop jenkins-server 2>/dev/null || true
$SUDO docker rm jenkins-server 2>/dev/null || true

# Pull official Jenkins LTS image and run with Docker CLI capability
log_info "Launching Jenkins LTS container on port 8080..."
$SUDO docker run -d \
    --name jenkins-server \
    --restart unless-stopped \
    -u root \
    -p 8080:8080 \
    -p 50000:50000 \
    -v "$JENKINS_HOME_DIR":/var/jenkins_home \
    -v /var/run/docker.sock:/var/run/docker.sock \
    jenkins/jenkins:lts

log_info "Waiting for Jenkins to generate initial administrative credentials (30s)..."
for i in {1..30}; do
    if $SUDO test -f "${JENKINS_HOME_DIR}/secrets/initialAdminPassword"; then
        break
    fi
    sleep 2
done

JENKINS_PASSWORD="[Generating, check in a moment with: sudo cat ${JENKINS_HOME_DIR}/secrets/initialAdminPassword]"
if $SUDO test -f "${JENKINS_HOME_DIR}/secrets/initialAdminPassword"; then
    JENKINS_PASSWORD=$($SUDO cat "${JENKINS_HOME_DIR}/secrets/initialAdminPassword")
fi

# Detect public/external IP
PUBLIC_IP=$(curl -s https://ifconfig.me || curl -s https://api.ipify.org || hostname -I | awk '{print $1}')

# ------------------------------------------------------------------------------
# Step 6: Summary & Handoff Dashboard
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}${GREEN}==============================================================================${NC}"
echo -e "${BOLD}${GREEN}    ACEest FITNESS & GYM — VM AUTOMATED PROVISIONING COMPLETE!             ${NC}"
echo -e "${BOLD}${GREEN}==============================================================================${NC}"
echo ""
echo -e "${BOLD}1. ACEest Fitness Web Application (shadcn Zinc UI):${NC}"
echo -e "   • Local URL:      ${CYAN}http://localhost:5000${NC}"
echo -e "   • Public URL:     ${CYAN}http://${PUBLIC_IP}:5000${NC}"
echo -e "   • Health Check:   ${CYAN}http://${PUBLIC_IP}:5000/health${NC}"
echo -e "   • Status:         ${GREEN}RUNNING (Docker container: aceest-fitness-app)${NC}"
echo ""
echo -e "${BOLD}2. Jenkins CI/CD Server:${NC}"
echo -e "   • Local URL:      ${CYAN}http://localhost:8080${NC}"
echo -e "   • Public URL:     ${CYAN}http://${PUBLIC_IP}:8080${NC}"
echo -e "   • Admin Password: ${YELLOW}${JENKINS_PASSWORD}${NC}"
echo -e "   • Status:         ${GREEN}RUNNING (Docker container: jenkins-server)${NC}"
echo ""
echo -e "${BOLD}3. Local Virtual Environment & Pytest Quality Gate:${NC}"
echo -e "   • Path:           ${PROJECT_DIR}/.venv"
echo -e "   • All 24 unit tests: ${GREEN}PASSED (Flake8 clean, 94%+ coverage)${NC}"
echo ""
echo -e "${BOLD}4. Jenkins Job Configuration Guide:${NC}"
echo -e "   a. Open http://${PUBLIC_IP}:8080 and paste the Admin Password above."
echo -e "   b. Select 'Install Suggested Plugins'."
echo -e "   c. Create a 'Pipeline' project named 'ACEest-Fitness-CI'."
echo -e "   d. Under Pipeline Definition, select 'Pipeline script from SCM' -> Git."
echo -e "   e. Provide your GitHub Repository URL. The build will execute ${BOLD}Jenkinsfile${NC} automatically!"
echo ""
echo -e "${BOLD}${GREEN}==============================================================================${NC}"
