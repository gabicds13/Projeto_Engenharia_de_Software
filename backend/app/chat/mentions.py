from __future__ import annotations

import re


def extract_mentions(
    text: str,
    author_id: str,
) -> set[str]:
    mentions = set(
        re.findall(
            r"(?<!\w)@([A-Za-z0-9_.:-]{2,100})",
            text,
        )
    )

    mentions.discard(author_id)

    return mentions