import os
import base64
import json
from datetime import datetime, timedelta

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
)
from functools import wraps
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-local")

LICENSES_FILE = os.path.join(app.root_path, "licenses.json")


def load_licenses():
    """Carga las licencias desde licenses.json."""
    if not os.path.exists(LICENSES_FILE):
        return {}

    with open(LICENSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_licenses(licenses):
    """Guarda las licencias en licenses.json."""
    with open(LICENSES_FILE, "w", encoding="utf-8") as f:
        json.dump(licenses, f, indent=4, ensure_ascii=False)


def get_license_expiration(license_type):
    """Devuelve fecha de vencimiento según el tipo de licencia."""
    now = datetime.now()

    if license_type == "admin":
        return None  # ilimitado

    if license_type == "24h":
        return now + timedelta(hours=24)

    if license_type == "30d":
        return now + timedelta(days=30)

    return None


def activate_license_code(code):
    """
    Activa un código de licencia.
    Retorna: (ok, mensaje)
    """
    code = code.strip().upper()
    licenses = load_licenses()

    if code not in licenses:
        return False, "Código inválido."

    license_data = licenses[code]
    license_type = license_data.get("type")

    # Código admin: siempre válido, no se marca como usado
    if license_type == "admin":
        session["license"] = {
            "code": code,
            "type": "admin",
            "activated_at": datetime.now().isoformat(),
            "expires_at": None
        }
        return True, "Licencia admin activada correctamente."

    # Para códigos normales: solo se pueden activar una vez
    if license_data.get("used"):
        return False, "Este código ya fue utilizado."

    activated_at = datetime.now()
    expires_at = get_license_expiration(license_type)

    license_data["used"] = True
    license_data["activated_at"] = activated_at.isoformat()
    license_data["expires_at"] = expires_at.isoformat() if expires_at else None

    licenses[code] = license_data
    save_licenses(licenses)

    session["license"] = {
        "code": code,
        "type": license_type,
        "activated_at": activated_at.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None
    }

    return True, "Licencia activada correctamente."


def license_is_active():
    """Revisa si hay licencia activa en la sesión."""
    license_data = session.get("license")

    if not license_data:
        return False

    if license_data.get("type") == "admin":
        return True

    expires_at = license_data.get("expires_at")

    if not expires_at:
        return False

    try:
        expiration_date = datetime.fromisoformat(expires_at)
    except ValueError:
        return False

    return datetime.now() <= expiration_date


def get_license_status_text():
    """Texto simple para mostrar estado de licencia en HTML."""
    license_data = session.get("license")

    if not license_data:
        return "Sin licencia activa"

    if license_data.get("type") == "admin":
        return "Licencia admin activa"

    expires_at = license_data.get("expires_at")
    if not expires_at:
        return "Licencia inválida"

    try:
        expiration_date = datetime.fromisoformat(expires_at)
        return f"Licencia activa hasta {expiration_date.strftime('%d-%m-%Y %H:%M')}"
    except ValueError:
        return "Licencia inválida"

# Usuario y contraseña “quemados” por ahora (luego podemos pasarlo a BD)
USERS = {
    "admin": "1234"  # cámbialo por lo que quieras
}

FIELD_LABELS = {
    "cancha": "Cancha",
    "division": "División",
    "dia": "Día",
    "mes": "Mes",
    "anio": "Año",
    "hora": "Hora",

    "equipo_a_establecimiento": "Equipo A - Establecimiento",
    "equipo_a_categoria": "Equipo A - Categoría",
    "equipo_a_entrenador": "Equipo A - Entrenador",
    "equipo_a_capitan": "Equipo A - Capitán",

    "equipo_b_establecimiento": "Equipo B - Establecimiento",
    "equipo_b_categoria": "Equipo B - Categoría",
    "equipo_b_entrenador": "Equipo B - Entrenador",
    "equipo_b_capitan": "Equipo B - Capitán",

    "equipo_a_jugadores": "Equipo A - Jugadores titulares",
    "equipo_a_suplentes": "Equipo A - Suplentes",
    "equipo_b_jugadores": "Equipo B - Jugadores titulares",
    "equipo_b_suplentes": "Equipo B - Suplentes",

    "goles_primer_tiempo": "Goles 1º tiempo (detalle)",
    "goles_segundo_tiempo": "Goles 2º tiempo (detalle)",
    "resultado_equipo_a_nombre": "Equipo A - Nombre",
    "resultado_equipo_a_goles": "Equipo A - Goles",
    "resultado_equipo_b_nombre": "Equipo B - Nombre",
    "resultado_equipo_b_goles": "Equipo B - Goles",

    "director_turno": "Director de turno",
    "arbitro": "Árbitro",
    "asistente_1": "Asistente 1",
    "asistente_2": "Asistente 2",

    "equipo_a_eventos_nombre": "Equipo A - Nombre equipo",
    "equipo_a_cambios_entran": "Equipo A - Cambios ENTRAN",
    "equipo_a_cambios_salen": "Equipo A - Cambios SALEN",
    "equipo_a_tarjetas_amarillas": "Equipo A - Tarjetas amarillas",
    "equipo_a_expulsados": "Equipo A - Expulsados",

    "equipo_b_eventos_nombre": "Equipo B - Nombre equipo",
    "equipo_b_cambios_entran": "Equipo B - Cambios ENTRAN",
    "equipo_b_cambios_salen": "Equipo B - Cambios SALEN",
    "equipo_b_tarjetas_amarillas": "Equipo B - Tarjetas amarillas",
    "equipo_b_expulsados": "Equipo B - Expulsados",

    "observaciones": "Observaciones",
    "firma_director_turno": "Firma director de turno",
    "firma_arbitro": "Firma árbitro",
    "firma_asistente_1": "Firma asistente 1",
    "firma_asistente_2": "Firma asistente 2",
}

SECTION_GROUPS = [
    ("Datos del partido", ["cancha", "division", "dia", "mes", "anio", "hora"]),
    ("Equipo A", [
        "equipo_a_establecimiento", "equipo_a_categoria",
        "equipo_a_entrenador", "equipo_a_capitan",
        "equipo_a_jugadores", "equipo_a_suplentes"
    ]),
    ("Equipo B", [
        "equipo_b_establecimiento", "equipo_b_categoria",
        "equipo_b_entrenador", "equipo_b_capitan",
        "equipo_b_jugadores", "equipo_b_suplentes"
    ]),
    ("Goles y resultado", [
        "goles_primer_tiempo", "goles_segundo_tiempo",
        "resultado_equipo_a_nombre", "resultado_equipo_a_goles",
        "resultado_equipo_b_nombre", "resultado_equipo_b_goles"
    ]),
    ("Director y árbitros", [
        "director_turno", "arbitro", "asistente_1", "asistente_2"
    ]),
    ("Eventos Equipo A", [
        "equipo_a_eventos_nombre",
        "equipo_a_cambios_entran", "equipo_a_cambios_salen",
        "equipo_a_tarjetas_amarillas", "equipo_a_expulsados"
    ]),
    ("Eventos Equipo B", [
        "equipo_b_eventos_nombre",
        "equipo_b_cambios_entran", "equipo_b_cambios_salen",
        "equipo_b_tarjetas_amarillas", "equipo_b_expulsados"
    ]),
    ("Observaciones y firmas", [
        "observaciones",
        "firma_director_turno", "firma_arbitro",
        "firma_asistente_1", "firma_asistente_2"
    ]),
]


# --------- AUTENTICACIÓN ---------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            # Guardamos a dónde quería ir (por ejemplo /planilla)
            next_url = request.path
            return redirect(url_for("login", next=next_url))
        return f(*args, **kwargs)
    return decorated_function


# Ruta raíz: siempre va al inicio (público)
@app.route("/")
def root():
    return redirect(url_for("inicio"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    # a dónde volver después de logearse
    next_url = request.args.get("next") or request.form.get("next")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if USERS.get(username) == password:
            session["username"] = username
            # volvemos donde nos habían pedido ir, o al inicio
            return redirect(next_url or url_for("inicio"))
        else:
            error = "Usuario o contraseña incorrectos"

    return render_template("login.html", error=error, next=next_url)


# --------- PÁGINAS ---------

# Inicio público
@app.route("/inicio")
def inicio():
    return render_template("inicio.html")

@app.route("/planillas")
def planillas():
    return render_template("planillas.html")


@app.route("/contacto")
def contacto():
    return render_template("contacto.html")


# Planilla protegida
@app.route("/planilla", methods=["GET", "POST"])
#@login_required
def planilla():
    mensaje = None

    if request.method == "POST":
        # Tomamos TODO el formulario
        formulario = request.form.to_dict()

        # Para la sesión solo guardamos los campos de texto (sin imágenes base64)
        datos_planilla = {
            k: v for k, v in formulario.items()
            if not k.endswith("_img")
        }

        session["ultima_planilla"] = datos_planilla
        mensaje = "Planilla guardada (solo en memoria por ahora)."

        return render_template(
        "planilla.html",
        mensaje=mensaje,
        datos=datos_planilla,
        license_active=license_is_active(),
        license_status=get_license_status_text()
    )

    datos_planilla = session.get("ultima_planilla")
    return render_template(
    "planilla.html",
    datos=datos_planilla,
    license_active=license_is_active(),
    license_status=get_license_status_text()
    )



@app.route("/activar", methods=["GET", "POST"])
def activar():
    error = None
    mensaje = None
    next_route = request.args.get("next") or request.form.get("next") or "planilla"

    # Solo permitimos volver a rutas internas conocidas.
    allowed_next_routes = {
        "planilla",
        "planilla_campeonato",
        "planillas",
    }
    if next_route not in allowed_next_routes:
        next_route = "planilla"

    if request.method == "POST":
        code = request.form.get("codigo", "")
        ok, msg = activate_license_code(code)

        if ok:
            return redirect(url_for(next_route))
        else:
            error = msg

    return render_template(
        "activar.html",
        error=error,
        mensaje=mensaje,
        license_status=get_license_status_text(),
        next_route=next_route
    )

# Generación de PDF protegida
@app.route("/descargar", methods=["GET", "POST"])
def descargar():
    if request.method == "POST":
        datos_planilla = request.form.to_dict()
    else:
        datos_planilla = session.get("ultima_planilla") or {}

    if not datos_planilla:
        return redirect(url_for("planilla"))

    # Bloqueo de descarga si no hay licencia activa
    if not license_is_active():
        return redirect(url_for("activar"))

    # Desde aquí hacia abajo queda todo tu código actual de generación PDF

    # Creamos PDF en memoria
    buffer = BytesIO()

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import simpleSplit, ImageReader

    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin = 30
    x0 = margin
    x1 = width - margin
    usable_w = x1 - x0

    # --- LOGO EN ESQUINA SUPERIOR IZQUIERDA ---
    logo_path = os.path.join(app.root_path, "static", "logo.png")
    logo_height = 50  # ajusta tamaño si quieres
    logo_width = 50

    if os.path.exists(logo_path):
        try:
            logo = ImageReader(logo_path)
            logo_y = height - margin - logo_height
            c.drawImage(
                logo,
                x0,
                logo_y,
                width=logo_width,
                height=logo_height,
                mask="auto"
            )
        except Exception:
            # Si la imagen falla, simplemente seguimos sin logo
            pass

    # Coordenada inicial para el resto del contenido (debajo del logo)
    y = height - 100

    def box_label_value(
        x, y, w, h, label, value,
        font_label="Helvetica", font_value="Helvetica",
        size_label=7, size_value=9, leading=10
    ):
        """Dibuja un rectángulo con etiqueta arriba y valor dentro."""
        c.rect(x, y, w, h)
        c.setFont(font_label, size_label)
        c.drawString(x + 3, y + h - 9, label)

        if value:
            c.setFont(font_value, size_value)
            max_width = w - 6
            lines = simpleSplit(str(value), font_value, size_value, max_width)
            ty = y + h - 18
            for line in lines:
                if ty < y + 3:
                    break
                c.drawString(x + 3, ty, line)
                ty -= leading

    def draw_signature_image(data_url, x, y, w, h):
        """Dibuja una imagen de firma (dataURL base64) dentro del rectángulo x,y,w,h."""
        if not data_url:
            return
        try:
            # data:image/png;base64,AAAA...
            if "," in data_url:
                _, b64data = data_url.split(",", 1)
            else:
                b64data = data_url
            img_bytes = base64.b64decode(b64data)
            img_buffer = BytesIO(img_bytes)
            img = ImageReader(img_buffer)
            img_w, img_h = img.getSize()

            # Ajuste para que quepa dentro del recuadro
            max_w = w - 10
            max_h = h - 10
            scale = min(max_w / img_w, max_h / img_h)
            draw_w = img_w * scale
            draw_h = img_h * scale

            x_img = x + (w - draw_w) / 2
            y_img = y + (h - draw_h) / 2

            c.drawImage(img, x_img, y_img, width=draw_w, height=draw_h, mask="auto")
        except Exception:
            # Si algo falla al decodificar, simplemente no dibujamos la firma
            pass

    # --------- PÁGINA 1 ---------
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, "PLANILLA DE FÚTBOL COPA UC")
    y -= 25

    # DATOS DEL PARTIDO (2 filas de 3 casillas)
    row_h = 26
    col_w = usable_w / 3
    filas_datos = [
        [("Cancha", "cancha"), ("División", "division"), ("Hora", "hora")],
        [("Día", "dia"), ("Mes", "mes"), ("Año", "anio")],
    ]
    for fila in filas_datos:
        y -= row_h
        for i, (label, key) in enumerate(fila):
            x = x0 + i * col_w
            box_label_value(x, y, col_w, row_h, label, datos_planilla.get(key, ""))

    y -= 20

    # ESTABLECIMIENTOS / EQUIPOS (4 filas x 2 columnas)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x0, y, "ESTABLECIMIENTOS / EQUIPOS")
    y -= 8

    row_h = 26
    col_w = usable_w / 2

    left_fields = [
        ("Equipo A - Establecimiento", "equipo_a_establecimiento"),
        ("Equipo A - Categoría", "equipo_a_categoria"),
        ("Entrenador (nombre y firma)", "equipo_a_entrenador"),
        ("Capitán (nombre y firma)", "equipo_a_capitan"),
    ]
    right_fields = [
        ("Equipo B - Establecimiento", "equipo_b_establecimiento"),
        ("Equipo B - Categoría", "equipo_b_categoria"),
        ("Entrenador (nombre y firma)", "equipo_b_entrenador"),
        ("Capitán (nombre y firma)", "equipo_b_capitan"),
    ]

    for i in range(4):
        y -= row_h
        box_label_value(x0,        y, col_w, row_h, left_fields[i][0],  datos_planilla.get(left_fields[i][1], ""))
        box_label_value(x0+col_w,  y, col_w, row_h, right_fields[i][0], datos_planilla.get(right_fields[i][1], ""))

    y -= 20

    # JUGADORES Y SUPLENTES
    if y < 260:
        c.showPage()
        width, height = A4
        x0 = margin
        x1 = width - margin
        usable_w = x1 - x0
        y = height - 40

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x0, y, "JUGADORES Y SUPLENTES")
    y -= 8

    row_h = 14          # altura de cada fila
    rows = 11           # 11 jugadores
    team_w = usable_w / 2
    num_col_w = 32      # ancho de la columna del número

    def draw_players_table_pdf(x, y_top, team_title, tipo, field_key):
        """
        Dibuja una tabla de 11 filas con columnas N° / Nombre
        y rellena con los datos de field_key (texto "N° - Nombre" por línea).
        Devuelve la coordenada 'bottom' (abajo de la tabla).
        """
        table_height = (rows + 1) * row_h  # +1 por la fila de encabezado
        top = y_top
        bottom = top - table_height

        # Marco exterior
        c.rect(x, bottom, team_w, table_height)

        # Línea horizontal que separa encabezado de filas
        header_y = top - row_h
        c.line(x, header_y, x + team_w, header_y)

        # Líneas horizontales de las filas
        for i in range(1, rows + 1):
            line_y = header_y - i * row_h
            c.line(x, line_y, x + team_w, line_y)

        # Línea vertical que separa N° de Nombre (solo bajo el encabezado)
        num_x = x + num_col_w
        c.line(num_x, header_y, num_x, bottom)

        # Título (Equipo A - Titulares, etc.) – lo ponemos encima del recuadro
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x + 3, top + 4, f"{team_title} - {tipo}")

        # Encabezados de columnas
        c.drawString(x + 5, header_y + row_h / 2 - 4, "N°")
        c.drawString(num_x + 3, header_y + row_h / 2 - 4, "Nombre")

        # Contenido
        value = datos_planilla.get(field_key, "") or ""
        lines = [ln.strip() for ln in value.splitlines() if ln.strip()]

        c.setFont("Helvetica", 8)
        for idx, line in enumerate(lines[:rows]):
            num = ""
            name = line
            parts = line.split("-", 1)
            if len(parts) == 2:
                num = parts[0].strip()
                name = parts[1].strip()

            row_top = header_y - idx * row_h
            text_y = row_top - row_h + 4

            if num:
                c.drawString(x + 5, text_y, num)
            if name:
                c.drawString(num_x + 3, text_y, name)

        return bottom

    # --- Tablas de TITULARES (Equipo A y B, lado a lado) ---
    y -= 4
    y_top_titulares = y

    bottom_a = draw_players_table_pdf(
        x0, y_top_titulares,
        "Equipo A", "Titulares",
        "equipo_a_jugadores"
    )
    bottom_b = draw_players_table_pdf(
        x0 + team_w, y_top_titulares,
        "Equipo B", "Titulares",
        "equipo_b_jugadores"
    )

    y = min(bottom_a, bottom_b) - 15

    # --- Tablas de SUPLENTES (Equipo A y B, lado a lado) ---
    y_top_suplentes = y

    bottom_a = draw_players_table_pdf(
        x0, y_top_suplentes,
        "Equipo A", "Suplentes",
        "equipo_a_suplentes"
    )
    bottom_b = draw_players_table_pdf(
        x0 + team_w, y_top_suplentes,
        "Equipo B", "Suplentes",
        "equipo_b_suplentes"
    )

    y = min(bottom_a, bottom_b) - 20

    # GOLES Y RESULTADO
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x0, y, "GOLES Y RESULTADO")
    y -= 8

    box_h = 50
    # 1er tiempo
    y -= box_h
    box_label_value(x0, y, usable_w, box_h, "Goles 1º tiempo (detalle)", datos_planilla.get("goles_primer_tiempo", ""))
    y -= 5
    # 2º tiempo
    y -= box_h
    box_label_value(x0, y, usable_w, box_h, "Goles 2º tiempo (detalle)", datos_planilla.get("goles_segundo_tiempo", ""))

    y -= 10
    row_h = 26
    col_w = usable_w / 2

    # Resultado equipos
    y -= row_h
    box_label_value(x0,       y, col_w, row_h, "Equipo A - Nombre", datos_planilla.get("resultado_equipo_a_nombre", ""))
    box_label_value(x0+col_w, y, col_w, row_h, "Equipo A - Goles",  datos_planilla.get("resultado_equipo_a_goles", ""))

    y -= row_h
    box_label_value(x0,       y, col_w, row_h, "Equipo B - Nombre", datos_planilla.get("resultado_equipo_b_nombre", ""))
    box_label_value(x0+col_w, y, col_w, row_h, "Equipo B - Goles",  datos_planilla.get("resultado_equipo_b_goles", ""))

    y -= 20

    # DIRECTOR Y ÁRBITROS
    if y < 150:
        c.showPage()
        width, height = A4
        x0 = margin
        x1 = width - margin
        usable_w = x1 - x0
        y = height - 40

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x0, y, "DIRECTOR DE TURNO Y ÁRBITROS")
    y -= 8

    row_h = 26
    col_w = usable_w / 2

    y -= row_h
    box_label_value(x0,       y, col_w, row_h, "Director de turno", datos_planilla.get("director_turno", ""))
    box_label_value(x0+col_w, y, col_w, row_h, "Árbitro",           datos_planilla.get("arbitro", ""))

    y -= row_h
    box_label_value(x0,       y, col_w, row_h, "Asistente 1", datos_planilla.get("asistente_1", ""))
    box_label_value(x0+col_w, y, col_w, row_h, "Asistente 2", datos_planilla.get("asistente_2", ""))

    y -= 20

    # --------- PÁGINA 2: EVENTOS + OBS/FIRMAS ---------
    if y < 200:
        c.showPage()
        width, height = A4
        x0 = margin
        x1 = width - margin
        usable_w = x1 - x0
        y = height - 40

    # Eventos equipo A
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x0, y, "EVENTOS DEL PARTIDO - EQUIPO A")
    y -= 14

    box_h = 40
    y -= box_h
    box_label_value(x0, y, usable_w, box_h, "Nombre equipo", datos_planilla.get("equipo_a_eventos_nombre", ""))
    y -= 5

    for label, key in [
        ("Cambios - ENTRAN", "equipo_a_cambios_entran"),
        ("Cambios - SALEN",  "equipo_a_cambios_salen"),
        ("Tarjetas amarillas", "equipo_a_tarjetas_amarillas"),
        ("Expulsados",         "equipo_a_expulsados"),
    ]:
        box_h = 40
        y -= box_h
        box_label_value(x0, y, usable_w, box_h, label, datos_planilla.get(key, ""))
        y -= 5

    # Eventos equipo B
    if y < 200:
        c.showPage()
        width, height = A4
        x0 = margin
        x1 = width - margin
        usable_w = x1 - x0
        y = height - 40

    # Bajamos un poco antes de escribir el título
    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x0, y, "EVENTOS DEL PARTIDO - EQUIPO B")
    y -= 24

    box_h = 40
    y -= box_h
    box_label_value(x0, y, usable_w, box_h, "Nombre equipo", datos_planilla.get("equipo_b_eventos_nombre", ""))
    y -= 5

    for label, key in [
        ("Cambios - ENTRAN", "equipo_b_cambios_entran"),
        ("Cambios - SALEN",  "equipo_b_cambios_salen"),
        ("Tarjetas amarillas", "equipo_b_tarjetas_amarillas"),
        ("Expulsados",         "equipo_b_expulsados"),
    ]:
        box_h = 40
        y -= box_h
        box_label_value(x0, y, usable_w, box_h, label, datos_planilla.get(key, ""))
        y -= 5

    # Observaciones y firmas
    if y < 160:
        c.showPage()
        width, height = A4
        x0 = margin
        x1 = width - margin
        usable_w = x1 - x0
        y = height - 40

    # Bajamos un poco después del último recuadro de expulsados
    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x0, y, "OBSERVACIONES Y FIRMAS")
    y -= 24

    box_h = 60
    y -= box_h
    box_label_value(x0, y, usable_w, box_h, "Observaciones", datos_planilla.get("observaciones", ""))
    y -= 10

    row_h = 40   # un poco más alto para que quepa mejor la firma
    col_w = usable_w / 2

    # Director y árbitro
    y -= row_h
    box_label_value(x0,       y, col_w, row_h, "Firma director de turno", datos_planilla.get("firma_director_turno", ""))
    box_label_value(x0+col_w, y, col_w, row_h, "Firma árbitro",           datos_planilla.get("firma_arbitro", ""))

    draw_signature_image(
        datos_planilla.get("firma_director_turno_img"),
        x0, y, col_w, row_h
    )
    draw_signature_image(
        datos_planilla.get("firma_arbitro_img"),
        x0 + col_w, y, col_w, row_h
    )

    # Asistentes
    y -= row_h
    box_label_value(x0,       y, col_w, row_h, "Firma asistente 1", datos_planilla.get("firma_asistente_1", ""))
    box_label_value(x0+col_w, y, col_w, row_h, "Firma asistente 2", datos_planilla.get("firma_asistente_2", ""))

    draw_signature_image(
        datos_planilla.get("firma_asistente_1_img"),
        x0, y, col_w, row_h
    )
    draw_signature_image(
        datos_planilla.get("firma_asistente_2_img"),
        x0 + col_w, y, col_w, row_h
    )

    # Cerramos PDF
    c.save()
    buffer.seek(0)

    fecha_descarga = datetime.now().strftime("%d_%m_%Y")
    nombre_archivo = f"copaUC_{fecha_descarga}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype="application/pdf"
    )



