# Proyecto final - Algoritmos II, Unidad 3 (Árboles): Gestor de proyectos y tareas
# Ejecutar: python gestor.py  ->  abrir http://localhost:8000   (python gestor.py --vacio  = sin datos de ejemplo)
import json, os, sys
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

AQUI = os.path.dirname(os.path.abspath(__file__))
ARCHIVO, HTML = os.path.join(AQUI, "datos.json"), os.path.join(AQUI, "index.html")
PRIO = ["Baja", "Media", "Alta", "Máxima"]          # verde, naranja, roja, negra
EST = ["Pendiente", "En progreso", "Completada"]
categorias = ["Académicas", "Laborales", "Personales", "Salud", "Finanzas", "Hogar"]

# ---------- Árbol binario de búsqueda (misma estructura del archivo 1212.py) ----------
class Nodo:
    def __init__(self, codigo, datos):
        self.codigo, self.datos = codigo, datos      # el código es el "peso" del nodo
        self.izquierdo = self.derecho = None

class Arbol:
    def __init__(self):
        self.raiz = None

    def insertar(self, codigo, datos):               # False si el código ya existe
        if self.buscar(codigo):
            return False
        self.raiz = self._insertar(self.raiz, codigo, datos)
        return True

    def _insertar(self, raiz, codigo, datos):
        if raiz is None:
            return Nodo(codigo, datos)
        if codigo < raiz.codigo:
            raiz.izquierdo = self._insertar(raiz.izquierdo, codigo, datos)
        else:
            raiz.derecho = self._insertar(raiz.derecho, codigo, datos)
        return raiz

    def buscar(self, codigo):
        r = self.raiz
        while r and r.codigo != codigo:
            r = r.izquierdo if codigo < r.codigo else r.derecho
        return r

    def inorden(self, desc=False):                   # asc: izq-raíz-der | desc: der-raíz-izq
        salida = []
        def rec(r):
            if r:
                a, b = (r.derecho, r.izquierdo) if desc else (r.izquierdo, r.derecho)
                rec(a); salida.append(r.datos); rec(b)
        rec(self.raiz)
        return salida

    def maximo(self):
        r = self.raiz
        while r and r.derecho:
            r = r.derecho
        return r.codigo if r else 0

    def eliminar(self, codigo):
        if not self.buscar(codigo):
            return False
        self.raiz = self._eliminar(self.raiz, codigo)
        return True

    def _eliminar(self, r, c):
        if c < r.codigo:
            r.izquierdo = self._eliminar(r.izquierdo, c)
        elif c > r.codigo:
            r.derecho = self._eliminar(r.derecho, c)
        else:
            if not r.izquierdo: return r.derecho
            if not r.derecho: return r.izquierdo
            s = r.derecho                            # sucesor inorden
            while s.izquierdo: s = s.izquierdo
            r.codigo, r.datos = s.codigo, s.datos
            r.derecho = self._eliminar(r.derecho, s.codigo)
        return r

def llenar(arbol, lista):                            # inserta por la mediana: árbol equilibrado
    if lista:
        m = len(lista) // 2
        arbol.insertar(lista[m]["codigo"], lista[m])
        llenar(arbol, lista[:m]); llenar(arbol, lista[m + 1:])

proyectos = Arbol()

# ---------- Persistencia ----------
def guardar():
    ps = [dict(p, tareas=p["tareas"].inorden()) for p in proyectos.inorden()]
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump({"categorias": categorias, "proyectos": ps}, f, ensure_ascii=False, indent=1)

def cargar(vacio):
    global categorias
    if os.path.exists(ARCHIVO):
        d = json.load(open(ARCHIVO, encoding="utf-8"))
        categorias = d["categorias"]
        lista = d["proyectos"]
    elif vacio:
        return
    else:
        h = lambda n: str(date.today() + timedelta(days=n))
        mk = lambda c, n, cat, pr, fin, es, et, no="": dict(codigo=c, nombre=n, categoria=cat, prioridad=pr,
              creacion=h(0), fin=h(fin), estado=es, etiquetas=et, notas=no)
        lista = [dict(mk(1, "Proyecto final de Algoritmos II", "Académicas", "Alta", 4, "En progreso",
                         ["universidad", "python"], "Entrega con interfaz HTML"),
                      tareas=[mk(1, "Diseñar el árbol binario", "Académicas", "Alta", 1, "Completada", ["diseño"]),
                              mk(2, "Construir la interfaz", "Académicas", "Máxima", 3, "En progreso", ["html"]),
                              mk(3, "Preparar la sustentación", "Académicas", "Media", -2, "Pendiente", ["universidad"])]),
                 dict(mk(2, "Chequeo médico anual", "Salud", "Baja", 20, "Pendiente", ["salud"]),
                      tareas=[mk(1, "Agendar cita", "Salud", "Baja", 5, "Pendiente", ["salud"])])]
    for p in lista:
        ts, p["tareas"] = p["tareas"], Arbol()
        llenar(p["tareas"], ts)
    llenar(proyectos, lista)

# ---------- Lógica ----------
def vencida(x):
    return x["fin"] < str(date.today()) and x["estado"] != "Completada"

