# Controller/pump_controller.py

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Iterable, Dict, Any

# Passe die Import-Pfade ggf. an dein Projekt an:
from Model.pump_model import PumpModel, Pump


class PumpController:
    """
    Dünner Controller um das PumpModel:
    - Bietet Preflight (Status/Distanz)
    - Dosiert Menge in ml über PREPARE -> DISPENSE
    - Kann eine ganze Rezept-Liste (Dispense-Plan) abarbeiten
    - NEU: Toggle für Simulation & I²C-Logging (für Admin-View)
    """

    def __init__(
        self,
        db_filename: str = "mixmate-oida.db",
        i2c_bus: int = 1,
        status_addr: int = 0x10,     # I²C-Adresse deines Status-/Sensor-Controllers
        debug: bool = False,
        dev_mode: bool = False,      # <-- NEU: Simulation beim Start
        log_i2c: bool = False,       # <-- NEU: I²C-DB-Logging beim Start
    ) -> None:
        self.pm = PumpModel(db_filename=db_filename, i2c_bus=i2c_bus, )
        # Start-Flags setzen (nutzt PumpModel-API falls vorhanden, sonst Fallback auf Attribute)
        self._set_dev_mode_internal(dev_mode)
        self._set_log_i2c_internal(log_i2c)

        self.status_addr = status_addr
        self.debug = debug

    # ---------------------------------------------------------
    # NEU: Toggle-API für View/Controller
    # ---------------------------------------------------------
    def enable_simulation(self) -> None:
        """Simulation (Dummy-I²C) einschalten."""
        self._set_dev_mode_internal(True)

    def disable_simulation(self) -> None:
        """Simulation ausschalten (echte I²C-Hardware wird genutzt)."""
        self._set_dev_mode_internal(False)

    def set_log_i2c(self, enabled: bool) -> None:
        """I²C-Frame-Logging in DB an/aus."""
        self._set_log_i2c_internal(bool(enabled))

    def is_simulation(self) -> bool:
        """Aktueller Simulationszustand (für Switch im View)."""
        return bool(getattr(self.pm, "dev_mode", False))

    def is_logging(self) -> bool:
        """Aktueller Logging-Zustand (falls du auch einen Logging-Switch anzeigst)."""
        return bool(getattr(self.pm, "log_i2c", False))

    # interne Setter, nutzen bevorzugt die Methoden aus dem Model, sonst Attribute
    def _set_dev_mode_internal(self, enabled: bool) -> None:
        if hasattr(self.pm, "set_dev_mode"):
            self.pm.set_dev_mode(enabled)
        else:
            self.pm.dev_mode = bool(enabled)

    def _set_log_i2c_internal(self, enabled: bool) -> None:
        if hasattr(self.pm, "set_log_i2c"):
            self.pm.set_log_i2c(enabled)
        else:
            self.pm.log_i2c = bool(enabled)

    # ---------------------------------------------------------
    # Schritt 1: Preflight / Plattform-Abfrage
    # ---------------------------------------------------------
    def preflight_check(self) -> Dict[str, Any]:
        """
        Fragt Statusbit & Distanz vom (zentralen) Status-Controller ab.
        Rückgabe: {"status_bit": int, "distance_mm": float|None}
        """
        status_bit, distance_mm, _raw = self.pm.query_platform(addr=self.status_addr)
        if self.debug:
            print(f"[Preflight] status_bit={status_bit} distance_mm={distance_mm}")
        return {"status_bit": int(status_bit), "distance_mm": distance_mm}

    # ---------------------------------------------------------
    # Schritt 2: Dosieren
    # ---------------------------------------------------------
    def dispense_by_id(
        self,
        pump_id: int,
        amount_ml: float,
        pump_channel: Optional[int] = None,
        cocktail_id: Optional[int] = None,
        ingredient_id: Optional[int] = None,
    ) -> int:
        """
        Dosiert amount_ml aus Pumpe pump_id.
        Optional: pump_channel überschreibt den im Pumpenstamm hinterlegten Kanal.
        Rückgabe: run_id (PumpRuns)
        """
        pump = self._pump_by_id(pump_id)
        if pump is None:
            raise RuntimeError(f"Pumpe mit ID {pump_id} nicht gefunden.")
        if not pump.is_enabled:
            raise RuntimeError(f"Pumpe '{pump.name}' ist deaktiviert.")

        # Kanal ggf. zur Laufzeit überschreiben (ohne DB ändern)
        if pump_channel is not None and pump_channel != pump.channel:
            pump = replace(pump, channel=int(pump_channel))

        if self.debug:
            print(f"[Dispense] pump={pump.name}({pump.pump_id}) ch={pump.channel} amount_ml={amount_ml}")

        run_id = self.pm.dispense(
            pump=pump,
            target_ml=float(amount_ml),
            cocktail_id=cocktail_id,
            ingredient_id=ingredient_id,
        )
        return run_id

    def dispense_by_name(
        self,
        pump_name: str,
        amount_ml: float,
        pump_channel: Optional[int] = None,
        cocktail_id: Optional[int] = None,
        ingredient_id: Optional[int] = None,
    ) -> int:
        """
        Wie dispense_by_id, aber mit Pumpenname.
        """
        pump = self.pm.get_pump_by_name(pump_name)
        if pump is None:
            raise RuntimeError(f"Pumpe '{pump_name}' nicht gefunden.")
        if not pump.is_enabled:
            raise RuntimeError(f"Pumpe '{pump.name}' ist deaktiviert.")

        if pump_channel is not None and pump_channel != pump.channel:
            pump = replace(pump, channel=int(pump_channel))

        if self.debug:
            print(f"[DispenseByName] pump={pump.name} ch={pump.channel} amount_ml={amount_ml}")

        return self.pm.dispense(
            pump=pump,
            target_ml=float(amount_ml),
            cocktail_id=cocktail_id,
            ingredient_id=ingredient_id,
        )

    def dispense_recipe(
        self,
        plan: Iterable[Dict[str, Any]],
        require_all_mapped: bool = True,
    ) -> None:
        """
        Abarbeitung eines Dispense-Plans, z. B. direkt aus RecipeModel.get_dispense_plan():
        plan-Elemente: {"ingredient", "amount_ml", "pump_id", "pump_channel"?}
        """
        # Validierung (optional strikt)
        if require_all_mapped:
            missing = [s for s in plan if not s.get("pump_id")]
            if missing:
                names = ", ".join(s.get("ingredient", "?") for s in missing)
                raise RuntimeError(f"Dispense-Plan unvollständig (keine Pumpe gesetzt für: {names})")

        for step in plan:
            pump_id = step.get("pump_id")
            amount_ml = float(step.get("amount_ml", 0))
            channel = step.get("pump_channel")
            if pump_id is None:
                if self.debug:
                    print(f"[DispenseRecipe] SKIP (kein pump_id) -> {step}")
                continue
            if amount_ml <= 0:
                if self.debug:
                    print(f"[DispenseRecipe] SKIP (amount<=0) -> {step}")
                continue

            if self.debug:
                print(f"[DispenseRecipe] {step.get('ingredient')}: {amount_ml} ml via pump {pump_id} ch={channel}")

            self.dispense_by_id(
                pump_id=pump_id,
                amount_ml=amount_ml,
                pump_channel=channel,
            )

    # ---------------------------------------------------------
    # Hilfsroutinen
    # ---------------------------------------------------------
    def ensure_demo_pumps_if_needed(self) -> None:
        """
        Legt Beispielpumpen an, wenn noch keine existieren (praktisch für Dev/Tests).
        """
        pumps = self.pm.list_pumps()
        if pumps:
            return
        # Beispielwerte – passe sie an deine Hardware an
        self.pm.add_or_update_pump("Vodka-Pumpe", i2c_address=0x12, channel=1, flow_ml_per_s=20.0, enabled=True)
        self.pm.add_or_update_pump("Rum-Pumpe",   i2c_address=0x13, channel=2, flow_ml_per_s=18.5, enabled=True)
        if self.debug:
            print("[DemoPumps] Zwei Beispielpumpen angelegt.")

    def _pump_by_id(self, pump_id: int) -> Optional[Pump]:
        """
        Sucht eine Pumpe per ID (PumpModel hat standardmäßig nur get_by_name/list).
        """
        for p in self.pm.list_pumps():
            if p.pump_id == pump_id:
                return p
        return None
