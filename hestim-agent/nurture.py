"""Follow-ups for undecided prospects (replaces email nurturing).

WhatsApp only lets a business send free-form text within 24h of the contact's last message.
FOLLOWUP_AFTER_HOURS defaults to 20h so the single follow-up lands inside that window.
Later re-engagement must use an approved WhatsApp template (see README).
"""
import logging

import config
import db
from agent import core
from channels import meta

log = logging.getLogger("hestim.nurture")
MAX_FOLLOWUPS = 1


def run_followups() -> int:
    cutoff = db.now() - config.FOLLOWUP_AFTER_HOURS * 3600
    sent = 0
    for conv in db.followup_candidates(cutoff, MAX_FOLLOWUPS):
        if conv["channel"] == "whatsapp" and conv["last_inbound_at"] and db.now() - conv["last_inbound_at"] > 23.5 * 3600:
            continue  # outside the 24h window: needs a template message
        reply = core.run_turn(
            conv["id"], None,
            internal_note=(
                "Le prospect n'a pas répondu depuis plusieurs heures. Écris UNE relance courte et utile "
                "dans sa langue : rappelle ce qui l'intéressait, apporte une info nouvelle de la base ou "
                "propose une prochaine étape simple (appel avec un conseiller). Pas de pression. "
                "N'appelle aucun outil sauf si nécessaire."
            ),
        )
        if reply:
            meta.send(conv["channel"], conv["external_id"], reply)
            db.update_conversation(conv["id"], followups_sent=conv["followups_sent"] + 1)
            sent += 1
    log.info("follow-ups sent: %d", sent)
    return sent
