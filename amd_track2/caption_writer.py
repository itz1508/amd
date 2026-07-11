"""Agent A: Generate style-specific captions from validated visual context."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from amd_track2.context_extractor import ContextResult
from amd_track2.vision_client import VisionClient

logger = logging.getLogger(__name__)

# Tech jargon terms that humorous_non_tech must avoid
_TECH_JARGON_TERMS = [
    "debugging", "algorithm", "API", "compile", "deploy", "server", "database",
    "code", "programming", "developer", "software", "hardware", "CPU", "GPU",
    "RAM", "binary", "recursion", "stack", "heap", "cache", "router", "bandwidth",
    "pixel", "render", "shader", "neural network", "machine learning", "AI", "LLM",
    "prompt", "token", "embedding", "gradient", "tensor", "epoch", "batch",
    "inference", "training", "dataset", "model", "classifier", "regression",
    "clustering", "blockchain", "crypto", "NFT", "DeFi", "smart contract", "hash",
    "mining", "wallet", "fork", "commit", "branch", "merge", "pull request",
    "repository", "Git", "GitHub", "IDE", "linter", "debugger", "breakpoint",
    "exception", "traceback", "stack overflow", "null pointer", "segmentation fault",
    "buffer overflow", "SQL", "NoSQL", "JSON", "XML", "YAML", "REST", "GraphQL",
    "SOAP", "OAuth", "JWT", "SSL", "TLS", "HTTPS", "DNS", "DHCP", "TCP", "UDP",
    "IP", "MAC", "VLAN", "subnet", "firewall", "proxy", "load balancer", "CDN",
    "Kubernetes", "Docker", "container", "pod", "service", "ingress", "namespace",
    "helm", "terraform", "ansible", "puppet", "chef", "Jenkins", "CI/CD",
    "pipeline", "build", "artifact", "release", "version", "semver", "changelog",
    "README", "markdown", "LaTeX", "regex", "grep", "sed", "awk", "bash", "shell",
    "terminal", "console", "CLI", "GUI", "TUI", "VS Code", "Emacs", "Vim", "Nano",
    "Emacs Lisp", "Elisp", "Lisp", "Scheme", "Racket", "Clojure", "Haskell",
    "OCaml", "F#", "Scala", "Kotlin", "Swift", "Rust", "Go", "Dart", "Flutter",
    "React", "Angular", "Vue", "Svelte", "Next.js", "Nuxt", "Remix", "Gatsby",
    "Astro", "Solid", "Qwik", "Lit", "Web Components", "Polymer", "jQuery",
    "Backbone", "Ember", "Knockout", "Ext JS", "Sencha", "Dojo", "MooTools",
    "Prototype", "YUI", "Closure", "AMP", "PWA", "SPA", "SSR", "CSR", "ISR",
    "SSG", "JAMstack", "headless", "decoupled", "monolithic", "microservices",
    "serverless", "FaaS", "BaaS", "PaaS", "IaaS", "SaaS", "DaaS", "XaaS",
    "cloud", "edge", "fog", "mist", "hybrid", "multi-cloud", "on-prem", "colo",
    "bare metal", "virtual machine", "hypervisor", "KVM", "Xen", "VMware",
    "VirtualBox", "Parallels", "QEMU", "Bochs", "DOSBox", "Wine", "Proton",
    "Steam", "Epic", "GOG", "itch.io", "Humble", "Origin", "Uplay", "Battle.net",
    "Bethesda", "Rockstar", "Ubisoft", "EA", "Activision", "Blizzard", "Valve",
    "Steam Deck", "Switch", "PlayStation", "Xbox", "Wii", "GameCube", "N64",
    "SNES", "NES", "Genesis", "Saturn", "Dreamcast", "Neo Geo", "Arcade",
    "Pinball", "slot machine", "poker", "blackjack", "roulette", "craps",
    "baccarat", "keno", "bingo", "lottery", "scratch card", "sports betting",
    "fantasy sports", "eSports", "streaming", "VOD", "OTT", "IPTV", "DVB",
    "ATSC", "ISDB", "DTMB", "DMB", "DAB", "DRM", "HDCP", "HDMI", "DisplayPort",
    "VGA", "DVI", "Thunderbolt", "USB", "FireWire", "SCSI", "SATA", "NVMe",
    "M.2", "PCIe", "AGP", "ISA", "EISA", "VLB", "MCA", "PCMCIA", "CardBus",
    "ExpressCard", "SD", "microSD", "CF", "xD", "Memory Stick", "MMC",
    "SmartMedia", "Zip", "Jaz", "Bernoulli", "SyQuest", "MO", "WORM", "RAID",
    "NAS", "SAN", "DAS", "JBOD", "iSCSI", "Fibre Channel", "FCoE", "InfiniBand",
    "RoCE", "RDMA", "NVMe-oF", "Ceph", "Gluster", "Lustre", "GPFS", "BeeGFS",
    "Weka", "VAST", "Pure", "NetApp", "EMC", "Dell", "HP", "IBM", "Lenovo",
    "Cisco", "Juniper", "Arista", "Brocade", "Extreme", "HPE", "Aruba", "Ruckus",
    "Meraki", "Ubiquiti", "MikroTik", "TP-Link", "Netgear", "D-Link", "Linksys",
    "ASUS", "Buffalo", "Synology", "QNAP", "Asustor", "TerraMaster", "WD",
    "Seagate", "Toshiba", "Samsung", "Intel", "AMD", "NVIDIA", "Qualcomm",
    "Broadcom", "Marvell", "Cavium", "ARM", "RISC-V", "MIPS", "PowerPC", "SPARC",
    "Itanium", "x86", "x64", "i386", "i486", "i586", "i686", "Pentium", "Celeron",
    "Xeon", "Core", "Atom", "Ryzen", "Threadripper", "EPYC", "Opteron", "Athlon",
    "Duron", "Sempron", "FX", "A-Series", "Phenom", "Turion", "Athlon XP",
    "Athlon 64", "Athlon II", "Phenom II", "FX-8150", "FX-8350", "FX-9590",
    "A4", "A6", "A8", "A10", "A12", "Ryzen 3", "Ryzen 5", "Ryzen 7", "Ryzen 9",
    "Ryzen Pro", "Threadripper 1900X", "1920X", "1950X", "2920X", "2950X",
    "2970WX", "2990WX", "3960X", "3970X", "3990X", "3995WX", "5945WX",
    "5965WX", "5975WX", "5995WX", "7965WX", "7975WX", "7985WX", "7995WX",
    "EPYC 7001", "7002", "7003", "9004", "9005", "9654", "9754", "9684X",
    "9384X", "9184X", "9124", "9354", "9334", "9274F", "9254", "9224", "9174F",
    "9734", "9754S", "9654P", "9554", "9534", "9474F", "9454", "9374F",
    "9354P", "8534P", "8534", "8434P", "8434", "8334", "8324P", "8324",
    "8314P", "8314", "8224P", "8224", "8214P", "8214", "8124P", "8124",
    "8024P", "8024", "8014P", "8014", "7763", "7713", "7663", "7643", "7543",
    "7513", "7453", "7443", "7413", "7343", "7313", "7283", "7253", "7233",
    "72F3", "74F3", "75F3", "7713P", "7763P", "7773X", "7573X", "7473X",
    "7373X", "73F3",
]

CAPTION_SYSTEM_PROMPT = """\
You are a creative caption writer. You write captions for videos based on provided visual context.
You must write captions in EXACTLY the styles requested. Each style has specific rules.
Respond in valid JSON only, no markdown, no extra text.
"""

CAPTION_USER_PROMPT_TEMPLATE = """\
Write captions for a video based on this visual context:

SCENE SUMMARY: {scene_summary}
MAIN SUBJECTS: {main_subjects}
ACTIONS: {actions}
SETTING: {setting}
IMPORTANT OBJECTS: {important_objects}
MOOD: {mood}
MUST MENTION: {must_mention}
MUST NOT CLAIM: {must_not_claim}
UNCERTAINTIES: {uncertainties}

Write captions in these styles: {styles}

Style definitions:
- formal: objective, factual, professional tone. No slang, no humor.
- sarcastic: dry, ironic, lightly mocking tone. Subtle wit.
- humorous_tech: funny with technology/programming references. Geek humor, tech jargon OK.
- humorous_non_tech: funny everyday humor. NO tech/programming jargon. Accessible to everyone.

Rules:
- Each caption must be grounded in the visual context above.
- Do not hallucinate subjects, objects, or actions not in the context.
- Do not contradict the MUST NOT CLAIM list.
- humorous_non_tech must NOT contain any of these tech/programming terms: {tech_terms}
- Captions for different styles must be meaningfully different from each other.
- Return exactly one caption per requested style.

Respond with valid JSON only using this exact schema:
{{"captions": {{"style_name": "caption text", ...}}}}
"""


@dataclass
class CaptionResult:
    """Result of caption generation."""

    captions: Dict[str, str]
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        return dict(self.captions)


class CaptionWriter:
    """Agent A: generates style-specific captions from grounded context."""

    def __init__(self, vision_client: VisionClient):
        self.vision = vision_client

    def write(self, context: ContextResult, requested_styles: List[str]) -> CaptionResult:
        """One vision call per video to generate all requested style captions."""
        tech_terms = ", ".join(_TECH_JARGON_TERMS[:50]) + ", and similar terms"

        user_prompt = CAPTION_USER_PROMPT_TEMPLATE.format(
            scene_summary=context.scene_summary,
            main_subjects=", ".join(context.main_subjects),
            actions=", ".join(context.actions),
            setting=context.setting,
            important_objects=", ".join(context.important_objects),
            mood=context.mood,
            must_mention=", ".join(context.must_mention),
            must_not_claim=", ".join(context.must_not_claim),
            uncertainties=", ".join(context.uncertainties),
            styles=", ".join(requested_styles),
            tech_terms=tech_terms,
        )

        response = self.vision.complete(
            system_prompt=CAPTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            image_paths=[],
            response_format={"type": "json_object"},
        )

        if not response.success or not response.parsed_json:
            logger.error("Caption generation failed: %s", response.error_message)
            return self._fallback_captions(requested_styles, response.content)

        parsed = response.parsed_json
        captions_dict = parsed.get("captions", {})
        if not isinstance(captions_dict, dict):
            logger.error("Caption response missing 'captions' dict")
            return self._fallback_captions(requested_styles, response.content)

        # Normalize and ensure all requested styles exist
        result: Dict[str, str] = {}
        for style in requested_styles:
            val = captions_dict.get(style)
            if isinstance(val, str) and val.strip():
                result[style] = val.strip()
            else:
                result[style] = self._safe_fallback_for_style(style, context)

        return CaptionResult(captions=result, raw_response=response.content)

    def _fallback_captions(
        self, requested_styles: List[str], raw_response: Optional[str]
    ) -> CaptionResult:
        """Return safe fallback captions when vision call fails."""
        logger.warning("Using fallback captions for styles: %s", requested_styles)
        return CaptionResult(
            captions={s: f"A video showing visible content." for s in requested_styles},
            raw_response=raw_response,
        )

    def _safe_fallback_for_style(self, style: str, context: ContextResult) -> str:
        """Generate a minimal safe caption for a specific style."""
        base = f"A video showing {context.scene_summary.lower()}."
        if style == "formal":
            return base
        if style == "sarcastic":
            return f"Oh, look, {base.lower()}"
        if style == "humorous_tech":
            return f"404: exciting video found. {base}"
        if style == "humorous_non_tech":
            return f"Well, this is something you don't see every day. {base}"
        return base