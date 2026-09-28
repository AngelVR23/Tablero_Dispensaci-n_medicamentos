# Tablero de dispensación de medicamentos (EPS) · Dash + SQL (SQLite)
# Instalar: python -m pip install -r requirements.txt   
import sqlite3
from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

DB_PATH = Path(__file__).parent / "medicamentos.db"

# ---------------------------------------------------------------------------
# Capa de datos: cada gráfica ejecuta su propia consulta SQL agregada.
# La vista temporal "d" normaliza campos y RECLASIFICA el grupo farmacológico:
# en 2020 la columna grupo_fco_economico viene vacía; se completa con el grupo
# que el mismo medicamento (descripcion) tiene en los registros que sí lo traen.
# ---------------------------------------------------------------------------
VISTA = """
CREATE TEMP VIEW d AS
SELECT t.*,
       CAST(strftime('%Y', t.fecha_entrega) AS INTEGER) AS anio,
       CAST(strftime('%m', t.fecha_entrega) AS INTEGER) AS mes,
       strftime('%Y-%m', t.fecha_entrega)               AS ym,
       COALESCE(NULLIF(t.grupo_fco_economico, ''), m.g, 'SIN CLASIFICAR') AS grupo,
       CASE WHEN t.regional_caf IN ('0', '') OR t.regional_caf IS NULL
            THEN 'SIN REGISTRO' ELSE t.regional_caf END AS reg,
       CASE WHEN t.departamento_caf IN ('0', '') OR t.departamento_caf IS NULL
            THEN 'SIN REGISTRO' ELSE t.departamento_caf END AS depto,
       CASE WHEN t.municipio_caf IN ('0', '') OR t.municipio_caf IS NULL
            THEN 'SIN REGISTRO' ELSE t.municipio_caf END AS muni,
       CASE WHEN t.tipo_entrega IS NULL OR t.tipo_entrega = ''
            THEN 'SIN REGISTRO' ELSE t.tipo_entrega END AS entrega
FROM dispensacion t
LEFT JOIN (SELECT descripcion, MAX(grupo_fco_economico) AS g
           FROM dispensacion WHERE grupo_fco_economico <> ''
           GROUP BY descripcion) m ON m.descripcion = t.descripcion;
"""


def consultar(query: str, params=None) -> pd.DataFrame:
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute(VISTA)
        return pd.read_sql_query(query, con, params=params or [])
    finally:
        con.close()


def donde(anios=None, meses=None, grupos=None, regs=None, extra=None):
    """Arma el WHERE con parámetros (?) a partir de los filtros. Lista vacía = todos."""
    conds, params = [], []
    for col, vals in (("anio", anios), ("mes", meses), ("grupo", grupos), ("reg", regs)):
        if vals:
            conds.append(f"{col} IN ({','.join('?' * len(vals))})")
            params += list(vals)
    if extra:
        conds.append(extra)
    return (" AND ".join(conds) or "1=1"), params


MESES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio",
         8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
ANIOS = consultar("SELECT DISTINCT anio FROM d ORDER BY anio")["anio"].tolist()
GRUPOS = consultar("SELECT DISTINCT grupo FROM d ORDER BY grupo")["grupo"].tolist()
REGIONALES = consultar("SELECT DISTINCT reg FROM d ORDER BY reg")["reg"].tolist()