# --------- PLANILLA CAMPEONATO ---------
@app.route("/planilla_campeonato", methods=["GET", "POST"])
def planilla_campeonato():
    mensaje = None

    if request.method == "POST":
        datos_planilla = request.form.to_dict()
        session["ultima_planilla_campeonato"] = datos_planilla
        mensaje = "Planilla campeonato guardada (solo en memoria por ahora)."

        return render_template(
            "planilla_campeonato.html",
            mensaje=mensaje,
            datos=datos_planilla,
            license_active=license_is_active(),
            license_status=get_license_status_text()
        )

    datos_planilla = session.get("ultima_planilla_campeonato")

    return render_template(
        "planilla_campeonato.html",
        datos=datos_planilla,
        license_active=license_is_active(),
        license_status=get_license_status_text()
    )


@app.route("/descargar_campeonato", methods=["GET", "POST"])
def descargar_campeonato():
    if request.method == "POST":
        datos_planilla = request.form.to_dict()
    else:
        datos_planilla = session.get("ultima_planilla_campeonato") or {}

    if not datos_planilla:
        return redirect(url_for("planilla_campeonato"))

    if not license_is_active():
        return redirect(url_for("activar", next="planilla_campeonato"))

    session["ultima_planilla_campeonato"] = datos_planilla
    return generar_pdf_campeonato(datos_planilla)


