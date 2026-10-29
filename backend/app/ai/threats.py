from __future__ import annotations

import re
from dataclasses import dataclass

RULES_VERSION = "local-rules-v2"
RULES_SOURCE = "rules-v2"


@dataclass(frozen=True)
class ThreatCandidate:
    threat_class: str
    severity: str
    snippet: str
    confidence: float
    reason: str
    context_cautions: tuple[str, ...] = ()


CONTEXT_CUES = {
    "en": {
        "possible_negation_or_denial": re.compile(
            r"\b(?:not|never|no one|nobody|did not|didn't|was not|wasn't|is not|isn't|do not|don't|cannot|can't)\b", re.I
        ),
        "possible_quote_or_reported_speech": re.compile(
            r"\b(?:reported|told me|said|message says|screenshot says|quote|quoted|according to)\b", re.I
        ),
        "possible_educational_or_hypothetical_context": re.compile(
            r"\b(?:awareness|training|educational|hypothetical|fictional|for example|in a film|in the movie|news report)\b", re.I
        ),
    },
    "hi": {
        "possible_negation_or_denial": re.compile(r"(?:नहीं|नही|मत|कभी नहीं)"),
        "possible_quote_or_reported_speech": re.compile(r"(?:रिपोर्ट|बताया|कहा|उद्धरण)"),
        "possible_educational_or_hypothetical_context": re.compile(r"(?:जागरूकता|शिक्षा|उदाहरण|काल्पनिक|फिल्म)"),
    },
    "kn": {
        "possible_negation_or_denial": re.compile(r"(?:ಬೇಡ|ಇಲ್ಲ|ಮಾಡಬೇಡಿ|ಮಾಡಲಿಲ್ಲ)"),
        "possible_quote_or_reported_speech": re.compile(r"(?:ವರದಿ|ಹೇಳಿದ|ಉದಾಹರಣೆ|ಉಲ್ಲೇಖ)"),
        "possible_educational_or_hypothetical_context": re.compile(r"(?:ಜಾಗೃತಿ|ಶಿಕ್ಷಣ|ಕಾಲ್ಪನಿಕ|ಚಿತ್ರ)"),
    },
}


def context_cautions(text: str, language: str) -> tuple[str, ...]:
    """Return review cues without suppressing a threat candidate or deciding intent."""
    patterns = CONTEXT_CUES.get(language, CONTEXT_CUES["en"])
    return tuple(name for name, pattern in patterns.items() if pattern.search(text))