# Coordenadas aproximadas de los municipios (para el mapa de calor de gasto)
COORDS = {
    "CARTAGENA": (10.391, -75.479), "VALLEDUPAR": (10.463, -73.253), "ARJONA": (10.257, -75.347),
    "TURBACO": (10.333, -75.415), "MARIALABAJA": (9.974, -75.297), "SAN CRISTOBAL": (10.391, -75.063),
    "TURBANA": (10.276, -75.443), "MOMPOX": (9.244, -74.428), "BARRANQUILLA": (10.964, -74.796),
    "PUEBLO NUEVO": (8.42, -75.52), "MAHATES": (10.233, -75.189), "SAMPUES": (9.183, -75.383),
    "SANTA ROSA": (10.447, -75.370), "SAN JUAN NEPOMUCENO": (9.954, -75.081), "VILLANUEVA": (10.446, -75.274),
    "SOPLAVIENTO": (10.395, -75.142), "SINCE": (9.305, -75.398), "SINCELEJO": (9.305, -75.398),
    "TOLU": (9.523, -75.581), "CALAMAR": (10.251, -74.914), "HATILLO DE LOBA": (8.948, -74.077),
    "SAN JACINTO": (9.83, -75.12), "BAYUNCA": (10.5, -75.42), "SOLEDAD": (10.918, -74.765),
    "ZAMBRANO": (9.744, -74.819), "CERETE": (8.885, -75.795), "SAN BERNARDO DEL VIENTO": (9.355, -75.953),
    "EL CARMEN DE BOLIVAR": (9.719, -75.121), "ARROYO HONDO": (10.25, -75.019), "EL PENON": (8.98, -73.94),
    "MAGANGUE": (9.242, -74.755), "MONTERIA": (8.75, -75.881), "COROZAL": (9.318, -75.293),
    "LORICA": (9.239, -75.816), "CIENAGA": (11.007, -74.247), "SABANAGRANDE": (10.789, -74.758),
    "OVEJAS": (9.529, -75.229), "BOGOTA": (4.711, -74.072),
}

# ---------------------------------------------------------------------------
# Formato y estilo
# ---------------------------------------------------------------------------
C = {"indigo": "#4F46E5", "cyan": "#06B6D4", "rosa": "#EC4899", "ambar": "#F59E0B",
     "verde": "#10B981", "violeta": "#8B5CF6", "gris": "#64748B", "noche": "#0F172A"}
SECUENCIA = [C["indigo"], C["cyan"], C["rosa"], C["ambar"], C["verde"], C["violeta"]]


def pesos(v):
    v = 0 if v is None or pd.isna(v) else v
    return "$ " + f"{v:,.0f}".replace(",", ".")


def millones(v):
    v = 0 if v is None or pd.isna(v) else v
    return "$ " + f"{v / 1e6:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".") + " M"


def entero(v):
    v = 0 if v is None or pd.isna(v) else v
    return f"{v:,.0f}".replace(",", ".")


def estilo(fig):
    fig.update_layout(
        template="plotly_white", font=dict(family="Inter, sans-serif", size=12, color="#334155"),
        margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.18), hoverlabel=dict(font_size=12),
    )
    return fig


def vacia(msg="Sin datos para los filtros seleccionados"):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font=dict(size=14, color=C["gris"]))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return estilo(fig)


def corto(s, n=48):
    return s if len(s) <= n else s[: n - 1] + "…"


# ---------------------------------------------------------------------------
# Componentes de la interfaz
# ---------------------------------------------------------------------------
ESTILOS = """
body{font-family:'Inter',sans-serif;background:#F4F6FB}
.encabezado{background:linear-gradient(120deg,#0F172A 0%,#312E81 55%,#0891B2 100%);color:#fff;border-radius:20px;padding:1.6rem 2rem;margin:1rem 0}
.encabezado h2{font-weight:800;margin:0}.encabezado p{margin:.2rem 0 0;color:#CBD5E1}
.panel{background:#fff;border-radius:16px;padding:1rem 1.2rem;box-shadow:0 4px 18px rgba(15,23,42,.07);margin-bottom:1rem}
.panel label{font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:#475569}
.kpi{border-radius:18px;color:#fff;padding:1.1rem 1.3rem;min-height:118px;box-shadow:0 6px 18px rgba(15,23,42,.15)}
.kpi .t{font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;opacity:.9}
.kpi .v{font-size:1.65rem;font-weight:800;line-height:1.2;margin-top:.2rem}
.kpi .s{font-size:.75rem;opacity:.85;margin-top:.2rem}
.seccion{font-weight:700;color:#0F172A;margin:1.4rem 0 .7rem;border-left:5px solid #4F46E5;padding-left:.7rem}
.desc{color:#64748B;font-size:.82rem;margin-bottom:.4rem}
.scroll-x{overflow-x:auto;overflow-y:hidden}.scroll-xy{overflow:auto;max-height:420px}
.scroll-xy th{position:sticky;top:0;background:#EEF2FF;white-space:nowrap}.scroll-xy td{white-space:nowrap}
.nav-tabs .nav-link{font-weight:600;color:#475569}.nav-tabs .nav-link.active{color:#4F46E5}
.respuesta{background:#EEF2FF;border-left:5px solid #4F46E5;border-radius:12px;padding:.9rem 1.1rem;margin-bottom:.8rem}
"""

