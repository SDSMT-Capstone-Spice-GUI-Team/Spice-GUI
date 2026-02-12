"""Strategy-pattern renderers for circuit component symbols (#327).

Each component type has an IEEE renderer and an IEC renderer registered in
a ``(component_type, style)`` keyed registry.  The dispatch in
``ComponentGraphicsItem.draw_component_body`` and ``get_obstacle_shape``
delegates to the appropriate renderer via ``get_renderer``.
"""

import math
from abc import ABC, abstractmethod

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPen

# ---------------------------------------------------------------------------
# Abstract base & registry
# ---------------------------------------------------------------------------


class ComponentRenderer(ABC):
    """Base class for all component renderers."""

    @abstractmethod
    def draw(self, painter, component) -> None:
        """Draw the component body using *painter*.

        *component* is the ``ComponentGraphicsItem`` instance — renderers may
        call ``component.scene()`` to decide whether to draw terminal leads.
        """

    @abstractmethod
    def get_obstacle_shape(self, component) -> list[tuple[float, float]]:
        """Return the obstacle polygon for pathfinding (local coords)."""


_registry: dict[tuple[str, str], ComponentRenderer] = {}


def register(component_type: str, style: str, renderer: ComponentRenderer):
    """Register *renderer* for (*component_type*, *style*)."""
    _registry[(component_type, style)] = renderer


def get_renderer(component_type: str, style: str) -> ComponentRenderer:
    """Look up the renderer for (*component_type*, *style*).

    Raises ``KeyError`` if no renderer is registered.
    """
    renderer = _registry.get((component_type, style))
    if renderer is not None:
        return renderer
    raise KeyError(f"No renderer for ({component_type!r}, {style!r})")


def _bounding_rect_obstacle(component) -> list[tuple[float, float]]:
    """Fallback obstacle shape — bounding rect of the component."""
    rect = component.boundingRect()
    return [
        (rect.left(), rect.top()),
        (rect.right(), rect.top()),
        (rect.right(), rect.bottom()),
        (rect.left(), rect.bottom()),
    ]


# ---------------------------------------------------------------------------
# IEEE renderers
# ---------------------------------------------------------------------------


class IEEEResistor(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, 0, -15, 0)
            painter.drawLine(15, 0, 30, 0)
        painter.drawLine(-15, 0, -10, -8)
        painter.drawLine(-10, -8, -5, 8)
        painter.drawLine(-5, 8, 0, -8)
        painter.drawLine(0, -8, 5, 8)
        painter.drawLine(5, 8, 10, -8)
        painter.drawLine(10, -8, 15, 0)

    def get_obstacle_shape(self, component):
        return [(-18.0, -11.0), (18.0, -11.0), (18.0, 11.0), (-18.0, 11.0)]


class IEEECapacitor(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, 0, -5, 0)
            painter.drawLine(5, 0, 30, 0)
        painter.drawLine(-5, -12, -5, 12)
        painter.drawLine(5, -12, 5, 12)

    def get_obstacle_shape(self, component):
        return [(-18.0, -14.0), (18.0, -14.0), (18.0, 14.0), (-18.0, 14.0)]


class IEEEInductor(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, 0, -20, 0)
            painter.drawLine(20, 0, 30, 0)
        for i in range(-20, 20, 8):
            painter.drawArc(i, -5, 8, 10, 0, 180 * 16)

    def get_obstacle_shape(self, component):
        return [(-18.0, -11.0), (18.0, -11.0), (18.0, 11.0), (-18.0, 11.0)]


class IEEEVoltageSource(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, 0, -15, 0)
            painter.drawLine(15, 0, 30, 0)
        painter.drawEllipse(-15, -15, 30, 30)
        painter.drawLine(-10, 2, -10, -2)
        painter.drawLine(-12, 0, -8, 0)
        painter.drawLine(12, 0, 8, 0)

    def get_obstacle_shape(self, component):
        return [(-18.0, -18.0), (18.0, -18.0), (18.0, 18.0), (-18.0, 18.0)]


class IEEECurrentSource(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, 0, -15, 0)
            painter.drawLine(15, 0, 30, 0)
        painter.drawEllipse(-15, -15, 30, 30)
        painter.drawText(-5, 5, "I")

    def get_obstacle_shape(self, component):
        return [(-18.0, -18.0), (18.0, -18.0), (18.0, 18.0), (-18.0, 18.0)]