def campos(b, base, cat_def=None):
    nombre = str(b.get("nombre", "")).strip()
    cat = str(b.get("categoria", "")).strip() or cat_def
    if not nombre: raise ValueError("El nombre es obligatorio.")
    if not cat: raise ValueError("La categoría es obligatoria.")
    if b.get("prioridad") not in PRIO: raise ValueError("Prioridad inválida.")
    if b.get("estado") not in EST: raise ValueError("Estado inválido.")
    try: date.fromisoformat(b.get("fin", ""))
    except ValueError: raise ValueError("Fecha de finalización inválida.")
    if b["fin"] < base: raise ValueError("La fecha de finalización no puede ser anterior a la de creación.")
    if cat not in categorias:
        categorias.append(cat)                       # categoría "Otra" creada por el usuario
    et = b.get("etiquetas", "")
    et = et.split(",") if isinstance(et, str) else et
    return dict(nombre=nombre, categoria=cat, prioridad=b["prioridad"], fin=b["fin"], estado=b["estado"],
                notas=str(b.get("notas", "")).strip(),
                etiquetas=[e.strip().lower().lstrip("#") for e in et if e.strip()])

def crear(arbol, b, extra, cat_def=None):
    try: cod = int(b.get("codigo") or arbol.maximo() + 1)
    except (TypeError, ValueError): raise ValueError("Código inválido.")
    if cod < 1: raise ValueError("El código debe ser mayor a 0.")
    hoy = str(date.today())
    if not arbol.insertar(cod, dict(codigo=cod, creacion=hoy, **campos(b, hoy, cat_def), **extra)):
        raise ValueError(f"El código {cod} ya existe.")
    guardar()
    return {"ok": True}

def pedir(arbol, c):
    n = arbol.buscar(int(c))
    if not n: raise ValueError(f"No existe el código {c}.")
    return n.datos

def cumple(x, q):
    t = q.get("q", "").lower()
    if t and t not in x["nombre"].lower() and t not in x["notas"].lower() and t != str(x["codigo"]): return False
    for k in ("categoria", "prioridad", "estado"):
        if q.get(k) and x[k] != q[k]: return False
    if q.get("etiqueta") and q["etiqueta"].lower().lstrip("#") not in x["etiquetas"]: return False
    return not (q.get("vencidas") and not vencida(x))

def vista(p, desc):
    d = {k: v for k, v in p.items() if k != "tareas"}
    return dict(d, vencido=vencida(p), tareas=[dict(t, vencida=vencida(t)) for t in p["tareas"].inorden(desc)])

def rutas(m, r, q, b):
    desc = q.get("orden") == "desc"
    if r == ["meta"]:
        return {"categorias": categorias, "prioridades": PRIO, "estados": EST, "hoy": str(date.today())}
    if r == ["tareas"]:                              # búsqueda de tareas: proyectos y tareas en inorden
        return [dict(t, proyecto=p["codigo"], proyecto_nombre=p["nombre"], vencida=vencida(t))
                for p in proyectos.inorden(desc) for t in p["tareas"].inorden(desc) if cumple(t, q)]
    if r == ["proyectos"]:
        if m == "GET": return [vista(p, desc) for p in proyectos.inorden(desc) if cumple(p, q)]
        return crear(proyectos, b, {"tareas": Arbol()})
    if len(r) >= 2 and r[0] == "proyectos":
        p = pedir(proyectos, r[1])
        if len(r) == 2:
            if m == "GET": return vista(p, desc)
            if m == "PUT": p.update(campos(b, p["creacion"]))
            if m == "DELETE": proyectos.eliminar(p["codigo"])
        elif r[2] == "tareas" and len(r) == 3 and m == "POST":
            return crear(p["tareas"], b, {}, p["categoria"])
        elif r[2] == "tareas" and len(r) == 4:
            t = pedir(p["tareas"], r[3])
            if m == "PUT": t.update(campos(b, t["creacion"]))
            if m == "DELETE": p["tareas"].eliminar(t["codigo"])
        guardar()
        return {"ok": True}
    raise ValueError("Ruta no encontrada.")

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def responder(self, datos, codigo=200, tipo="application/json"):
        cuerpo = datos if isinstance(datos, bytes) else json.dumps(datos, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", tipo + "; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers(); self.wfile.write(cuerpo)

    def atender(self, m):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        r = [x for x in u.path.split("/") if x]
        try:
            if m == "GET" and not r:
                return self.responder(open(HTML, "rb").read(), tipo="text/html")
            n = int(self.headers.get("Content-Length") or 0)
            self.responder(rutas(m, r[1:], q, json.loads(self.rfile.read(n)) if n else {}))
        except ValueError as e:
            self.responder({"error": str(e)}, 400)

    def do_GET(self): self.atender("GET")
    def do_POST(self): self.atender("POST")
    def do_PUT(self): self.atender("PUT")
    def do_DELETE(self): self.atender("DELETE")

if __name__ == "__main__":
    cargar("--vacio" in sys.argv)
    print("Gestor listo en http://localhost:8000  (Ctrl+C para salir)")
    ThreadingHTTPServer(("", 8000), H).serve_forever()