# Conservative exact phrases and bounded context patterns for local triage.
# These are review cues, not a classifier of intent, guilt, authenticity, or crime.
CATEGORY_TERMS = {
    "en": {
        "critical": {
            "other": ("kill you", "shoot you", "i will kill", "bomb your"),
        },
        "high": {
            "cyberstalking_bullying": (
                "i know where you live", "i will find you", "tracking your location",
                "i am following you", "wait outside your home", "wait outside your office",
                "follow you after work",
            ),
            "blackmail_threatening": (
                "pay or else", "send money or", "send me money or", "pay me or",
                "unless you pay", "threaten you", "threaten to expose", "blackmail you unless", "i will blackmail you",
            ),
            "intimate_image_abuse": (
                "share your photos", "share your private photos", "share your private images",
                "leak your photos", "publish your intimate pictures", "post your private pictures",
                "upload your private photos", "share your intimate images",
            ),
            "fake_profile_impersonation": (
                "fake account in your name", "fake account using your name", "pretending to be you",
                "using your identity to message", "used your identity to message", "impersonating you online",
            ),
            "defamation_morphing": (
                "morphed your photo", "altered your photo", "fake image of you",
                "false accusation about you", "edited your picture to show", "edited your picture falsely accuses",
            ),
            "other": (),
        },
        "medium": {
            "other": ("send me your otp", "steal your password"),
        },
    },
    "hi": {
        "critical": {
            "other": ("मार दूंगा", "जान से मार", "गोली मार", "बम से"),
        },
        "high": {
            "cyberstalking_bullying": ("तुम्हारा पीछा करता रहूँगा", "तुम्हारा पीछा करता रहूंगा", "तुम्हें ढूँढ लूँगा", "तुम्हें ढूंढ लूंगा", "तुम्हारी लोकेशन ट्रैक", "ऑफिस के बाहर इंतज़ार"),
            "blackmail_threatening": ("पैसे नहीं दिए", "पैसे दो वरना", "मुझे पैसे दो नहीं तो", "ब्लैकमेल करूँगा", "ब्लैकमेल करूंगा", "धमकी देकर पैसे"),
            "intimate_image_abuse": ("तस्वीरें वायरल", "तस्वीरें फैलाऊंगा", "निजी तस्वीरें साझा", "निजी तस्वीरें भेज दूंगा", "निजी तस्वीरें सबको भेज दूँगा", "निजी फोटो ऑनलाइन डाल दूंगा"),
            "fake_profile_impersonation": ("तुम्हारे नाम से फर्जी खाता", "तुम बनकर लोगों से बात", "तुम्हारी पहचान का उपयोग करके", "तुम्हारे नाम से नकली प्रोफ़ाइल"),
            "defamation_morphing": ("तुम्हारी तस्वीर से छेड़छाड़", "तुम्हारी नकली तस्वीर", "तुम्हारे बारे में झूठा आरोप", "तुम्हारी फोटो को बदलकर"),
            "other": ("धमकी दी",),
        },
        "medium": {},
    },
    "kn": {
        "critical": {
            "other": ("ಕೊಲ್ಲುತ್ತೇನೆ", "ಗುಂಡು ಹೊಡೆಯುತ್ತೇನೆ"),
        },
        "high": {
            "cyberstalking_bullying": ("ನಿನ್ನನ್ನು ಹಿಂಬಾಲಿಸುತ್ತೇನೆ", "ನಿನ್ನ ಮನೆ ಎಲ್ಲಿದೆ ನನಗೆ ಗೊತ್ತು", "ನಿನ್ನ ಸ್ಥಳವನ್ನು ಟ್ರ್ಯಾಕ್", "ನಿನ್ನ ಕಚೇರಿ ಹೊರಗೆ ಕಾಯುತ್ತೇನೆ"),
            "blackmail_threatening": ("ಹಣ ಕೊಡದಿದ್ದರೆ", "ಹಣ ಕೊಡು ಇಲ್ಲದಿದ್ದರೆ", "ಬ್ಲ್ಯಾಕ್‌ಮೇಲ್ ಮಾಡುತ್ತೇನೆ", "ಬೆದರಿಕೆ ಹಾಕಿ ಹಣ"),
            "intimate_image_abuse": ("ಚಿತ್ರಗಳನ್ನು ಹರಡುತ್ತೇನೆ", "ಖಾಸಗಿ ಚಿತ್ರಗಳನ್ನು ಹಂಚುತ್ತೇನೆ", "ಚಿತ್ರಗಳನ್ನು ಎಲ್ಲರಿಗೂ ಕಳುಹಿಸುತ್ತೇನೆ", "ಖಾಸಗಿ ಫೋಟೋಗಳನ್ನು ಪೋಸ್ಟ್ ಮಾಡುತ್ತೇನೆ"),
            "fake_profile_impersonation": ("ನಿನ್ನ ಹೆಸರಿನಲ್ಲಿ ನಕಲಿ ಖಾತೆ", "ನಿನ್ನಂತೆ ನಟಿಸಿ", "ನಿನ್ನ ಗುರುತನ್ನು ಬಳಸಿ ಸಂದೇಶ", "ನಿನ್ನ ಫೋಟೋ ಬಳಸಿ ನಕಲಿ ಪ್ರೊಫೈಲ್"),
            "defamation_morphing": ("ನಿನ್ನ ಫೋಟೋವನ್ನು ತಿರುಚಿ", "ನಿನ್ನ ಬಗ್ಗೆ ಸುಳ್ಳು ಆರೋಪ", "ನಿನ್ನ ನಕಲಿ ಚಿತ್ರ", "ನಿನ್ನ ಚಿತ್ರವನ್ನು ಬದಲಿಸಿ"),
            "other": ("ಬೆದರಿಕೆ ಹಾಕಿ ಹಣ",),
        },
        "medium": {},
    },
}

