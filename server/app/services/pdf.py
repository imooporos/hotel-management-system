"""Генерация PDF-документов: бланк заказа, отчёты."""

from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ---------------------------------------------------------------------------
# Шрифты с поддержкой кириллицы. Пытаемся подключить DejaVuSans, иначе fallback.
# ---------------------------------------------------------------------------

_FONT_NAME = "Helvetica"

for _path in (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
):
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", _path))
        _FONT_NAME = "DejaVuSans"
        break
    except Exception:  # noqa: BLE001 — опциональная регистрация шрифта
        continue


# ---------------------------------------------------------------------------
# Общие стили
# ---------------------------------------------------------------------------

_styles = getSampleStyleSheet()
_h1 = ParagraphStyle("h1", parent=_styles["Heading1"], fontName=_FONT_NAME, fontSize=18, leading=22)
_h2 = ParagraphStyle("h2", parent=_styles["Heading2"], fontName=_FONT_NAME, fontSize=14, leading=18)
_p = ParagraphStyle("p", parent=_styles["Normal"], fontName=_FONT_NAME, fontSize=10, leading=14)
_p_right = ParagraphStyle("p_right", parent=_p, alignment=TA_RIGHT)
_p_left = ParagraphStyle("p_left", parent=_p, alignment=TA_LEFT)
_meta = ParagraphStyle("meta", parent=_p, fontSize=9, textColor=colors.grey)


def _fmt_money(value: Any) -> str:
    if value is None:
        return "—"
    return f"{Decimal(value):,.2f} ₽".replace(",", " ")


def _fmt_date(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.strftime("%d.%m.%Y")
    return str(value or "—")


# ---------------------------------------------------------------------------
# Бланк заказа (booking receipt)
# ---------------------------------------------------------------------------


def generate_booking_receipt(booking: dict, services: list[dict]) -> bytes:
    """Готовит PDF с бланком заказа гостя."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title=f"Booking #{booking['booking_id']}",
        author="Hotel Management",
    )
    story: list = []

    story.append(Paragraph("Бланк бронирования №&nbsp;{}".format(booking["booking_id"]), _h1))
    story.append(Paragraph(
        f"сформирован {datetime.now().strftime('%d.%m.%Y %H:%M')}", _meta
    ))
    story.append(Spacer(1, 6 * mm))

    # Гость и номер
    info_rows = [
        ["Гость", booking.get("guest_name", "—")],
        ["E-mail", booking.get("guest_email", "—")],
        ["Телефон", booking.get("guest_phone") or "—"],
        ["Номер", f"{booking['room_number']} ({booking['category_title']})"],
        ["Заезд", _fmt_date(booking["check_in"])],
        ["Выезд", _fmt_date(booking["check_out"])],
        ["Ночей", str(booking.get("nights", "—"))],
        ["Гостей", str(booking.get("guests_count", "—"))],
        ["Статус", booking["status"]],
    ]
    table = Table(info_rows, colWidths=[55 * mm, 110 * mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 6 * mm))

    # Услуги
    story.append(Paragraph("Состав заказа", _h2))
    rows = [["Позиция", "Кол-во", "Цена", "Сумма"]]
    rows.append([
        f"Проживание: {booking['nights']} ночей × {booking['category_title']}",
        "1",
        _fmt_money(booking["total_price"] - sum(s["unit_price"] * s["quantity"] for s in services)),
        _fmt_money(booking["total_price"] - sum(s["unit_price"] * s["quantity"] for s in services)),
    ])
    for s in services:
        rows.append([
            s["title"],
            str(s["quantity"]),
            _fmt_money(s["unit_price"]),
            _fmt_money(Decimal(s["unit_price"]) * s["quantity"]),
        ])
    rows.append(["", "", "Итого:", _fmt_money(booking["total_price"])])
    rows.append(["", "", "Оплачено:", _fmt_money(booking.get("paid_total"))])
    rows.append(["", "", "К оплате:", _fmt_money(booking.get("amount_due"))])

    table = Table(rows, colWidths=[80 * mm, 25 * mm, 30 * mm, 35 * mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("FONTNAME", (2, -3), (-1, -1), _FONT_NAME),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(table)
    story.append(Spacer(1, 14 * mm))

    story.append(Paragraph(
        "Подпись администратора: ____________________________     " 
        "Подпись гостя: ____________________________", _p
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Документ сформирован автоматически информационной системой управления гостиницей.",
        _meta,
    ))

    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Отчёт «Выручка по категориям»
# ---------------------------------------------------------------------------


def generate_revenue_report(rows: list[dict]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=20 * mm, bottomMargin=20 * mm)
    story: list = [
        Paragraph("Отчёт: выручка по категориям", _h1),
        Paragraph(f"сформирован {datetime.now().strftime('%d.%m.%Y %H:%M')}", _meta),
        Spacer(1, 6 * mm),
    ]
    table_rows = [["Категория", "Бронирований", "Выручка", "Оплачено"]]
    total = Decimal(0)
    paid = Decimal(0)
    for r in rows:
        table_rows.append([
            r["category_title"],
            str(r["bookings_count"]),
            _fmt_money(r["revenue_total"]),
            _fmt_money(r["revenue_paid"]),
        ])
        total += Decimal(r["revenue_total"] or 0)
        paid += Decimal(r["revenue_paid"] or 0)
    table_rows.append(["Итого", "", _fmt_money(total), _fmt_money(paid)])

    t = Table(table_rows, colWidths=[60 * mm, 35 * mm, 35 * mm, 35 * mm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F1F5F9")),
    ]))
    story.append(t)
    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Отчёт «Загрузка номерного фонда»
# ---------------------------------------------------------------------------


def generate_occupancy_report(
    *, period_start: date, period_end: date, rate: float, active_bookings: list[dict]
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=20 * mm, bottomMargin=20 * mm)
    story: list = [
        Paragraph("Отчёт: загрузка номерного фонда", _h1),
        Paragraph(
            f"Период: {_fmt_date(period_start)} — {_fmt_date(period_end)}", _p
        ),
        Paragraph(f"Загрузка: <b>{rate*100:.2f}%</b>", _p),
        Spacer(1, 6 * mm),
        Paragraph("Текущие активные бронирования", _h2),
    ]
    if not active_bookings:
        story.append(Paragraph("Нет активных бронирований.", _p))
    else:
        rows = [["#", "Гость", "Номер", "Категория", "Заезд", "Выезд", "Сумма"]]
        for r in active_bookings:
            rows.append([
                str(r["booking_id"]),
                r["guest_name"],
                r["room_number"],
                r["category_title"],
                _fmt_date(r["check_in"]),
                _fmt_date(r["check_out"]),
                _fmt_money(r["total_price"]),
            ])
        t = Table(rows, colWidths=[15 * mm, 45 * mm, 18 * mm, 28 * mm, 22 * mm, 22 * mm, 25 * mm])
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
        ]))
        story.append(t)
    doc.build(story)
    return buf.getvalue()
