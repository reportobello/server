from pathlib import Path
from reportobello.domain.user import User
from reportobello.infra.db import create_or_update_template_for_user, create_or_update_user, create_random_api_key, get_user_by_provider_id


def create_admin_user_if_not_exists() -> None:
    if not get_user_by_provider_id(provider="reportobello", provider_user_id="admin"):
        admin_user = User(
            id=-1,
            api_key=create_random_api_key(),
            provider="reportobello",
            provider_user_id="admin",
            username="admin",
            is_setting_up_account=False,
        )

        create_or_update_user(admin_user)

        print(f'\n\x1b[31m"admin" API key: {admin_user.api_key}\n\x1b[0m')


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

        template = Path("reportobello/infra/seed/invoice.typ").read_text()

        create_or_update_template_for_user(demo_user.id, name="demo", content=template)