# Broader English patterns are deliberately combinations of a scenario cue,
# an action, and a person/context cue. They improve recall beyond exact phrases
# while avoiding a generic toxicity/keyword classifier. Every result remains
# a review lead, and context cautions are preserved rather than treated as a
# verdict about intent or truth.
ENGLISH_PATTERNS = {
    "cyberstalking_bullying": (
        re.compile(
            r"\b(?:follow|track|watch|monitor|wait|show up|turn up|find|found)\w*\b"
            r".{0,120}\b(?:you|me|your|my|location|route|bus stop|train|commute|home|office|work|class|friends|stories)\b", re.I
        ),
        re.compile(
            r"\b(?:keep|keeps|kept|continue\w*|won't stop|will not stop|not going to stop|every night|every day|again and again)\b"
            r".{0,100}\b(?:messag\w*|contact\w*|call\w*|tag\w*|follow\w*|reply\w*|show\w* up)\b"
            r".{0,80}\b(?:you|me|your|my|friends|coworkers|family|home|office|work|class)\b", re.I
        ),
        re.compile(
            r"\b(?:new|another|different|multiple|five)\s+(?:accounts?|profiles?|numbers?)\b"
            r".{0,100}\b(?:contact|message|call|tag|follow)\w*\b", re.I
        ),
        re.compile(
            r"\b(?:pile on|dogpile|mock\w*|humiliate\w*|call(?:ing)? me names|tag(?:ged|ging)? me in every|"
            r"share my (?:schedule|location)|asking where i live)\b", re.I
        ),
        re.compile(
            r"\b(?:blocked me|asked .{0,35} to stop|no contact)\b.{0,110}\b"
            r"(?:new account|another account|message\w*|contact\w*|follow\w*|tag\w*|call\w*)\b", re.I
        ),
        re.compile(
            r"\b(?:outside|near|by|at)\s+(?:your|my|the)\s+(?:office|home|workplace|school|class|bus stop|coaching center)\b"
            r".{0,90}\b(?:closing time|tomorrow|tonight|friday|wait|come|show up)\b", re.I
        ),
        re.compile(
            r"\b(?:changed|changing|new) your (?:username|profile)\b.{0,100}\b"
            r"(?:saved|found|searched|tracked)\b.{0,60}\b(?:profile|account|you)\b", re.I
        ),
        re.compile(
            r"\b(?:new|another) account\b.{0,80}\b(?:photo|picture|video|location|street|home|office|class|work)\b", re.I
        ),
        re.compile(
            r"\b(?:know|saved|watched)\b.{0,60}\b(?:your|my)\s+(?:train|bus|schedule|time|route|location|stories)\b"
            r".{0,90}\b(?:find|wait|show up|notice|meet|follow)\w*\b", re.I
        ),
        re.compile(
            r"\b(?:join|enter)\b.{0,50}\b(?:every|all)\s+(?:group|chat|server)s?\b.{0,70}\b(?:you|your)\b", re.I
        ),
        re.compile(r"\b(?:i know where you go|i know which .{0,30} you use)\b.{0,60}\b(?:walk|work|class|home|stop|route)\b", re.I),
        re.compile(r"\b(?:blank|silent) call\b.{0,80}\b(?:home|location|where you are|whether you are)\b", re.I),
        re.compile(
            r"\bafter i blocked\b.{0,80}\b(?:contact|message|call|ask)\w*\b.{0,90}\b"
            r"(?:coworkers|friends|family|office|schedule|where)\b", re.I
        ),
        re.compile(
            r"\b(?:keep|keeps|kept|continue\w*)\b.{0,70}\b(?:send\w*|make\w*)\b.{0,35}\b"
            r"(?:requests?|messages?|calls?)\b.{0,80}\b(?:new|another|different)\s+(?:profiles?|accounts?)\b", re.I
        ),
        re.compile(r"\b(?:unwanted messages|pressuring me|pressure me to reply|pressure me)\b", re.I),
        re.compile(
            r"\b(?:come|show up|wait|find)\b.{0,60}\b(?:at|to|near|outside)\b.{0,70}\b"
            r"(?:my|your|the)\s+(?:workplace|office|home|school|class)\b.{0,90}\b(?:if|unless|or)\b", re.I
        ),
    ),
    "blackmail_threatening": (
        re.compile(
            r"\b(?:pay|send|transfer|give)\b.{0,100}\b(?:or else|unless|otherwise|or i|or they|or it|or the sender)\b"
            r".{0,110}\b(?:publish|share|forward|expose|tell|contact|report|post|send|make.{0,20}public)\w*\b", re.I
        ),
        re.compile(
            r"\b(?:threat\w*|demand\w*|blackmail\w*)\b.{0,100}\b"
            r"(?:money|payment|transfer|gift card|amount|pay)\b.{0,90}\b"
            r"(?:post\w*|publish\w*|share\w*|expose\w*|forward\w*|tell\w*|contact\w*|report\w*|silence|secret)\b", re.I
        ),
        re.compile(
            r"\b(?:money|payment|transfer|gift card|amount|pay)\b.{0,100}\b"
            r"(?:threat\w*|demand\w*|unless|or else|otherwise|silence|keep.{0,25}(?:secret|private)|"
            r"(?:share\w*|publish\w*|expose\w*|forward\w*|tell\w*|contact\w*|report\w*))\b", re.I
        ),
        re.compile(
            r"\b(?:unless|or else|otherwise|if you (?:do not|don't))\b.{0,90}\b"
            r"(?:pay|send|transfer|comply|follow|do what|give)\b", re.I
        ),
        re.compile(
            r"\b(?:do what|comply|follow my demand)\b.{0,80}\b(?:or|unless|otherwise)\b"
            r".{0,100}\b(?:publish|share|forward|expose|tell|contact|report|post|send)\w*\b", re.I
        ),
        re.compile(
            r"\b(?:pay|send|transfer|give)\b.{0,90}\b(?:and i will|and i won't|to keep|in exchange|so i do not)\b"
            r".{0,100}\b(?:tell|share|publish|expose|contact|report|secret|private)\b", re.I
        ),
        re.compile(
            r"\bpay\b.{0,90}\b(?:after that|then|afterward)\b.{0,70}\b"
            r"(?:post|publish|share|send|forward|expose)\w*\b", re.I
        ),
        re.compile(
            r"\bpay\b.{0,90}\b(?:stop|keep|avoid|prevent)\b.{0,80}\b"
            r"(?:contact|share|post|publish|expose|send)\w*\b", re.I
        ),
        re.compile(
            r"\b(?:refus\w*|declin\w*|won't pay|do not pay|don't pay)\b.{0,100}\b"
            r"(?:post|publish|share|forward|expose|tell|contact|report)\w*\b", re.I
        ),
        re.compile(
            r"\b(?:money|amount|payment|pay)\b.{0,120}\b(?:screenshots?|messages?|private details|chat)\b"
            r".{0,80}\b(?:go|send|share|publish|forward)\w*\b", re.I
        ),
        re.compile(
            r"\bpay\b.{0,90}\b(?:after that|then|afterward)\b.{0,70}\b"
            r"(?:post\w*|publish\w*|share\w*|send\w*|forward\w*|expose\w*)\b", re.I
        ),
        re.compile(
            r"\b(?:refus\w*|declin\w*|won't pay|do not pay|don't pay)\b.{0,100}\b"
            r"(?:post\w*|publish\w*|share\w*|forward\w*|expose\w*|tell\w*|contact\w*|report\w*)\b", re.I
        ),
        re.compile(
            r"\b(?:money|amount|payment|pay)\b.{0,120}\b(?:screenshots?|messages?|private details|chat)\b"
            r".{0,80}\b(?:go|send|share|publish|forward)\w*\b", re.I
        ),
        re.compile(
            r"\b(?:pressure|pressured|demand\w*)\b.{0,70}\b(?:send|transfer|pay|money)\b"
            r".{0,100}\b(?:expos\w*|publish\w*|share\w*|tell\w*|post\w*)\b", re.I
        ),
        re.compile(
            r"\b(?:gift card|payment|transfer)\b.{0,100}\b(?:keep|out of|private|secret|expos\w*|publish\w*)\b", re.I
        ),
        re.compile(
            r"\b(?:pay for silence|money to keep .{0,35} from being shared|"
            r"send .{0,35} to keep .{0,35} (?:private|secret))\b", re.I
        ),
    ),
    "fake_profile_impersonation": (
        re.compile(
            r"\b(?:fake|clon\w*|copied|copying|lookalike|copy of)\b.{0,50}\b(?:profile|account|page)\b"
            r".{0,120}\b(?:me|my|you|your|photo|name|identity)\b", re.I
        ),
        re.compile(
            r"\b(?:account|profile|page)\b.{0,100}\b(?:my|your)\s+(?:name|photo|pictures?|identity|profile)\b"
            r".{0,100}\b(?:message|contact|ask|tell|claim|pretend|reply|send|use|request)\w*\b", re.I
        ),
        re.compile(
            r"\b(?:using|uses|used|copied|copying)\s+(?:my|your)\s+(?:name|identity|photo|pictures?|profile)\b"
            r".{0,100}\b(?:message|contact|ask|tell|reply|send|claim|request)\w*\b", re.I
        ),
        re.compile(
            r"\b(?:impersonat\w*|pretending to be|claim\w* to be|as if it were|as though it were)\b"
            r".{0,65}\b(?:me|you|my|your)\b", re.I
        ),
        re.compile(
            r"\b(?:profile|account|page)\b.{0,100}\b(?:pretending to be|impersonating|claims? to be)\b"
            r".{0,65}\b(?:me|you|my|your)\b", re.I
        ),
    ),
}

