from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WalkForwardBacktester:
    def run(self, symbols: list[str], years: int = 5) -> dict:
        if not symbols:
            raise ValueError("Geri test için en az bir sembol gereklidir.")
        raise NotImplementedError(
            "Walk-forward geri test henüz uygulanmadı. Lütfen Test Center üzerinden devre dışı "
            "olduğunu göz önünde bulundurun veya backtest modülünü yapılandırın."
        )
