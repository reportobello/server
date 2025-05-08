from pathlib import Path

from reportobello import config
from reportobello.domain.user import User
from reportobello.infra.db import create_or_update_template_for_user, create_or_update_user, create_random_api_key, get_user_by_provider_id, is_valid_api_key


def create_admin_user_if_not_exists() -> None:
    admin_user = get_user_by_provider_id(provider="reportobello", provider_user_id="admin")

    is_initial_boot = admin_user is None

    if is_initial_boot:
        admin_user = User(
            id=-1,
            api_key=create_random_api_key(),
            provider="reportobello",
            provider_user_id="admin",
            username="admin",
            is_setting_up_account=False,
        )

        admin_user = create_or_update_user(admin_user)

    if config.ADMIN_API_KEY:
        assert is_valid_api_key(config.ADMIN_API_KEY), "Invalid API key format."

        admin_user.api_key = config.ADMIN_API_KEY

        create_or_update_user(admin_user)

    if is_initial_boot and not config.ADMIN_API_KEY:
        print(f'\n\x1b[31m"admin" API key: {admin_user.api_key}\n\x1b[0m')  # noqa: T201


def create_demo_user_if_not_exists() -> None:
    if not get_user_by_provider_id(provider="reportobello", provider_user_id="demo"):
        demo_user = User(
            id=-1,
            api_key="rpbl_DEMO_API_KEY_DEMO_API_KEY_DEMO_API_KEY_DEMO",
            provider="reportobello",
            provider_user_id="demo",
            username="demo",
            is_setting_up_account=False,
        )

        demo_user = create_or_update_user(demo_user)

        template = Path("reportobello/infra/seed/invoice.typ").read_text(encoding="utf8")

        create_or_update_template_for_user(demo_user.id, name="demo", content=template)