app = Dash(
    __name__, title="Dispensación de medicamentos · EPS", suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP,
                          "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap"],
)
server = app.server  # necesario para desplegar con gunicorn
app.index_string = app.index_string.replace("</head>", f"<style>{ESTILOS}</style></head>")


def kpi(titulo, id_, c1, c2):
    return dbc.Col(html.Div([html.Div(titulo, className="t"), html.Div(id=id_, className="v"),
                             html.Div(id=id_ + "-sub", className="s")], className="kpi",
                            style={"background": f"linear-gradient(135deg,{c1},{c2})"}), md=3, sm=6, className="mb-3")


def caja(titulo, desc, gid, alto=380, minw=560, md=6):
    """Tarjeta con gráfica; si el contenido no cabe aparece barra de desplazamiento horizontal."""
    return dbc.Col(html.Div([
        html.H6(titulo, className="fw-bold mb-0"), html.P(desc, className="desc"),
        html.Div(dcc.Graph(id=gid, style={"height": f"{alto}px", "minWidth": f"{minw}px"},
                           config={"displaylogo": False}), className="scroll-x"),
    ], className="panel h-100"), md=md, className="mb-3")


def drop(id_, etiqueta, opciones, md):
    return dbc.Col([html.Label(etiqueta), dcc.Dropdown(id=id_, options=opciones, multi=True, placeholder="Todos")], md=md)


filtros = html.Div(dbc.Row([
    drop("f-anio", "Año", [{"label": str(a), "value": a} for a in ANIOS], 2),
    drop("f-mes", "Mes", [{"label": n, "value": k} for k, n in MESES.items()], 3),
    drop("f-grupo", "Grupo farmacológico", GRUPOS, 4),
    drop("f-reg", "Regional CAF", REGIONALES, 3),
]), className="panel")

tab_general = [
    dbc.Row([kpi("Personas con dispensaciones", "k-pers", C["indigo"], C["violeta"]),
             kpi("Fórmulas distintas", "k-form", C["cyan"], C["indigo"]),
             kpi("Costo total", "k-costo", C["rosa"], C["violeta"]),
             kpi("Costo promedio por fórmula", "k-prom", C["ambar"], C["rosa"])], className="mt-2"),
    html.Div(id="nota-calidad", className="desc"),
    html.H5("Comportamiento en el tiempo", className="seccion"),
    dbc.Row([dbc.Col(html.Div([
        dbc.RadioItems(id="metrica", inline=True, value="costo", className="mb-2", options=[
            {"label": "Costo total", "value": "costo"}, {"label": "Personas", "value": "personas"},
            {"label": "Fórmulas", "value": "formulas"}]),
        html.Div(dcc.Graph(id="g-tiempo", style={"height": "380px", "minWidth": "700px"},
                           config={"displaylogo": False}), className="scroll-x")], className="panel"))]),
    html.H5("Concentración y cobertura", className="seccion"),
    dbc.Row([caja("Top 10 medicamentos por costo total", "Ordenados de mayor a menor; el nombre completo aparece al pasar el cursor.",
                  "g-top", 420, 700, 8),
             caja("Costo según plan de beneficios", "Participación PBS vs No PBS.", "g-pbs", 420, 380, 4)]),
    html.H5("Geografía y logística", className="seccion"),
    dbc.Row([caja("Costo por departamento de dispensación", "Departamento del punto de dispensación.", "g-depto", 380, 520),
             caja("Costo por tipo de entrega", "Costo anual y total de todos los años por modalidad.", "g-entrega", 380, 480)]),
    dbc.Row([caja("Mapa de calor del gasto por municipio", "Tamaño y color = costo total. Ubicaciones aproximadas; excluye registros sin municipio.",
                  "g-mapa", 480, 560, 7),
             caja("Costo por grupo farmacológico", "Área proporcional al costo total de cada grupo.", "g-grupo", 480, 480, 5)]),
    html.H5("Detalle de dispensaciones", className="seccion"),
    html.Div([html.P("Últimos 200 registros según los filtros. Desplázate para ver todas las columnas.", className="desc"),
              html.Div(id="tabla", className="scroll-xy")], className="panel"),
]

