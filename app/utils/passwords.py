"""Password policy: minimum length, no well-known passwords, nothing taken from the account's own details.

The list below holds only the most common passwords from public breach statistics. A production deployment
should also check new passwords against a breach corpus, for example the Have I Been Pwned range API
(k-anonymity: only the first 5 hex characters of the SHA-1 hash leave the server).
"""
from flask import current_app

COMMON_PASSWORDS = frozenset({
    '123456', '12345678', '123456789', '1234567890', '12345', '1234567', '111111', '000000', '123123', '654321',
    'password', 'password1', 'password123', 'passw0rd', 'qwerty', 'qwerty123', 'qwertyuiop', 'abc123', 'abcd1234',
    'iloveyou', 'admin', 'admin123', 'administrator', 'welcome', 'welcome1', 'letmein', 'letmein1', 'monkey',
    'dragon', 'football', 'baseball', 'sunshine', 'princess', 'master', 'superman', 'trustno1', '1q2w3e4r',
    '1qaz2wsx', 'zaq12wsx', 'asdfghjk', 'pakistan', 'pakistan123', 'changeme', 'default', 'secret', 'test1234',
})


def password_problem(password, *personal_values):
    """An error message if `password` is not acceptable, else None."""
    minimum = current_app.config['MIN_PASSWORD_LENGTH']
    if len(password) < minimum:
        return f'Password must be at least {minimum} characters.'
    lowered = password.lower()
    if lowered in COMMON_PASSWORDS:
        return 'This password is too common. Please choose another one.'
    for value in personal_values:
        value = (value or '').strip().lower()
        if len(value) >= 3 and (lowered == value or lowered == value.split('@')[0]):
            return 'Password must not be your name or email address.'
    return None
