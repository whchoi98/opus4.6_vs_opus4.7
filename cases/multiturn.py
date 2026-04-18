"""Test 6: Multi-turn conversation — input token scaling with turn count.

Simulates chatbot conversations of 1, 3, 5, 10 turns. Each case sends the
entire prior history plus a new user message and measures input_tokens.

Synthesized assistant responses are kept short and consistent so the only
variable is turn count (not per-turn response verbosity).
"""
from cases.base import TestCase
import config


# Each (user, assistant) pair is roughly ~50 tokens of text combined.
# Topic: planning a weekend trip — natural, bounded, in English for tokenizer stability.
_TURNS = [
    ("I want to plan a weekend trip. Can you help?",
     "Of course! I'd be happy to help you plan a weekend trip. To give you tailored suggestions, could you tell me: 1) Where are you starting from? 2) What's your approximate budget? 3) Do you prefer nature, city, beach, or something else?"),
    ("I'm in Seoul, budget around $500, I prefer nature with some cultural stops.",
     "Great combination! Based on that, I'd suggest exploring either Sokcho (Seoraksan National Park + coastal culture) or Jeonju (Hanok Village + nearby mountains). Both are reachable within 3 hours from Seoul. Which sounds more appealing?"),
    ("Sokcho sounds perfect. What should I prioritize?",
     "For Sokcho, I'd prioritize: 1) Seoraksan National Park — start early, take Ulsanbawi trail (~4h round trip). 2) Seaside at Sokcho Beach in the afternoon. 3) Fresh seafood dinner at Jungang Market. For lodging, Seorak Waterpia or a nearby hanok stay balances comfort and budget."),
    ("How do I get there and back from Seoul?",
     "The easiest option is the intercity bus from Seoul Express Bus Terminal or East Seoul Bus Terminal — roughly 2.5 hours, $15 each way. You can also take KTX to Gangneung and transfer, but the direct bus is simpler. Book ahead for Friday evening and Sunday afternoon departures."),
    ("Any food or local tips I should know?",
     "A few must-tries: 1) Dakgalbi (spicy chicken stir-fry) — a regional specialty. 2) Hoedeopbap (raw fish bowl) at the market. 3) Squid soondae if you're adventurous. Tips: carry cash for small stalls, wear layers (mountain weather changes), and download Kakao Map for offline use — Google Maps has limited coverage."),
    ("Should I be worried about crowds?",
     "Yes, some planning helps. Seoraksan on weekends gets crowded at popular trailheads between 10am–2pm. Start your hike by 7–8am to beat the rush. The cable car to Gwongeumseong has the longest queues — skip it or go first thing. Sokcho Beach itself is usually fine on off-peak weekends."),
    ("What's the weather like in autumn?",
     "Autumn (late September to November) is arguably the best season — cool, dry, and the fall foliage in Seoraksan is famous. Temperatures range 10–20°C; pack a windbreaker and a warm layer for early mornings. Peak foliage is usually mid-to-late October."),
    ("Any hidden gems besides the main trails?",
     "Three lesser-known spots: 1) Biryong Falls — an easy 1-hour hike near the main Seorak entrance, much quieter. 2) Daepohang Harbor — sunset + fish auction experience. 3) Naksansa Temple — cliff-top temple with ocean views, 20 min from Sokcho. All free or low-cost."),
    ("I'll also bring my partner who doesn't hike much. Adjustments?",
     "Good call — here's an easier alternative: Skip Ulsanbawi; instead take the cable car up Gwongeumseong (10-min ride, amazing views) and stroll the short ridge. For the afternoon, do Naksansa Temple together and relax at the beach. Evening: seafood dinner, hanok stay. Keeps it gentle without missing the signature scenery."),
]


def _synth_turn(i: int) -> tuple[str, str]:
    """Generate a synthetic (user, assistant) pair for high-turn tests.

    Returns a reasonable-length chat exchange on a travel-planning theme
    so the content is natural but easy to generate at scale.
    """
    topics = [
        "food recommendations", "best photo spots", "weather concerns",
        "packing list", "transport options", "budget breakdown",
        "day-trip ideas", "safety tips", "local etiquette",
        "souvenir shops", "nightlife options", "rainy-day backup plans",
    ]
    topic = topics[i % len(topics)]
    user_q = (
        f"Can you elaborate on {topic} for this trip — specifically "
        f"anything I shouldn't miss given we've already discussed the main plan?"
    )
    asst_a = (
        f"Great question about {topic}. Three specific suggestions: (1) "
        f"prioritize the highest-rated option nearest to Sokcho's main area, "
        f"(2) budget roughly the equivalent of one nice meal ($20–30) for this, "
        f"and (3) time it for early afternoon to avoid the weekend crowds. "
        f"The short version: plan ahead, budget modestly, go off-peak."
    )
    return user_q, asst_a


def _build_messages_extended(n_turns: int, final_user_msg: str) -> list[dict]:
    """Construct a messages list with n_turns back-and-forth pairs, ending with
    a new user message. Uses the curated _TURNS list first, then falls through
    to _synth_turn(i) for any turns beyond the curated count.
    """
    msgs: list[dict] = []
    for i in range(n_turns):
        if i < len(_TURNS):
            user_text, asst_text = _TURNS[i]
        else:
            user_text, asst_text = _synth_turn(i)
        msgs.append({"role": "user", "content": user_text})
        msgs.append({"role": "assistant", "content": asst_text})
    msgs.append({"role": "user", "content": final_user_msg})
    return msgs


def _build_messages(n_turns: int, final_user_msg: str) -> list[dict]:
    """Construct a messages list with n_turns back-and-forth pairs, ending with
    a new user message to be responded to."""
    msgs: list[dict] = []
    for user_text, asst_text in _TURNS[:n_turns]:
        msgs.append({"role": "user", "content": user_text})
        msgs.append({"role": "assistant", "content": asst_text})
    msgs.append({"role": "user", "content": final_user_msg})
    return msgs


_FINAL_USER_MSG = "Given everything we've discussed, please write me a single-day itinerary for Saturday with times."


def cases() -> list[TestCase]:
    m47 = config.MODELS_3P["opus-4.7"]
    m46 = config.MODELS_3P["opus-4.6"]
    out: list[TestCase] = []
    for n in (1, 3, 5, 10):
        msgs = _build_messages(n, _FINAL_USER_MSG)
        for model, model_id in (("opus-4.7", m47), ("opus-4.6", m46)):
            out.append(TestCase(
                name=f"{model}-turns-{n}",
                test_id="test_6",
                backend="bedrock_runtime",
                model_id=model_id,
                prompt=_FINAL_USER_MSG,  # kept for reporting; actual messages override takes precedence
                prompt_label=f"turns-{n}",
                max_tokens=300,
                messages_override=msgs,
            ))
    return out