INTIMATE_IMAGE_SIGNAL = re.compile(
    r"\b(?:intimate|private|nude|fabricated|fake|altered|morphed)\b.{0,40}\b"
    r"(?:photos?|images?|pictures?|videos?|clips?)\b|\b(?:photos?|images?|pictures?|videos?|clips?)\b"
    r".{0,40}\b(?:intimate|private|nude|fabricated|fake|altered|morphed)\b", re.I
)
INTIMATE_IMAGE_ACTION = re.compile(
    r"\b(?:share\w*|post\w*|publish\w*|upload\w*|send\w*|forward\w*|circulat\w*|leak\w*|"
    r"creat\w*|mak\w*|spread\w*|tag\w*|go to|reach)\b", re.I
)
INTIMATE_IMAGE_COERCION = re.compile(
    r"\b(?:threat\w*|will|would|unless|or else|if i|if you|demand\w*|pressure\w*|blackmail\w*|"
    r"says? .{0,35}(?:share|post|send|publish)|claims? .{0,35}(?:have|share|post))\b", re.I
)

DEFAMATION_MEDIA_SIGNAL = re.compile(
    r"\b(?:photo|image|picture|screenshot|clip|video|audio|recording|quote|post|conversation|chat|collage|notice)\b", re.I
)
DEFAMATION_MANIPULATION_SIGNAL = re.compile(
    r"\b(?:fake|fabricat\w*|doctored|morph\w*|alter\w*|edit\w*|chang\w*|crop\w*|"
    r"cut out|remove\w*|paste\w*|manipulat\w*|made[- ]up|attach\w*|added my face|pasted my face)\b", re.I
)
DEFAMATION_CLAIM_SIGNAL = re.compile(
    r"\b(?:false|falsely|accus\w*|alleg\w*|misleading|misrepresent\w*|claim\w*|"
    r"attribute\w*|made[- ]up|confession|never said|never wrote|did not (?:say|write|record)|"
    r"never attended|not (?:my|something i)|make me look|makes it look|sounds like|pretend\w*|"
    r"under my name|says i (?:approved|said|wrote|threatened)|make\w* .{0,25}look like|admission|"
    r"damage my reputation|misconduct|words i did not)\b", re.I
)
PERSON_REFERENCE = re.compile(r"\b(?:me|my|you|your|i|workplace|coworker|classmates|clients)\b", re.I)


