import json
import re
from email.utils import parseaddr
from typing import Optional

from sqlalchemy.orm import Session

from models.crm import EmailClassificationRule, EmailMetadata

STOPWORDS = {
    "about",
    "after",
    "again",
    "from",
    "have",
    "hello",
    "into",
    "mail",
    "more",
    "please",
    "that",
    "this",
    "with",
    "your",
}


def sender_domain(sender_email: str = "") -> str:
    email = parseaddr(sender_email or "")[1] or sender_email or ""
    if "@" not in email:
        return ""
    return email.rsplit("@", 1)[-1].lower().strip()


def extract_keywords(*parts: str, limit: int = 8) -> list[str]:
    text = " ".join(part or "" for part in parts).lower()
    words = re.findall(r"[a-z][a-z0-9+-]{2,}", text)
    keywords = []
    for word in words:
        if word in STOPWORDS or word in keywords:
            continue
        keywords.append(word)
        if len(keywords) >= limit:
            break
    return keywords


def _loads_keywords(value: str) -> list[str]:
    try:
        data = json.loads(value or "[]")
        return [str(item).lower() for item in data if item]
    except Exception:
        return []


def learn_rule_from_email(db: Session, email: EmailMetadata, category: str) -> EmailClassificationRule:
    category = str(category or "").strip()[:80]
    domain = sender_domain(email.sender_email)
    keywords = extract_keywords(email.subject, email.snippet)

    rule = (
        db.query(EmailClassificationRule)
        .filter(
            EmailClassificationRule.user_id == email.user_id,
            EmailClassificationRule.category == category,
            EmailClassificationRule.sender_domain == domain,
        )
        .first()
    )
    if not rule:
        rule = EmailClassificationRule(
            user_id=email.user_id,
            category=category,
            sender_domain=domain,
            sender_email=(email.sender_email or "").lower(),
            keywords=json.dumps(keywords),
            match_count=1,
        )
        db.add(rule)
    else:
        existing = _loads_keywords(rule.keywords)
        merged = list(dict.fromkeys(existing + keywords))[:12]
        rule.keywords = json.dumps(merged)
        rule.sender_email = rule.sender_email or (email.sender_email or "").lower()
        rule.match_count = (rule.match_count or 0) + 1
    return rule


def apply_learned_rule(db: Session, email: EmailMetadata) -> Optional[str]:
    domain = sender_domain(email.sender_email)
    if not domain:
        return None

    text = f"{email.subject or ''} {email.snippet or ''}".lower()
    rules = (
        db.query(EmailClassificationRule)
        .filter(EmailClassificationRule.user_id == email.user_id, EmailClassificationRule.sender_domain == domain)
        .order_by(EmailClassificationRule.match_count.desc(), EmailClassificationRule.updated_at.desc().nullslast())
        .all()
    )
    for rule in rules:
        keywords = _loads_keywords(rule.keywords)
        if not keywords or any(keyword in text for keyword in keywords):
            rule.match_count = (rule.match_count or 0) + 1
            email.ai_status = rule.category
            return rule.category
    return None
