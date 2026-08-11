"""Normalização de telefone brasileiro para E.164."""

from __future__ import annotations

import pytest

from app.models.common import normalize_br_phone


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("11987654321", "+5511987654321"),          # celular com DDD
        ("(11) 98765-4321", "+5511987654321"),      # celular formatado
        ("5511987654321", "+5511987654321"),        # já com código do país
        ("+55 11 98765-4321", "+5511987654321"),
        ("011987654321", "+5511987654321"),         # com 0 de operadora
        ("1132654321", "+551132654321"),            # fixo com DDD (8 dígitos)
        ("(11) 3265-4321", "+551132654321"),
        ("551132654321", "+551132654321"),          # fixo com código do país
    ],
)
def test_normaliza_formatos_validos(entrada: str, esperado: str) -> None:
    assert normalize_br_phone(entrada) == esperado


@pytest.mark.parametrize("entrada", ["", "123", "987654321", "5511987654321999"])
def test_rejeita_formatos_invalidos(entrada: str) -> None:
    with pytest.raises(ValueError):
        normalize_br_phone(entrada)