def generar_pdf_campeonato(datos_planilla):
    """Genera PDF para la planilla tipo campeonato."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader, simpleSplit

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin = 24
    x0 = margin
    x1 = width - margin
    usable_w = x1 - x0
    y_top = height - margin

    def val(key):
        return str(datos_planilla.get(key, "") or "")

    def draw_text(x, y, text, size=6, bold=False, max_width=None):
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)

        if max_width:
            lines = simpleSplit(str(text), font, size, max_width)
            yy = y
            for line in lines[:2]:
                c.drawString(x, yy, line)
                yy -= size + 1
        else:
            c.drawString(x, y, str(text))

    def draw_center(x, y, w, text, size=6, bold=False):
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawCentredString(x + w / 2, y, str(text))

    def rect(x, y, w, h, fill=0):
        c.rect(x, y, w, h, stroke=1, fill=fill)

    def label_box(x, y, w, h, label, value="", size_label=5.5, size_value=7):
        rect(x, y, w, h)

        if label:
            draw_text(x + 2, y + h - 7, label, size_label, True)

        if value:
            draw_text(x + 2, y + 3, value, size_value, False, w - 4)

    def draw_bar(x, y, w, h, text):
        c.setFillGray(0.18)
        c.rect(x, y, w, h, stroke=1, fill=1)

        c.setFillGray(1)
        draw_center(x, y + 3, w, text, 6, True)

        c.setFillGray(0)

    def draw_signature_image(data_url, x, y, w, h):
        if not data_url:
            return

        try:
            b64data = data_url.split(",", 1)[1] if "," in data_url else data_url
            img_bytes = base64.b64decode(b64data)
            img = ImageReader(BytesIO(img_bytes))
            img_w, img_h = img.getSize()

            max_w = w - 10
            max_h = h - 10
            scale = min(max_w / img_w, max_h / img_h)

            draw_w = img_w * scale
            draw_h = img_h * scale

            c.drawImage(
                img,
                x + (w - draw_w) / 2,
                y + (h - draw_h) / 2,
                width=draw_w,
                height=draw_h,
                mask="auto"
            )
        except Exception:
            pass

    def draw_small_cell_text(x, y, w, h, text, size=4.8):
        if text:
            draw_text(x + 1.4, y + h / 2 - 1.8, text, size, False, w - 2)

    # Marco exterior
    rect(x0, 38, usable_w, height - 62)

    # =========================
    # ENCABEZADO
    # =========================
    header_h = 70

    logo_path = os.path.join(app.root_path, "static", "ldes.jpg")

    logo_box_x = x0 + 16
    logo_box_y = y_top - 58
    logo_box_w = 78
    logo_box_h = 52

    rect(logo_box_x, logo_box_y, logo_box_w, logo_box_h)

    if os.path.exists(logo_path):
        try:
            logo = ImageReader(logo_path)

            # Logo centrado dentro de su caja
            draw_logo_size = 46
            c.drawImage(
                logo,
                logo_box_x + (logo_box_w - draw_logo_size) / 2,
                logo_box_y + (logo_box_h - draw_logo_size) / 2,
                width=draw_logo_size,
                height=draw_logo_size,
                mask="auto"
            )
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(width / 2, y_top - 38, "PLANILLA DE FUTBOL CAMPEONATO LDES")

    # =========================
    # DATOS PARTIDO
    # =========================
    y = y_top - header_h
    row_h = 14

    label_box(x0, y, usable_w * 0.22, row_h, "Fecha:", val("fecha"), 5, 6)
    label_box(x0 + usable_w * 0.22, y, usable_w * 0.18, row_h, "Hora:", val("hora"), 5, 6)
    label_box(x0 + usable_w * 0.40, y, usable_w * 0.60, row_h, "Estadio:", val("estadio"), 5, 6)

    # =========================
    # ÁRBITROS Y OFICIALES
    # =========================
    y -= 70
    section_h = 70

    rect(x0, y, usable_w, section_h)
    draw_bar(x0, y + section_h - 12, usable_w, 12, "ÁRBITROS Y OFICIALES DEL PARTIDO")

    half_w = usable_w / 2
    off_y = y
    off_h = section_h - 12

    left_fields = [
        ("Árbitro:", "arbitro"),
        ("Árbitro Asistente 1:", "asistente_1"),
        ("Árbitro Asistente 2:", "asistente_2"),
        ("Cuarto Árbitro:", "cuarto_arbitro"),
        ("Asesor de Árbitros:", "asesor_arbitros"),
    ]

    right_fields = [
        ("Director de Turno:", "director_turno"),
        ("Jefe de Seguridad (Club local):", "jefe_seguridad"),
        ("Encargado Recinto:", "encargado_recinto"),
        ("Ciudad:", "ciudad"),
    ]

    line_h = off_h / 5

    for i, (label, key) in enumerate(left_fields):
        yy = off_y + off_h - (i + 1) * line_h
        label_box(x0, yy, half_w, line_h, label, val(key), 5, 6)

    for i in range(5):
        label, key = right_fields[i] if i < len(right_fields) else ("", "")
        yy = off_y + off_h - (i + 1) * line_h
        label_box(x0 + half_w, yy, half_w, line_h, label, val(key), 5, 6)

    # =========================
    # JUGADORES LOCAL / VISITA
    # =========================
    y -= 8
    players_top = y

    team_gap = 10
    team_w = (usable_w - team_gap) / 2

    def draw_team_players(x, y_top_team, prefix, title):
        """
        Dibuja equipo completo:
        - Nombre equipo
        - Titulares
        - Suplentes
        - Sustituciones con 6 filas

        Devuelve el punto inferior real usado por la tabla.
        """

        row_h = 11

        # Alto real aproximado considerando 6 sustituciones
        table_h = 352
        bottom = y_top_team - table_h

        rect(x, bottom, team_w, table_h)

        current_y = y_top_team - 14
        label_box(x, current_y, team_w, 14, title + ":", val(f"equipo_{prefix}"), 5, 6.2)

        # Barra jugadores
        current_y -= 12
        draw_bar(x, current_y, team_w, 12, "Jugadores")

        cols = [
            ("N°", 0.09),
            ("Nombre", 0.30),
            ("Apellidos", 0.31),
            ("G", 0.055),
            ("A/C", 0.06),
            ("TA", 0.06),
            ("TR", 0.06),
        ]

        col_widths = [team_w * frac for _, frac in cols]
        diff = team_w - sum(col_widths)
        col_widths[-1] += diff

        def draw_header_row(y_row):
            xx = x
            for (label, _), cw in zip(cols, col_widths):
                rect(xx, y_row, cw, 12)
                draw_center(xx, y_row + 3.2, cw, label, 4.8, True)
                xx += cw

        draw_header_row(current_y - 12)
        current_y -= 24

        # Titulares
        for i in range(1, 12):
            xx = x
            keys = [
                f"{prefix}_titular_num_{i}",
                f"{prefix}_titular_nombre_{i}",
                f"{prefix}_titular_apellido_{i}",
                f"{prefix}_titular_g_{i}",
                f"{prefix}_titular_ac_{i}",
                f"{prefix}_titular_ta_{i}",
                f"{prefix}_titular_tr_{i}",
            ]

            for key, cw in zip(keys, col_widths):
                rect(xx, current_y, cw, row_h)
                draw_small_cell_text(xx, current_y, cw, row_h, val(key))
                xx += cw

            current_y -= row_h

        # Suplentes
        draw_bar(x, current_y, team_w, 12, "Suplentes")
        current_y -= 12

        for i in range(1, 8):
            xx = x
            keys = [
                f"{prefix}_suplente_num_{i}",
                f"{prefix}_suplente_nombre_{i}",
                f"{prefix}_suplente_apellido_{i}",
                f"{prefix}_suplente_g_{i}",
                f"{prefix}_suplente_ac_{i}",
                f"{prefix}_suplente_ta_{i}",
                f"{prefix}_suplente_tr_{i}",
            ]

            for key, cw in zip(keys, col_widths):
                rect(xx, current_y, cw, row_h)
                draw_small_cell_text(xx, current_y, cw, row_h, val(key))
                xx += cw

            current_y -= row_h

        # Sustituciones
        draw_bar(x, current_y, team_w, 12, "SUSTITUCIONES")
        current_y -= 12

        sub_cols = [
            team_w * 0.38,
            team_w * 0.38,
            team_w * 0.24,
        ]

        sub_labels = ["Sale", "Entra", "Min."]

        xx = x
        for label, cw in zip(sub_labels, sub_cols):
            rect(xx, current_y, cw, row_h)
            draw_center(xx, current_y + 3.2, cw, label, 4.8, True)
            xx += cw

        current_y -= row_h

        for i in range(1, 7):
            xx = x
            keys = [
                f"{prefix}_sub_sale_{i}",
                f"{prefix}_sub_entra_{i}",
                f"{prefix}_sub_min_{i}",
            ]

            for key, cw in zip(keys, sub_cols):
                rect(xx, current_y, cw, row_h)
                draw_small_cell_text(xx, current_y, cw, row_h, val(key))
                xx += cw

            current_y -= row_h

        # Retornamos el punto real más bajo usado, no el antiguo bottom fijo.
        return min(bottom, current_y)

    local_bottom = draw_team_players(x0, players_top, "local", "LOCAL")
    visita_bottom = draw_team_players(x0 + team_w + team_gap, players_top, "visita", "VISITA")

    y = min(local_bottom, visita_bottom) - 8

    # =========================
    # LEYENDA
    # =========================
    draw_center(
        x0,
        y,
        usable_w,
        "T: Titular | S: Suplente | A: Arquero | C: Capitán | J: Juvenil | E: Extranjero",
        5.6,
        False
    )

    y -= 28

    # =========================
    # FIRMAS DT
    # =========================
    sig_w = usable_w / 2 - 26
    sig_h = 32
    sig_y = y

    line_y = sig_y + sig_h - 6

    c.line(x0 + 20, line_y, x0 + 20 + sig_w, line_y)
    c.line(x0 + usable_w / 2 + 20, line_y, x0 + usable_w / 2 + 20 + sig_w, line_y)

    draw_signature_image(val("firma_dt_local_img"), x0 + 20, sig_y + 8, sig_w, 24)
    draw_signature_image(val("firma_dt_visita_img"), x0 + usable_w / 2 + 20, sig_y + 8, sig_w, 24)

    draw_center(x0 + 20, sig_y + 4, sig_w, "Firma - Director Técnico", 6)
    draw_center(x0 + usable_w / 2 + 20, sig_y + 4, sig_w, "Firma - Director Técnico", 6)

    y -= 26

    # =========================
    # NOTA
    # =========================
    note_h = 20
    rect(x0, y, usable_w, note_h)

    draw_text(
        x0 + 3,
        y + 11,
        "NOTA: El Director Técnico y el Director de Turno declaran se hacen responsables que la información entregada es fidedigna y se ajusta a las Bases del Campeonato.",
        5.2,
        False,
        usable_w - 6
    )

    draw_center(
        x0,
        y + 2,
        usable_w,
        "Esta planilla deberá ser completada con letra imprenta legible.",
        5.2,
        True
    )

    # =========================
    # CUERPO TÉCNICO
    # =========================
    y -= 90

    ct_h = 86
    ct_w = (usable_w - team_gap) / 2

    def draw_ct(x, y, prefix, title):
        rect(x, y, ct_w, ct_h)
        draw_bar(x, y + ct_h - 13, ct_w, 13, title)

        row_h_ct = (ct_h - 13) / 5

        fields = [
            ("Director técnico", f"ct_{prefix}_dt"),
            ("Entrenador asistente", f"ct_{prefix}_asistente"),
            ("Preparador físico", f"ct_{prefix}_pf"),
            ("Otro", f"ct_{prefix}_otro1"),
            ("Otro", f"ct_{prefix}_otro2"),
        ]

        for i, (label, key) in enumerate(fields):
            yy = y + ct_h - 13 - (i + 1) * row_h_ct

            label_box(x, yy, ct_w * 0.48, row_h_ct, "", val(key), 4.5, 5.2)
            label_box(x + ct_w * 0.48, yy, ct_w * 0.52, row_h_ct, label, "", 4.8, 5.2)

    draw_ct(x0, y, "local", "CUERPO TÉCNICO LOCAL")
    draw_ct(x0 + ct_w + team_gap, y, "visita", "CUERPO TÉCNICO VISITA")

    # =========================
    # RESULTADO
    # =========================
    y -= 16

    result_h = 14

    label_box(x0, y, usable_w * 0.18, result_h, "RESULTADO", val("resultado_local"), 5, 6)
    label_box(x0 + usable_w * 0.18, y, usable_w * 0.32, result_h, "LOCAL", val("equipo_local"), 5, 6)
    label_box(x0 + usable_w * 0.50, y, usable_w * 0.18, result_h, "RESULTADO", val("resultado_visita"), 5, 6)
    label_box(x0 + usable_w * 0.68, y, usable_w * 0.32, result_h, "VISITA", val("equipo_visita"), 5, 6)

    # =========================
    # OBSERVACIONES
    # =========================
    y -= 55

    obs_h = 50
    label_box(x0, y, usable_w, obs_h, "OBSERVACIONES:", val("observaciones"), 5, 6)

    # Cerrar PDF
    c.save()
    buffer.seek(0)

    fecha_descarga = datetime.now().strftime("%d_%m_%Y")
    nombre_archivo = f"FUTBOL_LDES_{fecha_descarga}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=nombre_archivo,
        mimetype="application/pdf"
    )


# Cerrar sesión
@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("inicio"))


if __name__ == "__main__":
    app.run(debug=True)
    # Para exponer en red local:
    # app.run(host="0.0.0.0", port=5000, debug=True)