tab_antidiabeticos = [
    html.H5("Análisis del grupo ANTIDIABÉTICOS", className="seccion"),
    html.P("Esta sección usa todo el periodo (ignora los filtros de año, mes y grupo) y respeta la regional CAF.", className="desc"),
    dbc.Row([kpi("Costo total del grupo", "a-costo", C["indigo"], C["violeta"]),
             kpi("Fórmula promedio", "a-prom", C["ambar"], C["rosa"]),
             kpi("Variación de costo", "a-var", C["cyan"], C["indigo"]),
             kpi("Medicamento más costoso", "a-top", C["rosa"], C["violeta"])]),
    html.Div(id="a-respuestas"),
    dbc.Row([caja("Costo mensual y costo promedio por fórmula", "Barras: costo total del mes. Línea: costo promedio por fórmula.", "a-tiempo", 400, 640, 8),
             caja("Insulinas vs antidiabéticos orales", "Participación en el costo del grupo.", "a-tipo", 400, 360, 4)]),
    dbc.Row([caja("Medicamentos antidiabéticos más costosos", "Costo total acumulado.", "a-top10", 420, 700, 12)]),
    html.Div([html.H6("Precio unitario promedio por medicamento", className="fw-bold mb-0"),
              html.P("Costo ÷ unidades dispensadas. La variación compara 2021 contra 2020.", className="desc"),
              html.Div(id="a-tabla", className="scroll-xy")], className="panel"),
]

app.layout = dbc.Container([
    html.Div([html.H2("Tablero de dispensación de medicamentos"),
              html.P("Periodo 2020 – 2021 · Costos en pesos colombianos (COP)")], className="encabezado"),
    filtros,
    dbc.Tabs([dbc.Tab(tab_general, label="Resumen general", tab_id="t1"),
              dbc.Tab(tab_antidiabeticos, label="Antidiabéticos", tab_id="t2")], active_tab="t1"),
    html.Div(className="pb-4"),
], fluid=True)


