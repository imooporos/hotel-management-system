"""Генерация PDF-документов (бланк заказа / бронирования)."""

import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import os

_FONT_REGISTERED = False


def _register_fonts():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    bold_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]

    font_file = None
    bold_file = None
    for p in font_paths:
        if os.path.exists(p):
            font_file = p
            break
    for p in bold_paths:
        if os.path.exists(p):
            bold_file = p
            break

    if font_file:
        pdfmetrics.registerFont(TTFont("CustomFont", font_file))
        if bold_file:
            pdfmetrics.registerFont(TTFont("CustomFontBold", bold_file))
        else:
            pdfmetrics.registerFont(TTFont("CustomFontBold", font_file))
    else:
        pdfmetrics.registerFont(TTFont("CustomFont", "Helvetica"))
        pdfmetrics.registerFont(TTFont("CustomFontBold", "Helvetica-Bold"))

    _FONT_REGISTERED = True


def generate_booking_pdf(booking: dict, services: list[dict]) -> bytes:
    _register_fonts()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleRu", parent=styles["Title"],
        fontName="CustomFontBold", fontSize=16,
    )
    heading_style = ParagraphStyle(
        "HeadingRu", parent=styles["Heading2"],
        fontName="CustomFontBold", fontSize=12,
    )
    normal_style = ParagraphStyle(
        "NormalRu", parent=styles["Normal"],
        fontName="CustomFont", fontSize=10, leading=14,
    )
    small_style = ParagraphStyle(
        "SmallRu", parent=styles["Normal"],
        fontName="CustomFont", fontSize=8, leading=10, textColor=colors.grey,
    )

    elements = []

    elements.append(Paragraph("ГОСТИНИЦА «ГРАНД ОТЕЛЬ»", title_style))
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a237e")))
    elements.append(Spacer(1, 6 * mm))

    elements.append(Paragraph(f"БЛАНК ЗАКАЗА № {booking.get('id', '')}", heading_style))
    elements.append(Spacer(1, 4 * mm))

    guest_name = " ".join(filter(None, [
        booking.get("last_name", ""),
        booking.get("first_name", ""),
        booking.get("patronymic", ""),
    ]))

    info_data = [
        ["Гость:", guest_name or "—"],
        ["Email:", booking.get("email", "—")],
        ["Телефон:", booking.get("phone", "—")],
        ["Паспорт:", f'{booking.get("passport_series", "")} {booking.get("passport_number", "")}' if booking.get("passport_series") else "—"],
    ]

    info_table = Table(info_data, colWidths=[40 * mm, 120 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "CustomFontBold"),
        ("FONTNAME", (1, 0), (1, -1), "CustomFont"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6 * mm))

    elements.append(Paragraph("Детали бронирования", heading_style))
    elements.append(Spacer(1, 3 * mm))

    check_in = booking.get("check_in_date", "—")
    check_out = booking.get("check_out_date", "—")
    nights = 0
    if hasattr(check_in, "isoformat") and hasattr(check_out, "isoformat"):
        nights = (check_out - check_in).days
        check_in = check_in.strftime("%d.%m.%Y")
        check_out = check_out.strftime("%d.%m.%Y")

    booking_data = [
        ["Параметр", "Значение"],
        ["Номер комнаты", booking.get("room_number", "—")],
        ["Категория", booking.get("category_name", "—")],
        ["Дата заезда", str(check_in)],
        ["Дата выезда", str(check_out)],
        ["Кол-во ночей", str(nights)],
        ["Кол-во гостей", str(booking.get("guests_count", 1))],
        ["Цена за ночь", f'{float(booking.get("base_price", 0)):,.2f} руб.'],
        ["Статус", str(booking.get("status", "—"))],
    ]

    bt = Table(booking_data, colWidths=[60 * mm, 100 * mm])
    bt.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "CustomFontBold"),
        ("FONTNAME", (0, 1), (-1, -1), "CustomFont"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eaf6")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(bt)
    elements.append(Spacer(1, 6 * mm))

    if services:
        elements.append(Paragraph("Дополнительные услуги", heading_style))
        elements.append(Spacer(1, 3 * mm))

        svc_data = [["Услуга", "Кол-во", "Цена", "Сумма"]]
        svc_total = 0
        for s in services:
            qty = s.get("quantity", 1)
            price = float(s.get("price_at_booking", 0))
            subtotal = qty * price
            svc_total += subtotal
            svc_data.append([
                s.get("name", "—"),
                str(qty),
                f"{price:,.2f} руб.",
                f"{subtotal:,.2f} руб.",
            ])
        svc_data.append(["", "", "Итого услуги:", f"{svc_total:,.2f} руб."])

        st = Table(svc_data, colWidths=[70 * mm, 20 * mm, 35 * mm, 35 * mm])
        st.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "CustomFontBold"),
            ("FONTNAME", (0, 1), (-1, -1), "CustomFont"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eaf6")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
            ("FONTNAME", (-2, -1), (-1, -1), "CustomFontBold"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ]))
        elements.append(st)
        elements.append(Spacer(1, 6 * mm))

    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a237e")))
    elements.append(Spacer(1, 4 * mm))

    total = float(booking.get("total_amount", 0))
    elements.append(Paragraph(f"<b>ИТОГО К ОПЛАТЕ: {total:,.2f} руб.</b>", ParagraphStyle(
        "Total", parent=normal_style, fontName="CustomFontBold", fontSize=14,
        alignment=2,
    )))
    elements.append(Spacer(1, 10 * mm))

    if booking.get("notes"):
        elements.append(Paragraph(f"Примечание: {booking['notes']}", normal_style))
        elements.append(Spacer(1, 6 * mm))

    elements.append(Spacer(1, 15 * mm))
    elements.append(Paragraph("Подпись гостя: _________________________", normal_style))
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph("Подпись администратора: _________________________", normal_style))
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        "Документ сформирован автоматически информационной системой «Гранд Отель»",
        small_style,
    ))

    doc.build(elements)
    return buffer.getvalue()
