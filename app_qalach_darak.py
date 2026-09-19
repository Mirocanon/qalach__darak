import asyncio
import os
import json
import sqlite3
from datetime import datetime

import flet as ft
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


GOLD = "#D4AF37"
INK = "#090A0C"
PANEL = "#111318"
PANEL_ALT = "#171A21"
LINE = "#272B34"
MUTED = "#8B929F"
WHITE = "#F7F7F4"
RED = "#F05D5E"
AMBER = "#F0A94B"
GREEN = "#55C98A"
TEAM_PIN = os.environ.get("QALACH_DARAK_PIN", "2026")
DATA_DIR = os.environ.get("QALACH_DATA_DIR", os.path.dirname(__file__))
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_FILE = os.path.join(DATA_DIR, "qalach_darak.db")
LOGO_FILE = "logo.png.jpg"


def initialize_database():
    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                location TEXT NOT NULL,
                start_date TEXT,
                status TEXT NOT NULL,
                area TEXT,
                rooms TEXT,
                salon REAL DEFAULT 0,
                measurements TEXT DEFAULT '{}'
            )
        """)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(clients)").fetchall()}
        if "measurements" not in columns:
            connection.execute("ALTER TABLE clients ADD COLUMN measurements TEXT DEFAULT '{}' ")


def load_clients():
    with sqlite3.connect(DATABASE_FILE) as connection:
        rows = connection.execute("""
            SELECT name, phone, location, start_date, status, area, rooms, salon, measurements
            FROM clients ORDER BY id DESC
        """).fetchall()
    return [
        {
            "name": row[0], "phone": row[1], "location": row[2], "date": row[3] or "",
            "status": row[4], "area": row[5] or "غير محدد", "rooms": row[6] or "", "salon": row[7] or 0,
            "measurements": json.loads(row[8] or "{}"),
        }
        for row in rows
    ]


def persist_client(client):
    with sqlite3.connect(DATABASE_FILE, timeout=10) as connection:
        connection.execute("""
            INSERT INTO clients (name, phone, location, start_date, status, area, rooms, salon, measurements)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            client["name"], client["phone"], client["location"], client.get("date", ""),
            client["status"], client.get("area", "غير محدد"), str(client.get("rooms", "")), client.get("salon", 0),
            json.dumps(client.get("measurements", {}), ensure_ascii=False),
        ))
        return connection.execute("SELECT last_insert_rowid()").fetchone()[0]


def parse_measurement(value):
    normalized = str(value or "").strip().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    normalized = normalized.replace(",", ".").replace("٫", ".").replace("٬", "")
    normalized = normalized.replace(" ", "")
    number = float(normalized)
    if number < 0:
        raise ValueError
    return number


initialize_database()


