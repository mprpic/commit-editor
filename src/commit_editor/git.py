import subprocess


def get_user_name() -> str | None:
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        return None


def get_user_email() -> str | None:
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except subprocess.CalledProcessError:
        return None
    except FileNotFoundError:
        return None


def get_signed_off_by() -> str | None:
    name = get_user_name()
    email = get_user_email()

    if name and email:
        return f"Signed-off-by: {name} <{email}>"
    return None