# ---------------------------------------------------------------------------
# Callback 1: resumen general
# ---------------------------------------------------------------------------
@app.callback(
    [Output(i, "children") for i in ("k-pers", "k-form", "k-costo", "k-prom")]
    + [Output("k-costo-sub", "children"), Output("k-prom-sub", "children"), Output("nota-calidad", "children")]
    + [Output(i, "figure") for i in ("g-tiempo", "g-top", "g-pbs", "g-depto", "g-entrega", "g-mapa", "g-grupo")]
    + [Output("tabla", "children")],
    Input("f-anio", "value"), Input("f-mes", "value"), Input("f-grupo", "value"),
    Input("f-reg", "value"), Input("metrica", "value"),
)
def actualizar(anios, meses, grupos, regs, metrica):
    w, p = donde(anios, meses, grupos, regs)
    k = consultar(f"""SELECT COUNT(DISTINCT id) personas, COUNT(DISTINCT formula) formulas,
                      COALESCE(SUM(costo_total),0) costo, COUNT(*) filas FROM d WHERE {w}""", p).iloc[0]
    if k["filas"] == 0:
        v = vacia()
        return ("0", "0", pesos(0), pesos(0), "", "", "", v, v, v, v, v, v, v, "Sin registros.")
    prom = k["costo"] / k["formulas"] if k["formulas"] else 0

    # 4. Serie de tiempo (líneas con marcadores + media móvil de 3 meses)
    t = consultar(f"""SELECT ym, SUM(costo_total) costo, COUNT(DISTINCT id) personas,
                      COUNT(DISTINCT formula) formulas FROM d WHERE {w} GROUP BY ym ORDER BY ym""", p)
    et = {"costo": "Costo total ($)", "personas": "Personas", "formulas": "Fórmulas"}[metrica]
    g_t = go.Figure()
    g_t.add_scatter(x=t["ym"], y=t[metrica], mode="lines+markers", name=et, line=dict(color=C["indigo"], width=3),
                    marker=dict(size=8, color=C["cyan"], line=dict(width=2, color=C["indigo"])),
                    hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>")
    g_t.add_scatter(x=t["ym"], y=t[metrica].rolling(3, min_periods=1).mean(), mode="lines", name="Media móvil 3 meses",
                    line=dict(color=C["rosa"], dash="dash", width=2), hoverinfo="skip")
    g_t.update_yaxes(title=et, separatethousands=True, tickprefix="$ " if metrica == "costo" else "")
    g_t.update_xaxes(title="Mes de dispensación")
    g_t = estilo(g_t)

    # 5. Top 10 medicamentos
    top = consultar(f"""SELECT descripcion, SUM(costo_total) costo FROM d WHERE {w}
                        GROUP BY descripcion ORDER BY costo DESC LIMIT 10""", p).sort_values("costo")
    g_top = go.Figure(go.Bar(
        x=top["costo"], y=top["descripcion"].map(corto), orientation="h", customdata=top["descripcion"],
        text=top["costo"].map(millones), textposition="outside", cliponaxis=False,
        marker=dict(color=top["costo"], colorscale=[[0, C["cyan"]], [1, C["indigo"]]]),
        hovertemplate="%{customdata}<br>$ %{x:,.0f}<extra></extra>"))
    g_top.update_xaxes(title="Costo total ($)", separatethousands=True, range=[0, top["costo"].max() * 1.25])
    g_top = estilo(g_top)

    # 6. PBS vs No PBS (rosca con total al centro)
    pb = consultar(f"SELECT CASE WHEN pbs='SI' THEN 'PBS' ELSE 'No PBS' END pbs, SUM(costo_total) costo FROM d WHERE {w} GROUP BY 1", p)
    g_pbs = go.Figure(go.Pie(labels=pb["pbs"], values=pb["costo"], hole=0.62, sort=False,
                             marker=dict(colors=[C["cyan"] if x == "PBS" else C["rosa"] for x in pb["pbs"]]),
                             textinfo="percent", hovertemplate="%{label}<br>$ %{value:,.0f}<extra></extra>"))
    g_pbs.add_annotation(text=f"<b>{millones(k['costo'])}</b><br>total", showarrow=False, font=dict(size=15))
    g_pbs = estilo(g_pbs)

    # 7. Departamento
    dp = consultar(f"SELECT depto, SUM(costo_total) costo FROM d WHERE {w} GROUP BY depto ORDER BY costo DESC", p)
    g_dp = go.Figure(go.Bar(x=dp["depto"], y=dp["costo"], text=dp["costo"].map(millones), textposition="outside",
                            cliponaxis=False, marker_color=[C["gris"] if x == "SIN REGISTRO" else C["indigo"] for x in dp["depto"]],
                            hovertemplate="%{x}<br>$ %{y:,.0f}<extra></extra>"))
    g_dp.update_yaxes(title="Costo total ($)", separatethousands=True, range=[0, dp["costo"].max() * 1.2])
    g_dp = estilo(g_dp)
    sin_reg = dp.loc[dp["depto"] == "SIN REGISTRO", "costo"].sum() / k["costo"] * 100 if k["costo"] else 0
    nota = (f"Nota de calidad de datos: el {sin_reg:.1f}% del costo filtrado no tiene departamento/municipio/regional "
            "registrado (código 0 en la base). Aparece como «SIN REGISTRO» en las barras y se excluye del mapa.")

    # 8. Tipo de entrega por año y total de todos los años
    en = consultar(f"""SELECT entrega, CAST(anio AS TEXT) anio, SUM(costo_total) costo FROM d WHERE {w}
                       GROUP BY entrega, anio ORDER BY anio""", p)
    w_total, p_total = donde(meses=meses, grupos=grupos, regs=regs)
    en_total = consultar(f"SELECT entrega, SUM(costo_total) costo FROM d WHERE {w_total} GROUP BY entrega", p_total)
    etiqueta_total = f"Total {ANIOS[0]}-{ANIOS[-1]}"
    en_total["anio"] = etiqueta_total
    en = pd.concat([en, en_total], ignore_index=True)
    colores_entrega = {str(anio): SECUENCIA[i % len(SECUENCIA)] for i, anio in enumerate(ANIOS)}
    colores_entrega[etiqueta_total] = C["noche"]
    g_en = px.bar(en, x="entrega", y="costo", color="anio", barmode="group", color_discrete_map=colores_entrega,
                  labels={"entrega": "", "costo": "Costo total ($)", "anio": "Año"})
    g_en.update_yaxes(separatethousands=True)
    g_en = estilo(g_en)

    # Mapa de calor por municipio
    mu = consultar(f"SELECT muni, SUM(costo_total) costo FROM d WHERE {w} AND muni <> 'SIN REGISTRO' GROUP BY muni", p)
    mu["lat"] = mu["muni"].map(lambda m: COORDS.get(m, (None, None))[0])
    mu["lon"] = mu["muni"].map(lambda m: COORDS.get(m, (None, None))[1])
    mu = mu.dropna(subset=["lat"])
    if mu.empty:
        g_mapa = vacia("Sin municipios con ubicación")
    else:
        mu["tam"] = mu["costo"] ** 0.5
        args = dict(lat="lat", lon="lon", size="tam", color="costo", hover_name="muni", size_max=48, zoom=5.3,
                    center=dict(lat=9.6, lon=-75.0), color_continuous_scale="YlOrRd", hover_data={"tam": False, "lat": False, "lon": False, "costo": ":,.0f"})
        if hasattr(px, "scatter_map"):
            g_mapa = px.scatter_map(mu, map_style="carto-positron", **args)
        else:
            g_mapa = px.scatter_mapbox(mu, mapbox_style="carto-positron", **args)
        g_mapa.update_layout(coloraxis_colorbar=dict(title="Costo ($)", len=0.7))
        g_mapa = estilo(g_mapa)

    # Grupo farmacológico (treemap)
    gr = consultar(f"SELECT grupo, SUM(costo_total) costo FROM d WHERE {w} GROUP BY grupo HAVING costo > 0", p)
    g_gr = px.treemap(gr, path=[px.Constant("Total"), "grupo"], values="costo", color="costo",
                      color_continuous_scale=[C["cyan"], C["indigo"], C["rosa"]])
    g_gr.update_traces(hovertemplate="%{label}<br>$ %{value:,.0f}<extra></extra>")
    g_gr.update_layout(coloraxis_showscale=False)
    g_gr = estilo(g_gr)

    # Tabla de detalle
    det = consultar(f"""SELECT fecha_entrega AS Fecha, descripcion AS Medicamento, grupo AS Grupo, reg AS Regional,
                        muni AS Municipio, pbs AS PBS, entrega AS Entrega, cantidad AS Cantidad,
                        costo_total AS Costo FROM d WHERE {w} ORDER BY fecha_entrega DESC LIMIT 200""", p)
    det["Costo"] = det["Costo"].map(pesos)
    tabla = dbc.Table.from_dataframe(det, striped=True, hover=True, size="sm", className="mb-0")

    return (entero(k["personas"]), entero(k["formulas"]), millones(k["costo"]), pesos(prom),
            f"{pesos(k['costo'])} · {entero(k['filas'])} registros", "Costo total ÷ fórmulas distintas", nota,
            g_t, g_top, g_pbs, g_dp, g_en, g_mapa, g_gr, tabla)


# ---------------------------------------------------------------------------
# Callback 2: análisis de ANTIDIABÉTICOS
# ---------------------------------------------------------------------------
@app.callback(
    [Output(i, "children") for i in ("a-costo", "a-prom", "a-var", "a-top", "a-respuestas", "a-tabla")]
    + [Output(i, "figure") for i in ("a-tiempo", "a-tipo", "a-top10")],
    Input("f-reg", "value"),
)
def antidiabeticos(regs):
    w, p = donde(regs=regs, extra="grupo = 'ANTIDIABETICOS'")
    m = consultar(f"""SELECT anio, mes, ym, SUM(costo_total) costo, COUNT(DISTINCT formula) formulas
                      FROM d WHERE {w} GROUP BY anio, mes, ym ORDER BY ym""", p)
    if m.empty:
        v = vacia()
        return "—", "—", "—", "—", "Sin datos para esta regional.", "", v, v, v
    m["prom"] = m["costo"] / m["formulas"]
    tot = consultar(f"SELECT SUM(costo_total) costo, COUNT(DISTINCT formula) f FROM d WHERE {w}", p).iloc[0]
    med = consultar(f"""SELECT descripcion, anio, SUM(costo_total) costo, SUM(cantidad) uds
                        FROM d WHERE {w} GROUP BY descripcion, anio""", p)

    # ¿Ha aumentado el costo? Se compara sobre los meses presentes en ambos años
    comunes = sorted(set(m[m.anio == ANIOS[0]].mes) & set(m[m.anio == ANIOS[-1]].mes))
    var_txt, resp_aum, prom_txt = "N/D", "No hay meses comparables entre 2020 y 2021.", ""
    if comunes:
        ph = ",".join("?" * len(comunes))
        an = consultar(f"""SELECT anio, SUM(costo_total) costo, COUNT(DISTINCT formula) f FROM d
                           WHERE {w} AND mes IN ({ph}) GROUP BY anio ORDER BY anio""", p + comunes).set_index("anio")
        if len(an) == 2:
            c0, c1 = an.loc[ANIOS[0], "costo"], an.loc[ANIOS[-1], "costo"]
            pr0, pr1 = c0 / an.loc[ANIOS[0], "f"], c1 / an.loc[ANIOS[-1], "f"]
            v_c, v_p = (c1 / c0 - 1) * 100, (pr1 / pr0 - 1) * 100
            rango = f"{MESES[comunes[0]]}–{MESES[comunes[-1]]}"
            var_txt = f"{v_c:+.1f}%"
            resp_aum = (f"**Sí, aumentó.** " if v_c > 0 else "**No, disminuyó.** ") + (
                f"Comparando {rango} de ambos años, el costo pasó de {millones(c0)} en 2020 a {millones(c1)} en 2021 ({v_c:+.1f}%). "
                f"El costo promedio por fórmula pasó de {pesos(pr0)} a {pesos(pr1)} ({v_p:+.1f}%).")
    top = med.groupby("descripcion")["costo"].sum().sort_values(ascending=False)
    prom_g = tot["costo"] / tot["f"]

    respuestas = html.Div([dcc.Markdown(t, className="respuesta") for t in (
        f"**1. ¿Su costo ha aumentado?** {resp_aum}",
        f"**2. ¿Cuál es el medicamento más costoso?** {top.index[0].title()}, con {pesos(top.iloc[0])} "
        f"({top.iloc[0] / tot['costo'] * 100:.1f}% del costo del grupo).",
        f"**3. ¿Cuál es el costo de una fórmula promedio?** {pesos(prom_g)} (costo total ÷ {entero(tot['f'])} fórmulas distintas).")])

    # Gráfica mensual: barras (costo) + línea (costo por fórmula)
    g_t = go.Figure()
    g_t.add_bar(x=m["ym"], y=m["costo"], name="Costo total", marker_color=C["indigo"], opacity=0.85,
                hovertemplate="%{x}<br>$ %{y:,.0f}<extra></extra>")
    g_t.add_scatter(x=m["ym"], y=m["prom"], name="Costo por fórmula", yaxis="y2", mode="lines+markers",
                    line=dict(color=C["rosa"], width=3), hovertemplate="%{x}<br>$ %{y:,.0f}<extra></extra>")
    g_t.update_layout(yaxis=dict(title="Costo total ($)", separatethousands=True),
                      yaxis2=dict(title="Costo por fórmula ($)", overlaying="y", side="right", separatethousands=True))
    g_t = estilo(g_t)

    # Insulinas vs orales
    ins = med.assign(tipo=med["descripcion"].map(lambda s: "Insulinas" if "INSULINA" in s else "Orales / otros"))
    ins = ins.groupby("tipo")["costo"].sum().reset_index()
    g_tipo = go.Figure(go.Pie(labels=ins["tipo"], values=ins["costo"], hole=0.6,
                              marker=dict(colors=[C["rosa"], C["cyan"]]), textinfo="percent",
                              hovertemplate="%{label}<br>$ %{value:,.0f}<extra></extra>"))
    g_tipo = estilo(g_tipo)

    # Top medicamentos
    t10 = top.head(10).sort_values().reset_index()
    g_top = go.Figure(go.Bar(x=t10["costo"], y=t10["descripcion"].map(corto), orientation="h", customdata=t10["descripcion"],
                             text=t10["costo"].map(millones), textposition="outside", cliponaxis=False,
                             marker=dict(color=t10["costo"], colorscale=[[0, C["cyan"]], [1, C["rosa"]]]),
                             hovertemplate="%{customdata}<br>$ %{x:,.0f}<extra></extra>"))
    g_top.update_xaxes(separatethousands=True, title="Costo total ($)", range=[0, t10["costo"].max() * 1.25])
    g_top = estilo(g_top)

    # Tabla de precios unitarios 2020 vs 2021
    pv = med.pivot_table(index="descripcion", columns="anio", values=["costo", "uds"], aggfunc="sum")
    tb = pd.DataFrame({"Medicamento": pv.index, "Costo total": pv["costo"].sum(axis=1).values,
                       "Unidades": pv["uds"].sum(axis=1).values})
    for a in (ANIOS[0], ANIOS[-1]):
        tb[f"Precio unit. {a}"] = (pv["costo"][a] / pv["uds"][a]).values if a in pv["costo"] else float("nan")
    tb["Variación"] = (tb[f"Precio unit. {ANIOS[-1]}"] / tb[f"Precio unit. {ANIOS[0]}"] - 1) * 100
    tb = tb.sort_values("Costo total", ascending=False).head(15)
    for c in ("Costo total", f"Precio unit. {ANIOS[0]}", f"Precio unit. {ANIOS[-1]}"):
        tb[c] = tb[c].map(lambda v: pesos(v) if pd.notna(v) else "—")
    tb["Unidades"] = tb["Unidades"].map(entero)
    tb["Variación"] = tb["Variación"].map(lambda v: f"{v:+.1f}%" if pd.notna(v) else "—")

    return (millones(tot["costo"]), pesos(prom_g), var_txt, corto(top.index[0].title(), 30), respuestas,
            dbc.Table.from_dataframe(tb, striped=True, hover=True, size="sm", className="mb-0"),
            g_t, g_tipo, g_top)


if __name__ == "__main__":
    app.run(debug=True)
