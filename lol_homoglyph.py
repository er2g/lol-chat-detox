# -*- coding: utf-8 -*-
"""
Non-AI sansür: mesajdaki her harfi lookalike karaktere çevirir.
Harita config.json içindeki homoglyph_map'ten gelir.
"""
import lol_config


def get_map(cfg=None):
    if cfg is None:
        cfg = lol_config.load_config()
    m = cfg.get("homoglyph_map")
    if isinstance(m, dict) and m:
        return m
    return lol_config.DEFAULT_HOMOGLYPH


def rewrite_homoglyph(text: str, cfg=None) -> str:
    """Mesajın tamamındaki harfleri lookalike ile değiştirir."""
    table = get_map(cfg)
    return "".join(table.get(ch, ch) for ch in text)


def preview(text: str, cfg=None) -> str:
    return rewrite_homoglyph(text, cfg)