class IEEEWaveformVoltageSource(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, 0, -15, 0)
            painter.drawLine(15, 0, 30, 0)
        painter.drawEllipse(-15, -15, 30, 30)
        # Draw sine wave symbol
        from models.component import COMPONENT_COLORS

        painter.setPen(QPen(QColor(COMPONENT_COLORS.get(component.component_type, "#E91E63")), 2))
        from PyQt6.QtGui import QPainterPath

        path = QPainterPath()
        path.moveTo(-10, 0)
        for x in range(-10, 11, 2):
            y = 8 * math.sin(x * math.pi / 10)
            path.lineTo(x, y)
        painter.drawPath(path)

    def get_obstacle_shape(self, component):
        return _bounding_rect_obstacle(component)


class IEEEGround(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(0, -10, 0, 0)
        painter.drawLine(0, 0, 0, 10)
        painter.drawLine(-15, 10, 15, 10)
        painter.drawLine(-10, 15, 10, 15)
        painter.drawLine(-5, 20, 5, 20)

    def get_obstacle_shape(self, component):
        return [(-17.0, 1.0), (17.0, 1.0), (17.0, 22.0), (-17.0, 22.0)]


class IEEEOpAmp(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, -10, -20, -10)
            painter.drawLine(-30, 10, -20, 10)
            painter.drawLine(20, 0, 30, 0)
        painter.drawLine(-20, -15, 20, 0)
        painter.drawLine(20, 0, -20, 15)
        painter.drawLine(-20, 15, -20, -15)

        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(-17, -8, -13, -8)
        painter.drawLine(-17, 8, -13, 8)
        painter.drawLine(-15, 6, -15, 10)

    def get_obstacle_shape(self, component):
        return _bounding_rect_obstacle(component)


class IEEEVCVS(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, -10, -15, -10)
            painter.drawLine(-30, 10, -15, 10)
            painter.drawLine(15, -10, 30, -10)
            painter.drawLine(15, 10, 30, 10)
        # Diamond shape
        painter.drawLine(-15, 0, 0, -15)
        painter.drawLine(0, -15, 15, 0)
        painter.drawLine(15, 0, 0, 15)
        painter.drawLine(0, 15, -15, 0)
        # +/- polarity markers
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(5, -6, 9, -6)
        painter.drawLine(7, -8, 7, -4)
        painter.drawLine(5, 6, 9, 6)

    def get_obstacle_shape(self, component):
        return [(-18.0, -18.0), (18.0, -18.0), (18.0, 18.0), (-18.0, 18.0)]


class IEEECCVS(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, -10, -15, -10)
            painter.drawLine(-30, 10, -15, 10)
            painter.drawLine(15, -10, 30, -10)
            painter.drawLine(15, 10, 30, 10)
        # Diamond shape
        painter.drawLine(-15, 0, 0, -15)
        painter.drawLine(0, -15, 15, 0)
        painter.drawLine(15, 0, 0, 15)
        painter.drawLine(0, 15, -15, 0)
        # +/- polarity markers
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(5, -6, 9, -6)
        painter.drawLine(7, -8, 7, -4)
        painter.drawLine(5, 6, 9, 6)
        # Arrow on control side
        painter.drawLine(-12, -2, -8, -2)
        painter.drawLine(-9, -4, -8, -2)
        painter.drawLine(-9, 0, -8, -2)

    def get_obstacle_shape(self, component):
        return [(-18.0, -18.0), (18.0, -18.0), (18.0, 18.0), (-18.0, 18.0)]


class IEEEVCCS(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, -10, -15, -10)
            painter.drawLine(-30, 10, -15, 10)
            painter.drawLine(15, -10, 30, -10)
            painter.drawLine(15, 10, 30, 10)
        # Diamond shape
        painter.drawLine(-15, 0, 0, -15)
        painter.drawLine(0, -15, 15, 0)
        painter.drawLine(15, 0, 0, 15)
        painter.drawLine(0, 15, -15, 0)
        # Arrow inside diamond
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(4, 6, 4, -6)
        painter.drawLine(2, -4, 4, -6)
        painter.drawLine(6, -4, 4, -6)

    def get_obstacle_shape(self, component):
        return [(-18.0, -18.0), (18.0, -18.0), (18.0, 18.0), (-18.0, 18.0)]


class IEEECCCS(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, -10, -15, -10)
            painter.drawLine(-30, 10, -15, 10)
            painter.drawLine(15, -10, 30, -10)
            painter.drawLine(15, 10, 30, 10)
        # Diamond shape
        painter.drawLine(-15, 0, 0, -15)
        painter.drawLine(0, -15, 15, 0)
        painter.drawLine(15, 0, 0, 15)
        painter.drawLine(0, 15, -15, 0)
        # Arrow inside diamond
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawLine(4, 6, 4, -6)
        painter.drawLine(2, -4, 4, -6)
        painter.drawLine(6, -4, 4, -6)
        # Arrow on control side
        painter.drawLine(-12, -2, -8, -2)
        painter.drawLine(-9, -4, -8, -2)
        painter.drawLine(-9, 0, -8, -2)

    def get_obstacle_shape(self, component):
        return [(-18.0, -18.0), (18.0, -18.0), (18.0, 18.0), (-18.0, 18.0)]


class IEEEBJTNPN(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-20, 0, -8, 0)
            painter.drawLine(8, -12, 20, -20)
            painter.drawLine(8, 12, 20, 20)
        painter.drawLine(-8, -12, -8, 12)
        painter.drawLine(-8, -6, 8, -12)
        painter.drawLine(-8, 6, 8, 12)
        painter.drawLine(8, 12, 4, 7)
        painter.drawLine(8, 12, 3, 12)

    def get_obstacle_shape(self, component):
        return [(-12.0, -15.0), (12.0, -15.0), (12.0, 15.0), (-12.0, 15.0)]


class IEEEBJTPNP(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-20, 0, -8, 0)
            painter.drawLine(8, -12, 20, -20)
            painter.drawLine(8, 12, 20, 20)
        painter.drawLine(-8, -12, -8, 12)
        painter.drawLine(-8, -6, 8, -12)
        painter.drawLine(-8, 6, 8, 12)
        painter.drawLine(-8, 6, -3, 2)
        painter.drawLine(-8, 6, -3, 7)

    def get_obstacle_shape(self, component):
        return [(-12.0, -15.0), (12.0, -15.0), (12.0, 15.0), (-12.0, 15.0)]


class IEEEMOSFETNMOS(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(20, -20, 20, -10)
            painter.drawLine(-20, 0, -10, 0)
            painter.drawLine(20, 20, 20, 10)
        painter.drawLine(-10, -12, -10, 12)
        painter.drawLine(-5, -12, -5, 12)
        painter.drawLine(-5, -10, 20, -10)
        painter.drawLine(-5, 10, 20, 10)
        painter.drawLine(-5, 0, 5, 0)
        painter.drawLine(-5, 10, -1, 7)
        painter.drawLine(-5, 10, -1, 13)

    def get_obstacle_shape(self, component):
        return [(-12.0, -15.0), (12.0, -15.0), (12.0, 15.0), (-12.0, 15.0)]


class IEEEMOSFETPMOS(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(20, -20, 20, -10)
            painter.drawLine(-20, 0, -10, 0)
            painter.drawLine(20, 20, 20, 10)
        painter.drawLine(-10, -12, -10, 12)
        painter.drawLine(-5, -12, -5, 12)
        painter.drawLine(-5, -10, 20, -10)
        painter.drawLine(-5, 10, 20, 10)
        painter.drawLine(-5, 0, 5, 0)
        painter.drawLine(0, 10, -4, 7)
        painter.drawLine(0, 10, -4, 13)
        painter.drawEllipse(-8, -2, 4, 4)

    def get_obstacle_shape(self, component):
        return [(-12.0, -15.0), (12.0, -15.0), (12.0, 15.0), (-12.0, 15.0)]


class IEEEVCSwitch(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, -10, -15, -10)
            painter.drawLine(-30, 10, -15, 10)
            painter.drawLine(15, -10, 30, -10)
            painter.drawLine(15, 10, 30, 10)
        painter.drawRect(-15, -15, 30, 30)
        painter.drawLine(-8, 8, 8, -4)
        painter.drawEllipse(-10, 6, 4, 4)
        painter.drawEllipse(6, -4, 4, 4)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.drawLine(-12, 0, -5, 0)
        painter.drawLine(-7, -2, -5, 0)
        painter.drawLine(-7, 2, -5, 0)

    def get_obstacle_shape(self, component):
        return [(-18.0, -18.0), (18.0, -18.0), (18.0, 18.0), (-18.0, 18.0)]


class IEEEDiode(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, 0, -10, 0)
            painter.drawLine(10, 0, 30, 0)
        painter.drawLine(-10, -10, -10, 10)
        painter.drawLine(-10, -10, 10, 0)
        painter.drawLine(-10, 10, 10, 0)
        painter.drawLine(10, -10, 10, 10)

    def get_obstacle_shape(self, component):
        return [(-12.0, -12.0), (12.0, -12.0), (12.0, 12.0), (-12.0, 12.0)]


class IEEELED(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, 0, -10, 0)
            painter.drawLine(10, 0, 30, 0)
        painter.drawLine(-10, -10, -10, 10)
        painter.drawLine(-10, -10, 10, 0)
        painter.drawLine(-10, 10, 10, 0)
        painter.drawLine(10, -10, 10, 10)
        # Light emission arrows
        painter.drawLine(2, -10, 6, -16)
        painter.drawLine(4, -16, 6, -16)
        painter.drawLine(6, -14, 6, -16)
        painter.drawLine(7, -8, 11, -14)
        painter.drawLine(9, -14, 11, -14)
        painter.drawLine(11, -12, 11, -14)

    def get_obstacle_shape(self, component):
        return [(-12.0, -18.0), (14.0, -18.0), (14.0, 12.0), (-12.0, 12.0)]


class IEEEZenerDiode(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, 0, -10, 0)
            painter.drawLine(10, 0, 30, 0)
        painter.drawLine(-10, -10, -10, 10)
        painter.drawLine(-10, -10, 10, 0)
        painter.drawLine(-10, 10, 10, 0)
        painter.drawLine(10, -10, 10, 10)
        painter.drawLine(10, -10, 7, -13)
        painter.drawLine(10, 10, 13, 13)

    def get_obstacle_shape(self, component):
        return [(-12.0, -15.0), (15.0, -15.0), (15.0, 15.0), (-12.0, 15.0)]


# ---------------------------------------------------------------------------
# IEC renderers — unique drawing for Resistor, Capacitor, Inductor;
# all others delegate to their IEEE counterpart.
# ---------------------------------------------------------------------------


class IECResistor(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, 0, -15, 0)
            painter.drawLine(15, 0, 30, 0)
        painter.drawRect(-15, -8, 30, 16)

    def get_obstacle_shape(self, component):
        return [(-18.0, -10.0), (18.0, -10.0), (18.0, 10.0), (-18.0, 10.0)]


class IECCapacitor(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, 0, -5, 0)
            painter.drawLine(5, 0, 30, 0)
        # IEC non-polarized: two parallel lines (same as IEEE)
        painter.drawLine(-5, -12, -5, 12)
        painter.drawLine(5, -12, 5, 12)

    def get_obstacle_shape(self, component):
        return [(-18.0, -14.0), (18.0, -14.0), (18.0, 14.0), (-18.0, 14.0)]


class IECInductor(ComponentRenderer):
    def draw(self, painter, component):
        if component.scene() is not None:
            painter.drawLine(-30, 0, -18, 0)
            painter.drawLine(18, 0, 30, 0)
        # IEC inductor: filled rectangular humps
        painter.drawRect(-18, -8, 36, 8)
        painter.drawLine(-18, 0, 18, 0)

    def get_obstacle_shape(self, component):
        return [(-20.0, -10.0), (20.0, -10.0), (20.0, 2.0), (-20.0, 2.0)]


# IEEE singleton instances used by IEC delegates
_ieee_voltage_source = IEEEVoltageSource()
_ieee_current_source = IEEECurrentSource()
_ieee_waveform_voltage_source = IEEEWaveformVoltageSource()
_ieee_ground = IEEEGround()
_ieee_opamp = IEEEOpAmp()
_ieee_vcvs = IEEEVCVS()
_ieee_ccvs = IEEECCVS()
_ieee_vccs = IEEEVCCS()
_ieee_cccs = IEEECCCS()
_ieee_bjt_npn = IEEEBJTNPN()
_ieee_bjt_pnp = IEEEBJTPNP()
_ieee_mosfet_nmos = IEEEMOSFETNMOS()
_ieee_mosfet_pmos = IEEEMOSFETPMOS()
_ieee_vc_switch = IEEEVCSwitch()
_ieee_diode = IEEEDiode()
_ieee_led = IEEELED()
_ieee_zener_diode = IEEEZenerDiode()


def _make_iec_delegate(ieee_instance: ComponentRenderer) -> "ComponentRenderer":
    """Create an IEC renderer that delegates to its IEEE counterpart."""

    class _IECDelegate(ComponentRenderer):
        def draw(self, painter, component):
            ieee_instance.draw(painter, component)

        def get_obstacle_shape(self, component):
            return ieee_instance.get_obstacle_shape(component)

    return _IECDelegate()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

_ieee_resistor = IEEEResistor()
_ieee_capacitor = IEEECapacitor()
_ieee_inductor = IEEEInductor()
_iec_resistor = IECResistor()
_iec_capacitor = IECCapacitor()
_iec_inductor = IECInductor()

# IEEE registrations
register("Resistor", "ieee", _ieee_resistor)
register("Capacitor", "ieee", _ieee_capacitor)
register("Inductor", "ieee", _ieee_inductor)
register("Voltage Source", "ieee", _ieee_voltage_source)
register("Current Source", "ieee", _ieee_current_source)
register("Waveform Source", "ieee", _ieee_waveform_voltage_source)
register("Ground", "ieee", _ieee_ground)
register("Op-Amp", "ieee", _ieee_opamp)
register("VCVS", "ieee", _ieee_vcvs)
register("CCVS", "ieee", _ieee_ccvs)
register("VCCS", "ieee", _ieee_vccs)
register("CCCS", "ieee", _ieee_cccs)
register("BJT NPN", "ieee", _ieee_bjt_npn)
register("BJT PNP", "ieee", _ieee_bjt_pnp)
register("MOSFET NMOS", "ieee", _ieee_mosfet_nmos)
register("MOSFET PMOS", "ieee", _ieee_mosfet_pmos)
register("VC Switch", "ieee", _ieee_vc_switch)
register("Diode", "ieee", _ieee_diode)
register("LED", "ieee", _ieee_led)
register("Zener Diode", "ieee", _ieee_zener_diode)

# IEC registrations — unique renderers for R, C, L; delegates for the rest
register("Resistor", "iec", _iec_resistor)
register("Capacitor", "iec", _iec_capacitor)
register("Inductor", "iec", _iec_inductor)
register("Voltage Source", "iec", _make_iec_delegate(_ieee_voltage_source))
register("Current Source", "iec", _make_iec_delegate(_ieee_current_source))
register("Waveform Source", "iec", _make_iec_delegate(_ieee_waveform_voltage_source))
register("Ground", "iec", _make_iec_delegate(_ieee_ground))
register("Op-Amp", "iec", _make_iec_delegate(_ieee_opamp))
register("VCVS", "iec", _make_iec_delegate(_ieee_vcvs))
register("CCVS", "iec", _make_iec_delegate(_ieee_ccvs))
register("VCCS", "iec", _make_iec_delegate(_ieee_vccs))
register("CCCS", "iec", _make_iec_delegate(_ieee_cccs))
register("BJT NPN", "iec", _make_iec_delegate(_ieee_bjt_npn))
register("BJT PNP", "iec", _make_iec_delegate(_ieee_bjt_pnp))
register("MOSFET NMOS", "iec", _make_iec_delegate(_ieee_mosfet_nmos))
register("MOSFET PMOS", "iec", _make_iec_delegate(_ieee_mosfet_pmos))
register("VC Switch", "iec", _make_iec_delegate(_ieee_vc_switch))
register("Diode", "iec", _make_iec_delegate(_ieee_diode))
register("LED", "iec", _make_iec_delegate(_ieee_led))
register("Zener Diode", "iec", _make_iec_delegate(_ieee_zener_diode))
