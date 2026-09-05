"""Unit tests validating production Docker Compose, Caddyfile, and environment configs."""

from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).parent.parent.parent


def test_docker_compose_prod_structure():
    compose_file = ROOT_DIR / "docker-compose.prod.yml"
    assert compose_file.exists(), "docker-compose.prod.yml must exist"

    with open(compose_file, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert "services" in config
    services = config["services"]

    # Verify all 5 core production services
    assert "postgres" in services
    assert "asterisk" in services
    assert "agent-api" in services
    assert "dashboard" in services
    assert "caddy" in services

    # Verify healthchecks on core backend services
    assert "healthcheck" in services["postgres"]
    assert "healthcheck" in services["agent-api"]

    # Verify volumes
    assert "volumes" in config
    assert "postgres_data" in config["volumes"]
    assert "asterisk_sounds" in config["volumes"]


def test_caddyfile_routing_rules():
    caddy_file = ROOT_DIR / "deploy" / "caddy" / "Caddyfile"
    assert caddy_file.exists(), "Caddyfile must exist"

    content = caddy_file.read_text(encoding="utf-8")
    assert "/api/*" in content
    assert "/ws/*" in content
    assert "agent-api:8000" in content
    assert "dashboard:3000" in content
    assert "X-Content-Type-Options" in content


def test_env_production_template_keys():
    env_example = ROOT_DIR / ".env.production.example"
    assert env_example.exists(), ".env.production.example must exist"

    content = env_example.read_text(encoding="utf-8")
    required_keys = [
        "DATABASE_URL",
        "LLM_PROVIDER",
        "STT_PROVIDER",
        "TTS_PROVIDER",
        "ASTERISK_ARI_URL",
        "SIP_TRUNK_HOST",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]
    for key in required_keys:
        assert key in content, f"Missing required config key {key} in .env.production.example"


def test_dockerfiles_exist():
    api_dockerfile = ROOT_DIR / "Dockerfile.api"
    dashboard_dockerfile = ROOT_DIR / "apps" / "dashboard" / "Dockerfile"
    asterisk_dockerfile = ROOT_DIR / "infrastructure" / "docker" / "Dockerfile.asterisk"

    assert api_dockerfile.exists()
    assert dashboard_dockerfile.exists()
    assert asterisk_dockerfile.exists()

    # Check non-root user in api dockerfile
    api_content = api_dockerfile.read_text(encoding="utf-8")
    assert "USER appuser" in api_content
    assert "HEALTHCHECK" in api_content