def _contextual_english_categories(text: str) -> set[str]:
    """Find combinations of English cues without deciding whether a claim is true."""
    matches = {
        category
        for category, patterns in ENGLISH_PATTERNS.items()
        if any(pattern.search(text) for pattern in patterns)
    }
    person_context = re.search(r"\b(?:me|my|you|your)\b", text)
    counterfeit_account = re.search(
        r"\b(?:fake|clon\w*|copy of|copied|copying|lookalike)\b.{0,50}\b(?:profile|account|page)\b|"
        r"\b(?:profile|account|page)\b.{0,60}\b(?:pretending to be|impersonating|claims? to be)\b"
        r".{0,50}\b(?:me|you|my|your)\b|"
        r"\b(?:profile|account|page)\b.{0,60}\b(?:my|your)\s+(?:identity|name|photo|pictures?)\b|"
        r"\b(?:impersonat\w*|pretending to be|claim\w* to be)\b.{0,50}\b(?:me|you|my|your)\b",
        text,
    )
    if person_context and counterfeit_account:
        matches.add("fake_profile_impersonation")
    if (
        INTIMATE_IMAGE_SIGNAL.search(text)
        and INTIMATE_IMAGE_ACTION.search(text)
        and INTIMATE_IMAGE_COERCION.search(text)
    ):
        matches.add("intimate_image_abuse")
    if (
        DEFAMATION_MEDIA_SIGNAL.search(text)
        and DEFAMATION_MANIPULATION_SIGNAL.search(text)
        and DEFAMATION_CLAIM_SIGNAL.search(text)
        and PERSON_REFERENCE.search(text)
    ):
        matches.add("defamation_morphing")
    if (
        DEFAMATION_MEDIA_SIGNAL.search(text)
        and DEFAMATION_CLAIM_SIGNAL.search(text)
        and PERSON_REFERENCE.search(text)
        and re.search(r"\b(?:share\w*|post\w*|publish\w*|send\w*|forward\w*|tag\w*|circulat\w*)\b", text)
    ):
        matches.add("defamation_morphing")
    return matches


