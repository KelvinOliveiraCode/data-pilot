"""Configuracao do pytest: torna o pacote em src/ importavel nos testes."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
