from __future__ import annotations

import os
import smtplib
import socket
import ssl
from email.message import EmailMessage

_TIMEOUT = 30
_REQUIRED_ENV = ("QAGENT_SMTP_HOST", "QAGENT_SMTP_USER", "QAGENT_SMTP_PASSWORD")
_NOT_CONFIGURED = (
    "Error: email not configured. "
    "Set QAGENT_SMTP_HOST/USER/PASSWORD env vars."
)


def is_configured() -> bool:
    return all(os.environ.get(var) for var in _REQUIRED_ENV)


def _split_addresses(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def send_email(to: str, subject: str, body: str, cc: str | None = None) -> str:
    if not is_configured():
        return _NOT_CONFIGURED

    host = os.environ["QAGENT_SMTP_HOST"]
    user = os.environ["QAGENT_SMTP_USER"]
    password = os.environ["QAGENT_SMTP_PASSWORD"]
    sender = os.environ.get("QAGENT_SMTP_FROM") or user
    tls_mode = os.environ.get("QAGENT_SMTP_TLS", "1")

    try:
        port = int(os.environ.get("QAGENT_SMTP_PORT", "587"))
    except ValueError:
        return "Error: QAGENT_SMTP_PORT must be an integer"

    to_list = _split_addresses(to)
    if not to_list:
        return "Error: 'to' must contain at least one address"
    cc_list = _split_addresses(cc) if cc else []

    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(to_list)
    if cc_list:
        message["Cc"] = ", ".join(cc_list)
    message["Subject"] = subject
    message.set_content(body)

    recipients = to_list + cc_list

    try:
        if tls_mode == "ssl":
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                host, port, timeout=_TIMEOUT, context=context
            ) as client:
                client.login(user, password)
                client.send_message(message, from_addr=sender, to_addrs=recipients)
        else:
            with smtplib.SMTP(host, port, timeout=_TIMEOUT) as client:
                client.ehlo()
                if tls_mode != "0":
                    context = ssl.create_default_context()
                    client.starttls(context=context)
                    client.ehlo()
                client.login(user, password)
                client.send_message(message, from_addr=sender, to_addrs=recipients)
    except (smtplib.SMTPException, ssl.SSLError, OSError, socket.error) as exc:
        return f"Error: {exc}"

    return f"Email sent to {to}"


SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": (
                "Send a plain-text email via the configured SMTP server."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": (
                            "Recipient address, or comma-separated addresses."
                        ),
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line.",
                    },
                    "body": {
                        "type": "string",
                        "description": "Plain-text message body.",
                    },
                    "cc": {
                        "type": "string",
                        "description": (
                            "Optional Cc address, or comma-separated addresses."
                        ),
                    },
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
]


def dispatch(name: str, args: dict) -> str | None:
    if name == "send_email":
        to = args.get("to")
        subject = args.get("subject")
        body = args.get("body")
        cc = args.get("cc")
        if not isinstance(to, str) or not isinstance(subject, str) or not isinstance(body, str):
            return "Error: send_email requires string to, subject, and body"
        if cc is not None and not isinstance(cc, str):
            return "Error: send_email cc must be a string when provided"
        return send_email(to, subject, body, cc)
    return None
