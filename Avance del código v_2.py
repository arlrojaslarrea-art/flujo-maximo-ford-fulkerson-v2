import os
import random
import tempfile
import networkx as nx

import streamlit as st
import streamlit.components.v1 as componentes
from pyvis.network import Network

# Configuración de página
st.set_page_config(
    page_title="Flujo máximo - Ford Fulkerson",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Algoritmo de Ford Fulkerson & Corte Mínimo")
st.markdown(
    "Aplicación interactiva: Resaltado en rojo del número de la arista que limita el flujo únicamente en su paso correspondiente."
)

# --- INICIALIZACIÓN DEL ESTADO ---
if "numero_nodos" not in st.session_state:
    st.session_state.numero_nodos = 8
if "aristas" not in st.session_state:
    st.session_state.aristas = []
if "historial" not in st.session_state:
    st.session_state.historial = []
if "paso_actual" not in st.session_state:
    st.session_state.paso_actual = 0
if "posiciones_nodos" not in st.session_state:
    st.session_state.posiciones_nodos = {}

# Captura de posiciones arrastradas manualmente (vía URL)
query_params = st.query_params
if "dragged_node" in query_params:
    try:
        node_id = int(query_params["dragged_node"])
        x_val = float(query_params["x"])
        y_val = float(query_params["y"])
        st.session_state.posiciones_nodos[node_id] = (x_val, y_val)
    except Exception:
        pass


# --- FUNCIONES AUXILIARES ---
def tiene_ciclos(num_nodos, aristas):
    """Verifica si el grafo contiene ciclos directos usando DFS."""
    grafo = nx.DiGraph()
    grafo.add_nodes_from(range(num_nodos))
    for u, v, c in aristas:
        grafo.add_edge(u, v)
    try:
        ciclos = list(nx.simple_cycles(grafo))
        return len(ciclos) > 0, ciclos
    except Exception:
        return False, []


def generar_dag_aleatorio(num_nodos, probabilidad_arista=0.35, cap_max=20):
    """Genera un grafo dirigido acíclico (DAG) aleatorio con capacidades."""
    aristas = []
    for i in range(num_nodos):
        for j in range(i + 1, num_nodos):
            if random.random() < probabilidad_arista:
                cap = random.randint(3, cap_max)
                aristas.append((i, j, cap))
    return aristas


def generar_posiciones_zigzag(num_nodos):
    """Genera posiciones en Zig-Zag alternando capas (Y=+120 y Y=-120)."""
    SEPARACION_X = 180
    ALTURA_Y = 120

    posiciones = {}
    for i in range(num_nodos):
        x = i * SEPARACION_X
        y = ALTURA_Y if (i % 2 == 0) else -ALTURA_Y
        posiciones[i] = (x, y)

    st.session_state.posiciones_nodos = posiciones


def interseca_nodo(u, v, posiciones, num_nodos, umbral=30.0):
    """Verifica geométricamente si el segmento entre u y v atraviesa algún nodo k."""
    x1, y1 = posiciones.get(u, (0, 0))
    x2, y2 = posiciones.get(v, (0, 0))

    for k in range(num_nodos):
        if k == u or k == v:
            continue

        xk, yk = posiciones.get(k, (0, 0))

        min_x, max_x = min(x1, x2) - 10, max(x1, x2) + 10
        min_y, max_y = min(y1, y2) - 10, max(y1, y2) + 10

        if min_x <= xk <= max_x and min_y <= yk <= max_y:
            num = abs((y2 - y1) * xk - (x2 - x1) * yk + x2 * y1 - y2 * x1)
            den = ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5
            distancia = num / den if den != 0 else 0

            if distancia < umbral:
                return True
    return False


def ejecutar_ford_fulkerson_pasos(num_nodos, aristas, fuente, sumidero):
    """Ejecuta Ford-Fulkerson paso a paso guardando el cuello de botella puntual de cada iteración."""
    capacidad = {}
    flujo = {}
    nodos = list(range(num_nodos))

    for u in nodos:
        for v in nodos:
            capacidad[(u, v)] = 0
            flujo[(u, v)] = 0

    for u, v, c in aristas:
        capacidad[(u, v)] = c

    historial = []

    # Estado inicial (Paso 1)
    historial.append(
        {
            "paso": 0,
            "camino": [],
            "cuello_botella": 0,
            "flujo": {
                k: v
                for k, v in flujo.items()
                if capacidad[k] > 0 or capacidad[(k[1], k[0])] > 0
            },
            "etiquetas": {fuente: ("-", "∞")},
            "flujo_total": 0,
            "mensaje": "Paso 1: Inicialización con flujo cero en todas las aristas y fuente etiquetada como (-, ∞).",
        }
    )

    flujo_total = 0
    iteracion = 1

    while True:
        etiquetas = {fuente: ("-", float("inf"))}
        padre = {}
        cola = [fuente]
        sumidero_encontrado = False

        while cola and not sumidero_encontrado:
            u = cola.pop(0)
            delta_u = etiquetas[u][1]

            for v in nodos:
                if v not in etiquetas:
                    residual = capacidad[(u, v)] - flujo[(u, v)]
                    if residual > 0:
                        delta = min(delta_u, residual)
                        etiquetas[v] = (f"{u}⁺", delta)
                        padre[v] = u
                        cola.append(v)
                        if v == sumidero:
                            sumidero_encontrado = True
                            break
                    elif flujo[(v, u)] > 0:
                        delta = min(delta_u, flujo[(v, u)])
                        etiquetas[v] = (f"{u}⁻", delta)
                        padre[v] = u
                        cola.append(v)
                        if v == sumidero:
                            sumidero_encontrado = True
                            break

        if not sumidero_encontrado:
            conjunto_S = set(etiquetas.keys())
            conjunto_T = set(nodos) - conjunto_S

            capacidad_corte = 0
            aristas_corte = []
            for u in conjunto_S:
                for v in conjunto_T:
                    if capacidad[(u, v)] > 0:
                        capacidad_corte += capacidad[(u, v)]
                        aristas_corte.append((u, v))

            historial.append(
                {
                    "paso": iteracion,
                    "camino": [],
                    "cuello_botella": 0,
                    "flujo": {
                        k: v
                        for k, v in flujo.items()
                        if capacidad[k] > 0 or capacidad[(k[1], k[0])] > 0
                    },
                    "etiquetas": etiquetas,
                    "flujo_total": flujo_total,
                    "finalizado": True,
                    "conjunto_S": conjunto_S,
                    "conjunto_T": conjunto_T,
                    "capacidad_corte": capacidad_corte,
                    "aristas_corte": aristas_corte,
                    "mensaje": f"Algoritmo finalizado: No existen más caminos de aumento. Flujo Máximo |f| = {flujo_total} = c(S, T).",
                }
            )
            break

        camino = []
        actual = sumidero
        cuello_botella = etiquetas[sumidero][1]

        while actual != fuente:
            anterior = padre[actual]
            camino.append((anterior, actual))
            actual = anterior
        camino.reverse()

        # Guardar el estado previo al incremento para identificar exactamente cuál arista tenía el residual igual al cuello de botella
        flujo_previo = dict(flujo)

        for u, v in camino:
            if "+" in etiquetas[v][0] or "⁺" in etiquetas[v][0]:
                flujo[(u, v)] += cuello_botella
            else:
                flujo[(v, u)] -= cuello_botella

        flujo_total += cuello_botella

        historial.append(
            {
                "paso": iteracion,
                "camino": camino,
                "cuello_botella": cuello_botella,
                "flujo_previo": flujo_previo,
                "flujo": {
                    k: v
                    for k, v in flujo.items()
                    if capacidad[k] > 0 or capacidad[(k[1], k[0])] > 0
                },
                "etiquetas": etiquetas,
                "flujo_total": flujo_total,
                "finalizado": False,
                "mensaje": f"Iteración {iteracion}: Camino de aumento {' -> '.join(str(n) for n in [fuente] + [arista[1] for arista in camino])}. Incremento Δ = {cuello_botella}.",
            }
        )

        iteracion += 1

    return historial


def renderizar_grafo_pyvis(
    num_nodos, aristas, info_paso_actual, nodo_fuente, nodo_sumidero, nombres_nodos=None
):
    """Renderiza el grafo destacando el texto en rojo solo para la arista limitante de este paso."""
    red = Network(
        height="550px",
        width="100%",
        directed=True,
        bgcolor="#f8f9fa",
        font_color="#000000",
    )

    if nombres_nodos is None:
        nombres_nodos = {i: str(i) for i in range(num_nodos)}

    posiciones = st.session_state.posiciones_nodos

    red.set_options("""
    {
      "physics": { "enabled": false },
      "interaction": { "dragNodes": true, "dragView": true, "zoomView": true }
    }
    """)

    dicc_etiquetas = info_paso_actual.get("etiquetas", {})
    dicc_flujo = info_paso_actual.get("flujo", {})
    dicc_flujo_previo = info_paso_actual.get("flujo_previo", {})
    aristas_camino = set(info_paso_actual.get("camino", []))
    cuello_botella_paso = info_paso_actual.get("cuello_botella", 0)
    esta_finalizado = info_paso_actual.get("finalizado", False)
    conjunto_S = info_paso_actual.get("conjunto_S", set())
    aristas_corte = set(info_paso_actual.get("aristas_corte", []))

    # Añadir Nodos
    for i in range(num_nodos):
        etiqueta_nodo = f"Nodo {nombres_nodos[i]}"
        if i in dicc_etiquetas:
            tag, delta = dicc_etiquetas[i]
            delta_str = "∞" if delta == float("inf") else str(delta)
            etiqueta_nodo += f"\n({tag}, {delta_str})"

        color = "#97C2FC"
        if i == nodo_fuente:
            color = "#2ECC71"
        elif i == nodo_sumidero:
            color = "#E74C3C"
        elif esta_finalizado:
            color = "#F39C12" if i in conjunto_S else "#3498DB"

        x, y = posiciones.get(i, (0, 0))

        red.add_node(
            i,
            label=etiqueta_nodo,
            color=color,
            title=f"Etiqueta: {dicc_etiquetas.get(i, 'Sin etiqueta')}",
            shape="circle",
            size=26,
            x=x,
            y=y,
            physics=False,
        )

    parejas_existentes = set((u, v) for u, v, _ in aristas)

    # Añadir Aristas
    for u, v, c in aristas:
        f = dicc_flujo.get((u, v), 0)
        etiqueta_arista = f"{c}, {f}"

        # Determinar si esta arista fue la CUELLO DE BOTELLA en ESTE PASO EXACTO
        # (Estaba en el camino y su capacidad residual previa coincidía con el cuello de botella)
        f_prev = dicc_flujo_previo.get((u, v), 0)
        residual_previo = c - f_prev
        es_limitante_del_paso = (
            (u, v) in aristas_camino
            and (residual_previo == cuello_botella_paso)
            and cuello_botella_paso > 0
        )

        # 1. Color y estilo base
        color_arista = "#848484"
        ancho = 2
        color_texto = "#E74C3C" if es_limitante_del_paso else "#343434"

        # 2. Camino de aumento activo en este paso: LÍNEA AMARILLA
        if (u, v) in aristas_camino:
            color_arista = "#F1C40F"
            ancho = 5

        # 3. Estado finalizado (Corte Mínimo)
        if esta_finalizado and (u, v) in aristas_corte:
            color_arista = "#E74C3C"
            color_texto = "#E74C3C"
            ancho = 6

        # Configuración de fuente de la etiqueta numérica
        config_fuente = {
            "color": color_texto,
            "size": 23,
            "strokeWidth": 5,
            "strokeColor": "#ffffff",
        }

        pasa_sobre_nodo = interseca_nodo(u, v, posiciones, num_nodos)
        es_bidireccional = (v, u) in parejas_existentes

        if pasa_sobre_nodo or es_bidireccional:
            _, yu = posiciones.get(u, (0, 0))
            _, yv = posiciones.get(v, (0, 0))
            y_medio = (yu + yv) / 2

            if y_medio >= 0:
                tipo_curva = "curvedCCW" if u < v else "curvedCW"
            else:
                tipo_curva = "curvedCW" if u < v else "curvedCCW"

            config_suave = {
                "enabled": True,
                "type": tipo_curva,
                "roundness": 0.25,
            }
        else:
            config_suave = False

        red.add_edge(
            u,
            v,
            label=etiqueta_arista,
            color=color_arista,
            font=config_fuente,
            width=ancho,
            smooth=config_suave,
            arrowStrikethrough=False,
        )

    dir_temporal = tempfile.gettempdir()
    ruta = os.path.join(dir_temporal, "graph.html")
    red.save_graph(ruta)

    with open(ruta, "r", encoding="utf-8") as f:
        contenido_html = f.read()

    js_persistencia = """
    <script type="text/javascript">
        function recalculateEdgeCurvatures() {
            var nodePositions = network.getPositions();
            var nodeIds = Object.keys(nodePositions);
            var edges = network.body.data.edges.get();

            edges.forEach(function(edge) {
                var u = edge.from;
                var v = edge.to;
                var posU = nodePositions[u];
                var posV = nodePositions[v];

                if (!posU || !posV) return;

                var intersects = false;
                for (var i = 0; i < nodeIds.length; i++) {
                    var k = nodeIds[i];
                    if (k == u || k == v) continue;
                    var posK = nodePositions[k];

                    var minX = Math.min(posU.x, posV.x) - 10;
                    var maxX = Math.max(posU.x, posV.x) + 10;
                    var minY = Math.min(posU.y, posV.y) - 10;
                    var maxY = Math.max(posU.y, posV.y) + 10;

                    if (posK.x >= minX && posK.x <= maxX && posK.y >= minY && posK.y <= maxY) {
                        var num = Math.abs((posV.y - posU.y) * posK.x - (posV.x - posU.x) * posK.y + posV.x * posU.y - posV.y * posU.x);
                        var den = Math.sqrt(Math.pow(posV.y - posU.y, 2) + Math.pow(posV.x - posU.x, 2));
                        var dist = den !== 0 ? num / den : 0;
                        if (dist < 30) {
                            intersects = true;
                            break;
                        }
                    }
                }

                if (intersects) {
                    var yMid = (posU.y + posV.y) / 2;
                    var type = yMid >= 0 ? (u < v ? "curvedCCW" : "curvedCW") : (u < v ? "curvedCW" : "curvedCCW");
                    network.body.data.edges.update({id: edge.id, smooth: {enabled: true, type: type, roundness: 0.25}});
                } else {
                    network.body.data.edges.update({id: edge.id, smooth: false});
                }
            });
        }

        network.on("dragging", function (params) {
            recalculateEdgeCurvatures();
        });

        network.on("dragEnd", function (params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                var position = network.getPosition(nodeId);
                var url = new URL(window.parent.location.href);
                url.searchParams.set("dragged_node", nodeId);
                url.searchParams.set("x", position.x);
                url.searchParams.set("y", position.y);
                window.parent.location.href = url.toString();
            }
        });
    </script>
    </body>
    """
    contenido_html = contenido_html.replace("</body>", js_persistencia)
    return contenido_html


# --- BARRA LATERAL: CONFIGURACIÓN ---
st.sidebar.header("⚙ Configuración del Grafo")

numero_nodos = st.sidebar.number_input(
    "Número de Nodos (n ∈ [7, 16]):",
    min_value=7,
    max_value=16,
    value=st.session_state.numero_nodos,
    step=1,
)

if numero_nodos != st.session_state.numero_nodos:
    st.session_state.numero_nodos = numero_nodos
    st.session_state.aristas = []
    st.session_state.historial = []
    st.session_state.paso_actual = 0
    st.session_state.posiciones_nodos = {}

modo_creacion = st.sidebar.radio("Modo de Creación:", ["Aleatorio", "Manual"])

if modo_creacion == "Aleatorio":
    if st.sidebar.button("🎲 Generar Grafo Aleatorio"):
        st.session_state.aristas = generar_dag_aleatorio(numero_nodos)
        st.session_state.historial = []
        st.session_state.paso_actual = 0
        generar_posiciones_zigzag(numero_nodos)

else:
    st.sidebar.subheader("Agregar Arista")
    col1, col2, col3 = st.sidebar.columns(3)
    u_in = col1.number_input("Origen", 0, numero_nodos - 1, 0)
    v_in = col2.number_input("Destino", 0, numero_nodos - 1, 1)
    cap_in = col3.number_input("Capacidad", 1, 100, 10)

    if st.sidebar.button("➕ Añadir Arista"):
        if u_in == v_in:
            st.sidebar.error("No se permiten bucles en el mismo nodo.")
        else:
            nuevas_aristas = [
                e
                for e in st.session_state.aristas
                if not (e[0] == u_in and e[1] == v_in)
            ]
            nuevas_aristas.append((u_in, v_in, cap_in))

            hay_ciclo, ciclos = tiene_ciclos(numero_nodos, nuevas_aristas)
            if hay_ciclo:
                st.sidebar.error(
                    f"❌ ¡Ciclo detectado! No se puede añadir esta arista: {ciclos[0]}"
                )
            else:
                st.session_state.aristas = nuevas_aristas
                st.session_state.historial = []
                st.session_state.paso_actual = 0
                if not st.session_state.posiciones_nodos:
                    generar_posiciones_zigzag(numero_nodos)

    if st.sidebar.button("🗑️ Limpiar Aristas"):
        st.session_state.aristas = []
        st.session_state.historial = []
        st.session_state.paso_actual = 0
        st.session_state.posiciones_nodos = {}

# --- PANEL PRINCIPAL ---
hay_ciclo, ciclos = tiene_ciclos(
    st.session_state.numero_nodos, st.session_state.aristas
)
if hay_ciclo:
    st.error(f"⚠️ El grafo actual contiene ciclos: {ciclos}. Corrige la estructura.")

indices_nodos = list(range(st.session_state.numero_nodos))

st.subheader("1️⃣ Selección de Fuentes y Sumideros")
col_s, col_t = st.columns(2)

fuentes_seleccionadas = col_s.multiselect(
    "Selecciona Fuentes Originales:",
    indices_nodos,
    default=[0] if indices_nodos else [],
)
sumideros_seleccionados = col_t.multiselect(
    "Selecciona Sumideros Originales:",
    indices_nodos,
    default=[st.session_state.numero_nodos - 1] if indices_nodos else [],
)

aristas_efectivas = list(st.session_state.aristas)
num_nodos_efectivos = st.session_state.numero_nodos
fuente_actual = fuentes_seleccionadas[0] if len(fuentes_seleccionadas) == 1 else None
sumidero_actual = (
    sumideros_seleccionados[0] if len(sumideros_seleccionados) == 1 else None
)

nombres_visibles_nodos = {i: str(i) for i in range(st.session_state.numero_nodos)}

if len(fuentes_seleccionadas) > 1 or len(sumideros_seleccionados) > 1:
    st.info(
        "ℹ Se incorporará un Origen Ficticio (S) y/o Destino Ficticio (T) con aristas de capacidad ∞."
    )

    id_fuente_ficticia = num_nodos_efectivos
    id_sumidero_ficticio = num_nodos_efectivos + (
        1 if len(fuentes_seleccionadas) > 1 else 0
    )

    if len(fuentes_seleccionadas) > 1:
        for nodo_s in fuentes_seleccionadas:
            aristas_efectivas.append((id_fuente_ficticia, nodo_s, 999999))
        fuente_actual = id_fuente_ficticia
        nombres_visibles_nodos[id_fuente_ficticia] = "S (Ficticia)"
        num_nodos_efectivos += 1

    if len(sumideros_seleccionados) > 1:
        for nodo_t in sumideros_seleccionados:
            aristas_efectivas.append((nodo_t, id_sumidero_ficticio, 999999))
        sumidero_actual = id_sumidero_ficticio
        nombres_visibles_nodos[id_sumidero_ficticio] = "T (Ficticio)"
        num_nodos_efectivos += 1

if (
    not st.session_state.posiciones_nodos
    or len(st.session_state.posiciones_nodos) < num_nodos_efectivos
):
    generar_posiciones_zigzag(num_nodos_efectivos)

st.subheader("2️⃣ Simulación del Algoritmo de Ford-Fulkerson")

if fuente_actual is None or sumidero_actual is None:
    st.warning("Debe haber al menos una fuente y un sumidero seleccionados.")
else:
    if st.button("🚀 Ejecutar / Reiniciar Simulación"):
        st.session_state.historial = ejecutar_ford_fulkerson_pasos(
            num_nodos_efectivos, aristas_efectivas, fuente_actual, sumidero_actual
        )
        st.session_state.paso_actual = 0

# --- NAVEGACIÓN PASO A PASO Y VISUALIZACIÓN ---
if st.session_state.historial:
    historial = st.session_state.historial
    paso_actual = st.session_state.paso_actual
    total_pasos = len(historial) - 1

    c1, c2, c3, c4 = st.columns([1, 1, 2, 2])
    if c1.button("⏮️ Inicio"):
        st.session_state.paso_actual = 0
    if c2.button("◀️️ Anterior") and paso_actual > 0:
        st.session_state.paso_actual -= 1
    if c3.button("Siguiente ▶") and paso_actual < total_pasos:
        st.session_state.paso_actual += 1
    if c4.button("⏭ Final"):
        st.session_state.paso_actual = total_pasos

    paso_actual = st.session_state.paso_actual
    info_paso = historial[paso_actual]

    st.markdown(f"**Paso {paso_actual} de {total_pasos}:** {info_paso['mensaje']}")
    st.metric(
        label="Flujo Total Actual |f|", value=f"{info_paso['flujo_total']} unidades"
    )

    html_grafo = renderizar_grafo_pyvis(
        num_nodos_efectivos,
        aristas_efectivas,
        info_paso,
        fuente_actual,
        sumidero_actual,
        nombres_visibles_nodos,
    )
    componentes.html(html_grafo, height=570)

    if info_paso.get("finalizado", False):
        st.success("🎉 **RESULTADO FINAL Y CORTE MÍNIMO**")

        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown(f"**Valor del Flujo Máximo |f|:** `{info_paso['flujo_total']}`")
            st.markdown(
                f"**Capacidad del Corte Mínimo c(S,T):** `{info_paso['capacidad_corte']}`"
            )
            st.markdown(
                r"**Verificación:** $\vert{}f\vert{} = c(S,T)$ (Teorema de Flujo Máximo y Corte Mínimo)"
            )

        with col_res2:
            nombres_S = [nombres_visibles_nodos[i] for i in info_paso["conjunto_S"]]
            nombres_T = [nombres_visibles_nodos[i] for i in info_paso["conjunto_T"]]
            st.markdown(f"**Conjunto S (Fuente):** {nombres_S}")
            st.markdown(f"**Conjunto T (Sumidero):** {nombres_T}")

        st.subheader("📋 Asignación de Flujo por Arista")
        tabla_datos = []
        for u, v, c in aristas_efectivas:
            f = info_paso["flujo"].get((u, v), 0)
            cap_str = "∞" if c == 999999 else str(c)
            tabla_datos.append(
                {
                    "Origen": nombres_visibles_nodos[u],
                    "Destino": nombres_visibles_nodos[v],
                    "Flujo Asignado": f,
                    "Capacidad": cap_str,
                    "Saturada": "Sí" if f == c and c != 999999 else "No",
                }
            )
        st.dataframe(tabla_datos, use_container_width=True)
