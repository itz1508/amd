"""
caption_styles.py

Track 2 (Video Captioning): the four required tones, applied to the SAME
context packet Agent B produced. This is where the four captions actually
diverge from each other — the facts (subject, action, setting, mood) stay
identical across all four; only the voice changes.

Design principle: keep tone instructions tight and example-anchored so
Agent A doesn't drift into inventing new facts while trying to "perform"
a tone — the context packet is still the only source of truth for WHAT
happened; these templates only control HOW it's said.
"""

from __future__ import annotations

STYLE_INSTRUCTIONS: dict[str, str] = {
    "formal": (
        "Write in a professional, objective, factual tone. Third person. "
        "No humor, no opinion, no embellishment. State only what the "
        "context confirms, plainly. Sentence structure should read like a "
        "neutral news caption or documentary narration."
    ),
    "sarcastic": (
        "Write in a dry, ironic, lightly mocking tone. Use understatement "
        "or deadpan delivery rather than exaggerated jokes. The irony "
        "should come from HOW the true facts are framed, not from "
        "inventing anything false or exaggerated about what's shown."
    ),
    "humorous_tech": (
        "Write with tech/programming humor — references to code, "
        "software, hardware, or internet culture, applied to what's "
        "actually shown in the video. The joke should map naturally onto "
        "the real subject/action; don't force an unrelated tech reference "
        "that has nothing to do with the scene."
    ),
    "humorous_non_tech": (
        "Write with everyday, general-audience humor — no technical or "
        "programming references. Playful, light, accessible. The humor "
        "should come from the real subject/action in the scene, not from "
        "unrelated jokes bolted on top."
    ),
}


def build_caption_prompt(context_packet: dict, style: str) -> str:
    """
    Builds the actual prompt for Agent A: the shared context packet
    (identical across all 4 styles) + one style-specific instruction.
    """
    if style not in STYLE_INSTRUCTIONS:
        raise ValueError(f"Unknown style: {style!r}. Expected one of {list(STYLE_INSTRUCTIONS)}")

    context_block = (
        f"Subject: {context_packet.get('main_subject', 'unknown')}\n"
        f"Action: {context_packet.get('action', 'unknown')}\n"
        f"Setting: {context_packet.get('setting', 'unknown')}\n"
        f"Important objects: {', '.join(context_packet.get('important_objects', []))}\n"
        f"Scene changes: {context_packet.get('scene_changes', 'none noted')}\n"
        f"Mood/tone of the footage: {context_packet.get('mood_tone', 'unspecified')}\n"
        f"Must mention: {', '.join(context_packet.get('must_mention_facts', []))}\n"
        f"Must NOT claim: {', '.join(context_packet.get('must_not_claim_facts', []))}\n"
    )

    return (
        f"{STYLE_INSTRUCTIONS[style]}\n\n"
        f"Context (this is the ONLY source of truth — do not add facts "
        f"not present here):\n{context_block}\n"
        f"Write one caption in the '{style}' style, grounded entirely in "
        f"the context above."
    )


def build_all_style_prompts(context_packet: dict, requested_styles: list[str]) -> dict[str, str]:
    """
    Convenience wrapper: builds prompts for every requested style from the
    same context packet, so Agent A generates all captions for a clip in
    one batched call (see below) instead of 4 separate ones.
    """
    return {style: build_caption_prompt(context_packet, style) for style in requested_styles}


def build_batched_caption_prompt(context_packet: dict, requested_styles: list[str]) -> str:
    """
    Combines all requested styles into ONE prompt, so Agent A produces all
    captions for a clip in a single call instead of one call per style.
    Same token-efficiency principle as Track 1: one call, shared context
    sent once, not once per style.
    """
    context_block = (
        f"Subject: {context_packet.get('main_subject', 'unknown')}\n"
        f"Action: {context_packet.get('action', 'unknown')}\n"
        f"Setting: {context_packet.get('setting', 'unknown')}\n"
        f"Important objects: {', '.join(context_packet.get('important_objects', []))}\n"
        f"Scene changes: {context_packet.get('scene_changes', 'none noted')}\n"
        f"Mood/tone of the footage: {context_packet.get('mood_tone', 'unspecified')}\n"
        f"Must mention: {', '.join(context_packet.get('must_mention_facts', []))}\n"
        f"Must NOT claim: {', '.join(context_packet.get('must_not_claim_facts', []))}\n"
    )

    style_blocks = "\n".join(
        f"- {style}: {STYLE_INSTRUCTIONS[style]}"
        for style in requested_styles
        if style in STYLE_INSTRUCTIONS
    )

    return (
        f"Context (this is the ONLY source of truth — do not add facts "
        f"not present here):\n{context_block}\n"
        f"Write ONE caption for each of the following styles, all "
        f"grounded in the SAME context above:\n{style_blocks}\n\n"
        f"Respond with ONLY valid JSON in this exact shape, no prose, no "
        f"markdown fences:\n"
        f'{{"formal": "...", "sarcastic": "...", "humorous_tech": "...", '
        f'"humorous_non_tech": "..."}}\n'
        f"Include only the requested styles: {requested_styles}"
    )


if __name__ == "__main__":
    example_context = {
        "main_subject": "an orange kitten",
        "action": "walking through green foliage, pausing to sniff a leaf",
        "setting": "a garden",
        "important_objects": ["leaves", "sunlight patches"],
        "scene_changes": "none — single continuous shot",
        "mood_tone": "calm, curious",
        "must_mention_facts": ["orange kitten", "garden setting"],
        "must_not_claim_facts": ["no other animals present", "no people visible"],
    }

    print("--- Single style prompt (formal) ---")
    print(build_caption_prompt(example_context, "formal"))
    print("\n--- Batched prompt (all 4 styles, one call) ---")
    print(build_batched_caption_prompt(
        example_context,
        ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"],
    ))