def main(page: ft.Page):
    page.title = "قلش دارك | إدارة الورشة"
    page.theme_mode = ft.ThemeMode.DARK
    page.rtl = True
    page.bgcolor = INK
    page.padding = 0

    clients = load_clients()
    materials = []
    active_view = "dashboard"
    known_client_count = len(clients)

    def notify(message):
        page.snack_bar = ft.SnackBar(ft.Text(message), open=True)
        page.update()

    def money(value):
        try:
            return f"{float(value or 0):,.2f} دج"
        except (TypeError, ValueError):
            return "0.00 دج"

    def status_color(status):
        return {
            "في الانتظار والتحضير": RED,
            "قيد التنفيذ الميداني حالياً": AMBER,
            "تم تسليم المفتاح بنجاح": GREEN,
        }.get(status, MUTED)

    def field(label, width=None, value=""):
        return ft.TextField(label=label, value=value, width=width, border_color=LINE, focused_border_color=GOLD, cursor_color=GOLD)

    def section_title(title, subtitle=""):
        parts = [ft.Text(title, size=22, weight=ft.FontWeight.BOLD, color=WHITE)]
        if subtitle:
            parts.append(ft.Text(subtitle, size=12, color=MUTED))
        return ft.Column(parts, spacing=4)

    def branded_screen(content):
        return ft.Stack([
            ft.Image(src=LOGO_FILE, fit=ft.BoxFit.CONTAIN, align=ft.Alignment(0, 0), expand=True, opacity=0.42),
            ft.Container(bgcolor="#70000000", expand=True),
            content,
        ], expand=True, alignment=ft.Alignment(0, 0))

    def badge(text, color):
        return ft.Container(ft.Row([
            ft.Container(width=7, height=7, bgcolor=color, border_radius=4),
            ft.Text(text, size=11, color=color, weight=ft.FontWeight.BOLD),
        ], spacing=6), bgcolor=f"{color}18", padding=9, border_radius=20)

    def metric_card(label, value, icon, accent):
        return ft.Container(ft.Column([
            ft.Row([
                ft.Container(ft.Icon(icon=icon, color=accent, size=19), bgcolor=f"{accent}18", padding=10, border_radius=10),
                ft.Text(label, size=12, color=MUTED, expand=True),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Text(value, size=27, weight=ft.FontWeight.BOLD, color=WHITE),
        ], spacing=16), bgcolor=PANEL, border=ft.Border.all(1, LINE), border_radius=14, padding=18, expand=True)

    def client_rows():
        if not clients:
            return [ft.Container(ft.Text("لا توجد ورشات مسجلة. أضف أول زبون للبدء.", color=MUTED, size=13), padding=24)]
        rows = []
        for client in clients:
            measurements = client.get("measurements", {})
            measurement_summary = " • ".join(f"{name}: {value}" for name, value in measurements.items()) or "لا توجد مقاسات"
            rows.append(ft.Container(ft.Row([
                ft.Column([ft.Text(client["name"], color=WHITE, weight=ft.FontWeight.BOLD), ft.Text(client["phone"], color=MUTED, size=11), ft.Text(measurement_summary, color=GOLD, size=10)], spacing=3, expand=True),
                ft.Text(client["location"], color=MUTED, size=12, expand=True),
                ft.Text(client.get("area", "غير محدد"), color=GOLD, size=12, width=90),
                ft.Text(client["date"] or "غير محدد", color=MUTED, size=12, width=95),
                badge(client["status"], status_color(client["status"])),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=12, border=ft.Border(bottom=ft.BorderSide(1, LINE))))
        return rows

    def client_table():
        return ft.Container(ft.Column([
            ft.Container(ft.Row([
                ft.Text("الزبون", color=MUTED, size=11, expand=True),
                ft.Text("الموقع", color=MUTED, size=11, expand=True),
                ft.Text("المساحة", color=MUTED, size=11, width=90),
                ft.Text("البداية", color=MUTED, size=11, width=95),
                ft.Text("الحالة", color=MUTED, size=11),
            ]), padding=12, bgcolor=PANEL_ALT),
            ft.Column(client_rows(), spacing=0),
        ], spacing=0), bgcolor=PANEL, border=ft.Border.all(1, LINE), border_radius=14)

    def add_client_view():
        name = field("اسم الزبون بالكامل")
        phone = field("رقم الهاتف")
        location = field("الموقع / الولاية")
        date = field("تاريخ بدء الأشغال", value=datetime.now().strftime("%d/%m/%Y"))
        status = ft.Dropdown(label="حالة الورشة", value="في الانتظار والتحضير", options=[ft.dropdown.Option(x) for x in ["في الانتظار والتحضير", "قيد التنفيذ الميداني حالياً", "تم تسليم المفتاح بنجاح"]], border_color=LINE, focused_border_color=GOLD)

        def save_client(e):
            if not name.value or not phone.value or not location.value:
                notify("أكمل اسم الزبون والهاتف والموقع أولاً.")
                return
            clients.append({"name": name.value.strip(), "phone": phone.value.strip(), "location": location.value.strip(), "date": date.value.strip(), "status": status.value, "area": "غير محدد"})
            persist_client(clients[-1])
            notify("تم حفظ الورشة في جدول الفريق.")
            show_view("clients")

        return ft.Column([
            section_title("إضافة ورشة جديدة", "سجّل بيانات الزبون قبل توزيع الفريق."),
            ft.Container(ft.Column([
                ft.Text("بيانات الزبون", color=GOLD, weight=ft.FontWeight.BOLD), name, phone, location, date, status,
                ft.Row([
                    ft.Button("حفظ الورشة", icon=ft.Icons.CHECK, on_click=save_client, style=ft.ButtonStyle(bgcolor=GOLD, color=INK, padding=16)),
                    ft.Button("إلغاء", on_click=lambda e: show_view("clients"), style=ft.ButtonStyle(bgcolor=PANEL_ALT, color=WHITE, padding=16)),
                ], spacing=10),
            ], spacing=14), bgcolor=PANEL, padding=24, border=ft.Border.all(1, LINE), border_radius=14),
        ], spacing=18)

    def dashboard_view():
        waiting = sum(c["status"] == "في الانتظار والتحضير" for c in clients)
        active = sum(c["status"] == "قيد التنفيذ الميداني حالياً" for c in clients)
        done = sum(c["status"] == "تم تسليم المفتاح بنجاح" for c in clients)
        return ft.Column([
            ft.Row([
                section_title("صباح الخير، فريق قلش دارك", "مركز القيادة اليومي للترميم والبلاكو بلاطر والكهرباء والصباغة الحديثة."),
                ft.Button("+ زبون جديد", icon=ft.Icons.ADD, on_click=lambda e: show_view("add"), style=ft.ButtonStyle(bgcolor=GOLD, color=INK, padding=16)),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([
                metric_card("إجمالي الورشات", str(len(clients)), ft.Icons.HOME_WORK, GOLD),
                metric_card("قيد التنفيذ", str(active), ft.Icons.BUILD, AMBER),
                metric_card("بانتظار التحضير", str(waiting), ft.Icons.EVENT, RED),
                metric_card("ورشات مكتملة", str(done), ft.Icons.CHECK_CIRCLE, GREEN),
            ], spacing=12),
            ft.Row([
                ft.Container(ft.Column([
                    ft.Row([ft.Text("جدول الورشات القادمة", size=17, color=WHITE, weight=ft.FontWeight.BOLD, expand=True), ft.Button("عرض الكل", on_click=lambda e: show_view("clients"), style=ft.ButtonStyle(color=GOLD, bgcolor="transparent"))]),
                    client_table(),
                ], spacing=14), expand=2),
                ft.Container(ft.Column([
                    ft.Text("توزيع الفريق", size=17, color=WHITE, weight=ft.FontWeight.BOLD),
                    ft.Text("ثلاثة تخصصات، مسار عمل واحد.", color=MUTED, size=12),
                    ft.Container(ft.Column([
                        ft.Row([ft.Icon(icon=ft.Icons.ELECTRICAL_SERVICES, color=GOLD), ft.Text("الكهربائي", color=WHITE, expand=True), ft.Text("متاح", color=GREEN, size=12)]),
                        ft.Row([ft.Icon(icon=ft.Icons.BUILD, color=GOLD), ft.Text("البلاكيست", color=WHITE, expand=True), ft.Text("متاح", color=GREEN, size=12)]),
                        ft.Row([ft.Icon(icon=ft.Icons.FORMAT_PAINT, color=GOLD), ft.Text("الصباغ", color=WHITE, expand=True), ft.Text("متاح", color=GREEN, size=12)]),
                    ], spacing=18), bgcolor=PANEL_ALT, padding=18, border_radius=12),
                    ft.Text("نصيحة اليوم", color=GOLD, weight=ft.FontWeight.BOLD),
                    ft.Text("ابدؤوا بالكهرباء ثم البلاكو، واتركوا الصباغة للمرحلة النهائية حتى تكون النتيجة نظيفة.", color=MUTED, size=12),
                ], spacing=14), bgcolor=PANEL, padding=20, border=ft.Border.all(1, LINE), border_radius=14, expand=1),
            ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.START),
        ], spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)

    def clients_view():
        return ft.Column([
            ft.Row([section_title("جدول الزبائن والورشات", "كل المعلومات التي يحتاجها الفريق في مكان واحد."), ft.Button("+ إضافة زبون", icon=ft.Icons.ADD, on_click=lambda e: show_view("add"), style=ft.ButtonStyle(bgcolor=GOLD, color=INK, padding=16))], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            client_table(),
        ], spacing=18, scroll=ft.ScrollMode.AUTO, expand=True)

    def client_portal_view():
        client_name = field("الاسم واللقب")
        client_location = field("مكان السكن (الولاية / البلدية)")
        client_phone = field("رقم الهاتف")
        measurement_labels = [
            ("الصالون", "المساحة بالمتر المربع"),
            ("المطبخ", "المساحة بالمتر المربع"),
            ("الهول / الممر", "المساحة بالمتر المربع"),
            ("القوس / الأقواس", "العدد أو القياس بالمتر"),
            ("الغرفة 1", "المساحة بالمتر المربع"),
            ("الغرفة 2", "المساحة بالمتر المربع"),
            ("الغرفة 3", "المساحة بالمتر المربع"),
            ("الغرفة 4", "المساحة بالمتر المربع"),
        ]
        measurement_fields = {name: field(hint) for name, hint in measurement_labels}
        measurement_rows = ft.Column([
            ft.Container(ft.Row([ft.Text(name, color=WHITE, size=13, expand=True), measurement_fields[name]], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=8, border=ft.Border(bottom=ft.BorderSide(1, LINE)))
            for name, _ in measurement_labels
        ], spacing=0)

        def submit_request(e):
            if not (client_name.value or "").strip() or not (client_phone.value or "").strip() or not (client_location.value or "").strip():
                notify("أكمل الاسم والهاتف والعنوان أولاً.")
                return
            try:
                measurements = {name: (control.value or "").strip() for name, control in measurement_fields.items() if (control.value or "").strip()}
                parsed_measurements = {name: parse_measurement(value) for name, value in measurements.items()}
                numeric_total = sum(parsed_measurements.values())
            except (ValueError, TypeError, AttributeError):
                notify("أدخل أرقامًا صحيحة موجبة، مثل 12.5 أو 12,5.")
                return
            if not measurements:
                notify("أدخل مقاسًا واحدًا على الأقل قبل الإرسال.")
                return
            request = {
                "name": (client_name.value or "").strip(),
                "phone": (client_phone.value or "").strip(),
                "location": (client_location.value or "").strip(),
                "date": "طلب جديد",
                "status": "في الانتظار والتحضير",
                "area": f"{numeric_total:,.1f} م²",
                "rooms": json.dumps(parsed_measurements, ensure_ascii=False),
                "salon": parsed_measurements.get("الصالون", 0),
                "measurements": parsed_measurements,
            }
            try:
                request_id = persist_client(request)
            except Exception as error:
                notify(f"تعذر إرسال الطلب: {error}")
                return
            try:
                clients.append(request)
                page.controls.clear()
                page.add(client_success_view(numeric_total, len(measurements), request_id))
                page.update()
            except Exception as error:
                notify(f"تم حفظ الطلب #{request_id}، لكن تعذر عرض صفحة التأكيد: {error}")

        logo_panel = ft.Container(
            ft.Column([
                ft.Image(src=LOGO_FILE, fit=ft.BoxFit.CONTAIN, width=300, height=300, opacity=0.95),
                ft.Text("قلش دارك", color=GOLD, size=24, weight=ft.FontWeight.BOLD),
                ft.Text("نرمم المكان، ونبني الفرق.", color=WHITE, size=13, text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            width=320, height=430, bgcolor="#85000000", border=ft.Border.all(1, "#4A3B17"), border_radius=18,
            alignment=ft.Alignment(0, 0), padding=18,
        )

        return branded_screen(ft.Container(ft.Column([
            ft.Row([
                ft.Column([ft.Text("بوابة الزبون", size=28, color=WHITE, weight=ft.FontWeight.BOLD), ft.Text("أرسل تفاصيل مساحتك للفريق بدون الدخول إلى لوحة الإدارة.", color=MUTED, size=13)], spacing=4, expand=True),
                ft.Button("رجوع", icon=ft.Icons.ARROW_BACK, on_click=lambda e: back_to_login(), style=ft.ButtonStyle(color=GOLD, bgcolor="transparent")),
            ]),
            ft.Row([
                logo_panel,
                ft.Container(ft.Column([
                    ft.Text("بيانات الزبون", color=GOLD, size=17, weight=ft.FontWeight.BOLD),
                    client_name, client_location, client_phone,
                    ft.Divider(color=LINE),
                    ft.Text("قياسات غرف المنزل", color=GOLD, size=17, weight=ft.FontWeight.BOLD),
                    ft.Text("اكتب المساحة بالمتر المربع أو القياس المطلوب أمام كل قسم.", color=MUTED, size=12),
                    measurement_rows,
                    ft.Button("إرسال المقاسات والطلب للفريق", icon=ft.Icons.SEND, on_click=submit_request, style=ft.ButtonStyle(bgcolor=GOLD, color=INK, padding=16)),
                ], spacing=14), bgcolor=PANEL, padding=26, border=ft.Border.all(1, LINE), border_radius=16, width=620),
            ], spacing=20, alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.START, wrap=True),
            ft.Text("قلش دارك  •  بلاكو بلاطر  •  كهرباء  •  صباغة حديثة", color=GOLD, size=11),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16, scroll=ft.ScrollMode.AUTO), alignment=ft.Alignment(0, 0), expand=True))

    def client_success_view(total_area, room_count_value, request_id):
        return branded_screen(ft.Container(ft.Column([
            ft.Container(ft.Icon(icon=ft.Icons.CHECK, color=INK, size=40), bgcolor=GREEN, width=78, height=78, alignment=ft.Alignment(0, 0), border_radius=22),
            ft.Text("تم إرسال طلبك بنجاح", size=28, color=WHITE, weight=ft.FontWeight.BOLD),
            ft.Text(f"تم تسجيل {room_count_value} غرفة وصالون بمساحة إجمالية {total_area:,.1f} م².", color=MUTED, size=14, text_align=ft.TextAlign.CENTER),
            ft.Text(f"رقم الطلب: #{request_id}", color=GOLD, size=14, weight=ft.FontWeight.BOLD),
            ft.Text("سيتواصل معك فريق قلش دارك لتأكيد المعاينة والتفاصيل.", color=GOLD, size=13),
            ft.Button("إرسال طلب جديد", icon=ft.Icons.ADD, on_click=lambda e: open_client_portal(), style=ft.ButtonStyle(bgcolor=GOLD, color=INK, padding=15)),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16), alignment=ft.Alignment(0, 0), expand=True))

    async def watch_new_requests():
        nonlocal known_client_count
        while True:
            await asyncio.sleep(4)
            latest_clients = load_clients()
            if len(latest_clients) <= known_client_count or active_view not in ("dashboard", "clients"):
                continue
            clients.clear()
            clients.extend(latest_clients)
            known_client_count = len(latest_clients)
            content.controls.clear()
            content.controls.append(dashboard_view() if active_view == "dashboard" else clients_view())
            page.snack_bar = ft.SnackBar(ft.Text("وصل طلب مقاسات جديد من بوابة الزبون."), open=True)
            page.update()

    def devis_view():
        categories = {
            "سلع البلاكو بلاطر": [
                "ألواح بلاكو بلاطر BA13 عادية",
                "ألواح بلاكو باقر BA13 مقاومة للرطوبة (خضراء)",
                "ألواح بلاكو BA13 مقاومة للحريق (حمراء)",
                "بروفيل (Cornière)", "بروفيل (Fourrure)", "بروفيل (Montant / Rail)",
                "براغي بلاكو (Vis 25mm)", "براغي تثبيت (Cheville à frapper)",
                "مادة لاصقة (Colle Placo)", "شريط المفاصل (Bande à joint)", "عجين المفاصل (Enduit de jointement)",
            ],
            "سلع الكهرباء والإضاءة": [
                "أسلاك كهربائية 1.5 ملم", "أسلاك كهربائية 2.5 ملم", "قنوات تمرير الأسلاك (Gaine ICTA)",
                "علب التفرع (Boîtes de dérivation)", "علب المفاتيح (Boîtiers d'encastrement)",
                "لوحة قواطع رئيسية (Tableau électrique)", "قواطع كهربائية (Disjoncteurs)",
                "مصابيح سبوت (Spots LED)", "شريط إضاءة مخفية (Ruban LED / Flexible)",
                "محولات طاقة (Transformateurs LED)", "مفاتيح ومآخذ كهربائية (Prises & Interrupteurs)",
            ],
            "سلع الطلاء والصباغة الحديثة": [
                "طلاء أساس (Fixateur / Impression)", "معجون الحوائط (Enduit de lissage)",
                "طلاء مائي عالي الجودة (Vinyle)", "طلاء زيتي (Laque satinée)",
                "صباغة حديثة: ديكور الصابلي (Sablé)", "صباغة حديثة: ستوكو (Stucco)",
                "صباغة حديثة: كراكيلي / فيرو (Ferro)", "شريط لاصق للحماية (Papier cache)",
                "بكرات وفراشي الصباغة (Rouleaux & Pinceaux)", "ورق صنفرة (Papier verre)",
            ],
        }
        category_icons = {"سلع البلاكو بلاطر": ft.Icons.BUILD, "سلع الكهرباء والإضاءة": ft.Icons.ELECTRICAL_SERVICES, "سلع الطلاء والصباغة الحديثة": ft.Icons.FORMAT_PAINT}
        category_colors = {"سلع البلاكو بلاطر": GOLD, "سلع الكهرباء والإضاءة": "#64B5F6", "سلع الطلاء والصباغة الحديثة": "#F59E9E"}
        prices = {}
        labor = field("أجر اليد العاملة للفريق (دج)", value="0")
        client_select = ft.Dropdown(label="اختر الزبون لإصدار الدوفي", options=[ft.dropdown.Option(client["name"]) for client in clients], border_color=LINE, focused_border_color=GOLD)
        total = ft.Text("0.00 دج", size=30, color=INK, weight=ft.FontWeight.BOLD)
        selected_count = ft.Text("0 مادة مسعّرة", color=MUTED, size=12)

        def update_total(e=None):
            priced_items = [item for item in prices.values() if item["field"].value.strip()]
            subtotal = 0
            for item in priced_items:
                try:
                    subtotal += float(item["field"].value.replace(",", ""))
                except ValueError:
                    pass
            try:
                labor_value = float(labor.value or 0)
            except ValueError:
                labor_value = 0
            total.value = money(subtotal + labor_value)
            selected_count.value = f"{len(priced_items)} مادة مسعّرة"
            if e is not None:
                page.update()

        def material_card(category, material_name):
            price_field = field("السعر (دج)")
            prices[material_name] = {"category": category, "field": price_field}
            price_field.on_change = update_total
            return ft.Container(ft.Row([
                ft.Text(material_name, color=WHITE, size=12, expand=True, text_align=ft.TextAlign.RIGHT),
                price_field,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=8, border=ft.Border(bottom=ft.BorderSide(1, LINE)))

        def category_card(category, materials_in_category):
            color = category_colors[category]
            return ft.Container(ft.Column([
                ft.Row([ft.Icon(icon=category_icons[category], color=color, size=22), ft.Text(category, color=color, size=16, weight=ft.FontWeight.BOLD, expand=True)]),
                ft.Text("اكتب السعر يدويًا بالدج أمام كل مادة.", color=MUTED, size=11),
                ft.Column([material_card(category, name) for name in materials_in_category], spacing=0),
            ], spacing=10), bgcolor=PANEL, border=ft.Border.all(1, LINE), border_radius=14, padding=14, expand=True)

        def generate_pdf(e):
            selected = next((client for client in clients if client["name"] == client_select.value), None)
            if not selected:
                notify("اختر الزبون أولاً من القائمة.")
                return
            priced_items = []
            for name, data in prices.items():
                raw_price = data["field"].value.strip().replace(",", "")
                if raw_price:
                    try:
                        priced_items.append({"category": data["category"], "name": name, "price": float(raw_price)})
                    except ValueError:
                        notify(f"تحقق من سعر المادة: {name}")
                        return
            safe_name = "".join(ch for ch in selected["name"] if ch.isalnum() or ch in " _-").strip() or "Client"
            file_name = f"Devis_{safe_name}.pdf"
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle("DevisTitle", parent=styles["Heading1"], fontSize=22, textColor=colors.HexColor(GOLD), alignment=1)
            body_style = ParagraphStyle("DevisBody", parent=styles["Normal"], fontSize=12, textColor=colors.HexColor("#111111"), spaceAfter=8)
            story = [Paragraph("QALACH DARAK - قـلش دارك", title_style), Paragraph("قائمة الدوفي وحساب السلع والخدمات", body_style), Spacer(1, 14), Paragraph(f"<b>الزبون:</b> {selected['name']}", body_style), Paragraph(f"<b>الهاتف:</b> {selected['phone']}", body_style), Paragraph(f"<b>الموقع:</b> {selected['location']}", body_style), Spacer(1, 10)]
            for category in categories:
                category_items = [item for item in priced_items if item["category"] == category]
                if category_items:
                    story.append(Paragraph(f"<b>{category}</b>", body_style))
                    for item in category_items:
                        story.append(Paragraph(f"- {item['name']}: {money(item['price'])}", body_style))
            story.extend([Spacer(1, 10), Paragraph(f"<b>أجر اليد العاملة للفريق:</b> {money(labor.value)}", body_style), Paragraph(f"<b>المجموع النهائي:</b> {total.value}", title_style)])
            SimpleDocTemplate(file_name, pagesize=letter).build(story)
            notify(f"تم إنشاء {file_name} في مجلد المشروع.")

        labor.on_change = update_total
        return ft.Column([
            section_title("قائمة الدوفي وحساب السلع والخدمات", "ثلاث قوائم منظمة. اكتب أسعار المواد المطلوبة فقط، وسيُحسب الإجمالي فورًا."),
            client_select,
            ft.Column([category_card(category, items) for category, items in categories.items()], spacing=14),
            ft.Container(ft.Column([ft.Text("أجر اليد العاملة للفريق (دج)", color=INK, size=13, weight=ft.FontWeight.BOLD), labor, ft.Row([ft.Text("المجموع الإجمالي", color=INK, size=13, expand=True), total], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), selected_count], spacing=10), bgcolor=GOLD, padding=18, border_radius=14),
            ft.Button("توليد ملف الدوفي للزبون", icon=ft.Icons.DOWNLOAD, on_click=generate_pdf, style=ft.ButtonStyle(bgcolor=PANEL_ALT, color=WHITE, padding=16)),
        ], spacing=18, scroll=ft.ScrollMode.AUTO, expand=True)

    content = ft.Column(expand=True, spacing=0)

    def show_view(view):
        nonlocal active_view, known_client_count
        active_view = view
        if view in ("dashboard", "clients", "devis"):
            previous_count = len(clients)
            clients.clear()
            clients.extend(load_clients())
            if len(clients) > previous_count and previous_count == known_client_count:
                notify(f"وصل طلب جديد للفريق ({len(clients) - previous_count} طلب).")
            known_client_count = len(clients)
        content.controls.clear()
        content.controls.append({"dashboard": dashboard_view, "clients": clients_view, "add": add_client_view, "devis": devis_view}[view]())
        page.update()

    def nav_button(label, icon, view):
        return ft.Button(label, icon=icon, on_click=lambda e: show_view(view), style=ft.ButtonStyle(color=GOLD if active_view == view else MUTED, bgcolor="#252018" if active_view == view else "transparent", padding=14))

    def build_shell():
        sidebar = ft.Container(ft.Column([
            ft.Row([ft.Container(ft.Text("ق", size=22, color=INK, weight=ft.FontWeight.BOLD), bgcolor=GOLD, width=42, height=42, alignment=ft.Alignment(0, 0), border_radius=12), ft.Column([ft.Text("QALACH", color=WHITE, weight=ft.FontWeight.BOLD, size=16), ft.Text("DARAK WORKS", color=GOLD, size=9)], spacing=0)], spacing=10),
            ft.Divider(color=LINE), ft.Text("مساحة الفريق", color=MUTED, size=11),
            nav_button("لوحة التحكم", ft.Icons.DASHBOARD, "dashboard"),
            nav_button("الزبائن والورشات", ft.Icons.GROUP, "clients"),
            nav_button("الحاسبة والدوفي", ft.Icons.RECEIPT_LONG, "devis"),
            ft.Container(expand=True), ft.Text("نظام داخلي للفريق", color=MUTED, size=11), ft.Text("v2.0  •  Qalach Darak", color=GOLD, size=11),
        ], spacing=10), width=235, bgcolor="#0F1116", padding=20, border=ft.Border(right=ft.BorderSide(1, LINE)))
        topbar = ft.Container(ft.Row([ft.Text("مساحة العمل الخاصة", color=MUTED, size=12, expand=True), ft.Button("تحديث", icon=ft.Icons.REFRESH, on_click=lambda e: show_view(active_view), style=ft.ButtonStyle(color=GOLD, bgcolor="transparent")), ft.Text(datetime.now().strftime("%d / %m / %Y"), color=GOLD, size=12), ft.Icon(icon=ft.Icons.LOCK, color=GREEN, size=17)], spacing=14), padding=15, border=ft.Border(bottom=ft.BorderSide(1, LINE)))
        return branded_screen(ft.Row([sidebar, ft.Column([topbar, ft.Container(content, padding=25, expand=True)], expand=True, spacing=0)], expand=True, spacing=0))

    def open_client_portal():
        page.controls.clear()
        page.add(client_portal_view())
        page.update()

    def back_to_login():
        page.controls.clear()
        page.add(login_view())
        page.update()

    def login_view():
        pin = ft.TextField(label="رمز دخول الفريق", password=True, can_reveal_password=True, width=300, border_color=LINE, focused_border_color=GOLD)

        def unlock(e):
            if pin.value == TEAM_PIN:
                page.controls.clear()
                page.add(build_shell())
                show_view("dashboard")
            else:
                pin.error_text = "الرمز غير صحيح"
                page.update()

        return ft.Container(ft.Column([
            ft.Container(ft.Text("ق", size=42, color=INK, weight=ft.FontWeight.BOLD), bgcolor=GOLD, width=78, height=78, alignment=ft.Alignment(0, 0), border_radius=22),
            ft.Text("قلش دارك", size=32, weight=ft.FontWeight.BOLD, color=WHITE),
            ft.Text("نظام إدارة الورشة الخاص بالفريق", size=14, color=MUTED),
            ft.Container(ft.Column([ft.Text("دخول آمن", color=GOLD, size=18, weight=ft.FontWeight.BOLD), ft.Text("هذه المساحة مخصصة لفريق الشركة فقط.", color=MUTED, size=12), pin, ft.Button("فتح لوحة التحكم", icon=ft.Icons.LOCK_OPEN, on_click=unlock, style=ft.ButtonStyle(bgcolor=GOLD, color=INK, padding=15), width=300)], spacing=15), bgcolor=PANEL, padding=28, border=ft.Border.all(1, LINE), border_radius=16),
            ft.Divider(color=LINE),
            ft.Text("لست من الفريق؟", color=MUTED, size=12),
            ft.Button("بوابة الزبون", icon=ft.Icons.HOME, on_click=lambda e: open_client_portal(), style=ft.ButtonStyle(color=GOLD, bgcolor="transparent", padding=12), width=300),
            ft.Text("البلاكو بلاطر  •  الكهرباء  •  الصباغة الحديثة", color=GOLD, size=11),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=14), alignment=ft.Alignment(0, 0), expand=True)

    page.add(login_view())
    if hasattr(page, "run_task"):
        page.run_task(watch_new_requests)


ft.run(
    main,
    view=ft.AppView.WEB_BROWSER,
    assets_dir=os.path.dirname(__file__),
    port=int(os.environ.get("PORT", "8550")),
)