def detect_threats(text: str, language: str) -> list[ThreatCandidate]:
    language_terms = CATEGORY_TERMS.get(language, CATEGORY_TERMS["en"])
    found: list[ThreatCandidate] = []
    seen: set[tuple[str, str]] = set()
    # OCR commonly inserts line wraps inside a sentence; match cues across
    # whitespace while keeping the original evidence snippet unchanged.
    for segment in re.split(r"(?<=[.!?।])\s+", text):
        snippet = segment.strip()
        if not snippet:
            continue
        lowered = re.sub(r"\s+", " ", snippet.casefold())
        matched_severity: dict[str, str] = {}
        matched_by_phrase: set[str] = set()
        for severity in ("critical", "high", "medium"):
            for threat_class, phrases in language_terms[severity].items():
                if threat_class not in matched_severity and any(phrase.casefold() in lowered for phrase in phrases):
                    matched_severity[threat_class] = severity
                    matched_by_phrase.add(threat_class)
        if language == "en":
            for threat_class in _contextual_english_categories(lowered):
                matched_severity.setdefault(threat_class, "high")
        for threat_class, severity in matched_severity.items():
            key = (threat_class, snippet)
            if key not in seen:
                cautions = context_cautions(snippet, language)
                confidence = .42 if cautions else (
                    .72 if threat_class in matched_by_phrase else .60
                )
                match_kind = "phrase" if threat_class in matched_by_phrase else "context pattern"
                reason = f"Matched a configured {language} review {match_kind} for {threat_class}; human review required."
                if cautions:
                    reason += " Context cues need review: " + ", ".join(cautions) + ". This does not decide whether the content is harmful."
                found.append(ThreatCandidate(
                    threat_class,
                    severity,
                    snippet[:4000],
                    confidence,
                    reason,
                    cautions,
                ))
                seen.add(key)
    if language == "en" and text.strip():
        whole_text = re.sub(r"\s+", " ", text.casefold()).strip()
        already_found = {item.threat_class for item in found}
        for threat_class in _contextual_english_categories(whole_text) - already_found:
            cautions = context_cautions(text, language)
            confidence = .42 if cautions else .56
            reason = (
                f"Matched a configured English review pattern across the evidence excerpt for {threat_class}; "
                "human review required."
            )
            if cautions:
                reason += " Context cues need review: " + ", ".join(cautions) + ". This does not decide whether the content is harmful."
            found.append(ThreatCandidate(threat_class, "high", text.strip()[:4000], confidence, reason, cautions))
    return found[:100]
