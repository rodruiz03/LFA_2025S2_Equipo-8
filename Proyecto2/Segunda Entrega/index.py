"""
Librerias Utilizadas
En este caso hay 2 factores fundamentales la primera que es necesario para que todo funcione bien
ninguna es externa de phyton debido a los requierimientos del proyecto
"""
import tkinter as tk                                                    #Ayuda a la interfaz grafica
from tkinter import filedialog, messagebox, ttk, scrolledtext           #Es para lo de los grafos
import os                                                               #Permite la interaccion de archivos
import subprocess                                                       #Ejecuta comandos de subprocesos
import sys                                                              #Acceso a rutas para los PDF´s
from dataclasses import dataclass, field                                #Se usa en el analizador
from typing import List, Optional, Union                                #Hace la parte del analizador

# ============================================================================ 
# CONFIGURACIÓN DE OPERADORES
# ============================================================================
#Se uso esta parte de darle simbolos en vez de palabras mas que nada porque era un poco mas entendible cuando se hacen los mapas
OPER_MAP = {
    'SUMA': '+',
    'RESTA': '-',
    'MULTIPLICACION': '*',
    'DIVISION': '/',
    'POTENCIA': '^',
    'RAIZ': 'r',
    'INVERSO': 'i',
    'MOD': '%'
}
# ============================================================================ 
# CLASES LÉXICO / TOKENS
# ============================================================================
#Aqui se hace los cambios de los tokens para saber que clase tienen y el apartado de fila y columna para el HTML de errores
@dataclass
class Token:
    tipo: str
    lexema: str
    fila: int
    columna: int
class ScannerLexico:
    """
    Scanner que tokeniza el texto y registra errores léxicos en formato:
    { "No": int, "Lexema": str, "Tipo": str, "Columna": int, "Fila": int, "Mensaje": str }
    """
    PALABRAS_RESERVADAS = set(OPER_MAP.keys())
    ETIQUETAS = {'Operacion', 'Numero', 'P', 'R'}

    def __init__(self, texto: str):
        self.texto = texto
        self.posicion = 0
        self.fila = 1
        self.columna = 1
        self.tokens: List[Token] = []
        self.errores: List[dict] = []

    def peek(self, offset: int = 0) -> Optional[str]:
        pos = self.posicion + offset
        return self.texto[pos] if pos < len(self.texto) else None

    def advance(self) -> Optional[str]:
        if self.posicion >= len(self.texto):
            return None
        ch = self.texto[self.posicion]
        self.posicion += 1
        if ch == '\n':
            self.fila += 1
            self.columna = 1
        else:
            self.columna += 1
        return ch
    #Define si es digito, letra o espacios en blanco
    def es_digito(self, ch: Optional[str]) -> bool:
        return ch is not None and '0' <= ch <= '9'

    def es_letra(self, ch: Optional[str]) -> bool:
        return ch is not None and (('A' <= ch <= 'Z') or ('a' <= ch <= 'z'))

    def es_espacio(self, ch: Optional[str]) -> bool:
        return ch in (' ', '\t', '\n', '\r')
    #Registra los errores 
    def registrar_error(self, mensaje: str, fila: int, columna: int, lexema: str):
        """Registra un error en el formato pedido (No, Lexema, Tipo, COLUMNA, FILA)."""
        self.errores.append({
            "No": len(self.errores) + 1,
            "Lexema": lexema,
            "Tipo": "Error",
            "Columna": columna,
            "Fila": fila,
            "Mensaje": mensaje
        })
    #Se extraen los numeros 
    def extraer_numero(self) -> Token:
        inicio_fila = self.fila
        inicio_columna = self.columna
        num = ""
        while self.es_digito(self.peek()):
            num += self.advance() # type: ignore
        if self.peek() == '.':
            num += self.advance()# type: ignore
            while self.es_digito(self.peek()):
                num += self.advance()# type: ignore
        return Token("NUMERO", num, inicio_fila, inicio_columna)
    #Se identifican las palabras o etiquetas 
    def extraer_palabra_o_etiqueta(self) -> Token:
        inicio_fila = self.fila
        inicio_columna = self.columna
        palabra = ""
        while self.es_letra(self.peek()) or self.peek() == '_':
            palabra += self.advance()# type: ignore
        palabra_norm = palabra.upper()
        return Token("IDENTIFICADOR", palabra_norm, inicio_fila, inicio_columna)
    #En caso de fallo hay una etiqueta habierta lo que ocaciona un error es un trigger digamos
    def extraer_etiqueta_abierta(self) -> Token:
        inicio_fila = self.fila
        inicio_columna = self.columna
        lex = ""
        # consume '<'
        lex += self.advance()# type: ignore
        nombre = ""
        while self.es_letra(self.peek()) or self.peek() == '_':
            nombre += self.advance()# type: ignore
        if not nombre:
            self.registrar_error("Etiqueta sin nombre", inicio_fila, inicio_columna, "<")
            # sincronizar hasta '>'
            while self.peek() and self.peek() != '>':
                self.advance()
            if self.peek() == '>':
                lex += self.advance()# type: ignore
            return Token("ETIQUETA_ABIERTA", lex, inicio_fila, inicio_columna)
        lex += nombre
        if self.peek() == '=':
            lex += self.advance()# type: ignore
            while self.es_espacio(self.peek()) and self.peek() != '\n':
                lex += self.advance()# type: ignore
            tipo_op = ""
            while self.es_letra(self.peek()) or self.peek() == '_':
                tipo_op += self.advance()# type: ignore
            tipo_op_norm = tipo_op.upper()
            if tipo_op_norm and tipo_op_norm not in self.PALABRAS_RESERVADAS:
                # registrar como error léxico del tipo de operación (aunque no detenemos el scanner)
                self.registrar_error(f"Tipo de operación no válido: {tipo_op_norm}", self.fila, self.columna - len(tipo_op), tipo_op_norm)
            lex += tipo_op
        # consumir espacios hasta '>'
        while self.es_espacio(self.peek()) and self.peek() != '\n':
            lex += self.advance()# type: ignore
        if self.peek() == '>':
            lex += self.advance()# type: ignore
        else:
            self.registrar_error("Se esperaba '>' para cerrar etiqueta", self.fila, self.columna, self.peek() or "EOF")
        return Token("ETIQUETA_ABIERTA", lex, inicio_fila, inicio_columna)
    #Si todo sale bien en la ejecucion existira la etiqueta cerrada y eso sera valido
    def extraer_etiqueta_cerrada(self) -> Token:
        inicio_fila = self.fila
        inicio_columna = self.columna
        lex = ""
        lex += self.advance()# type: ignore
        if self.peek() != '/':
            self.registrar_error("Se esperaba '/' en etiqueta de cierre", self.fila, self.columna, self.peek() or "")
            return Token("ETIQUETA_CERRADA", lex, inicio_fila, inicio_columna)
        lex += self.advance()# type: ignore
        nombre = ""
        while self.es_letra(self.peek()) or self.peek() == '_':
            nombre += self.advance()# type: ignore
        if nombre not in self.ETIQUETAS:
            self.registrar_error(f"Etiqueta de cierre no válida: {nombre}", inicio_fila, inicio_columna, f"</{nombre}")
        lex += nombre
        if self.peek() == '>':
            lex += self.advance()# type: ignore
        else:
            self.registrar_error("Se esperaba '>'", self.fila, self.columna, "")
        return Token("ETIQUETA_CERRADA", lex, inicio_fila, inicio_columna)
    #Con los toquens se evaluan los numeros para saber si son iguales o existe algun error
    def scanear(self) -> List[Token]:
        while self.posicion < len(self.texto):
            ch = self.peek()
            if self.es_espacio(ch):
                self.advance()
                continue
            if self.es_digito(ch):
                self.tokens.append(self.extraer_numero())
            elif ch == '<':
                if self.peek(1) == '/':
                    self.tokens.append(self.extraer_etiqueta_cerrada())
                else:
                    self.tokens.append(self.extraer_etiqueta_abierta())
            elif ch == '=':
                self.tokens.append(Token("IGUAL", self.advance(), self.fila, self.columna - 1))# type: ignore
            elif ch == '>':
                self.tokens.append(Token("MAYOR", self.advance(), self.fila, self.columna - 1))# type: ignore
            elif self.es_letra(ch) or ch == '_':
                self.tokens.append(self.extraer_palabra_o_etiqueta())
            else:
                # carácter inválido -> registrar con la posición actual
                inval = self.advance()
                self.registrar_error("Carácter no reconocido", self.fila, self.columna - 1, inval)# type: ignore
                self.tokens.append(Token("ERROR", inval, self.fila, self.columna - 1))# type: ignore
        self.tokens.append(Token("EOF", "", self.fila, self.columna))
        return self.tokens
# ============================================================================ 
# NODOS, PARSER Y EVALUADOR
# ============================================================================
@dataclass
class NodoOperacion:
    tipo: str
    operandos: List[Union['NodoOperacion', float]] = field(default_factory=list)
    valido: bool = True
    fila: int = 0
    columna: int = 0
# ============================================================================ 
# Clase parseo
# ============================================================================
class Parser:
    """
    Parser que construye los nodos. parsear_operacion recibe nivel para distinguir
    raíz vs anidadas (pero en esta implementación las anidadas se devuelven como
    hijos y no se listan por separado en la salida principal).
    """
    #recibe la lista de tokens y prepara el análisis.
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.posicion = 0
        self.errores: List[str] = []
    #es el punto de entrada del análisis sintáctico.
    def peek(self, offset: int = 0) -> Optional[Token]:
        pos = self.posicion + offset
        return self.tokens[pos] if pos < len(self.tokens) else None
    #construye un nodo del árbol (recursivo).
    def advance(self) -> Optional[Token]:
        t = self.peek()
        self.posicion += 1
        return t
    #Obtiene el simbolo de la operacion con la tabla que establecimos arriba 
    def esperar(self, tipo: str) -> bool:
        t = self.peek()
        return bool(t and t.tipo == tipo)
    #valida que el token actual sea del tipo esperado, si no, lanza error.
    def consumir(self, tipo: str) -> Token:
        if not self.esperar(tipo):
            raise Exception(f"Se esperaba {tipo}, se encontró {self.peek().tipo if self.peek() else 'EOF'}")# type: ignore
        return self.advance()# type: ignore
    #Extrae el tipo de operacion
    def extraer_tipo_operacion(self, lexema: str) -> str:
        if '=' not in lexema:
            return ""
        try:
            partes = lexema.split('=', 1)
            if len(partes) != 2:
                return ""
            tipo = partes[1].replace('>', '').strip().upper()
            return tipo
        except Exception:
            return ""

    def parsear(self) -> List[Union[NodoOperacion, float]]:
        operaciones = []
        while self.posicion < len(self.tokens):
            t = self.peek()
            if t is None or t.tipo == "EOF":
                break
            if t.tipo == "ETIQUETA_ABIERTA":
                lex = t.lexema
                if "Operacion" in lex or "OPERACION" in lex:
                    operaciones.append(self.parsear_operacion(nivel=0))
                elif "Numero" in lex or "NUMERO" in lex:
                    operaciones.append(self.parsear_numero())
                else:
                    self.advance()
            else:
                self.advance()
        if len(operaciones) == 1:
            return operaciones[0]
        elif len(operaciones) > 1:
            return operaciones
        else:
            raise Exception("No se encontraron operaciones para analizar")
    #valida y retorna las operaaciones en caso se pueda.
    """
    Analiza una operacion a partir de una etiqueta <Operacion=...>.
    Si contiene operaciones anidadas, las procesa recursivamente.
    'nivel' indica si la operacion es raíz o interna.
    Retorna un objeto NodoOperacion con su tipo y operandos.

    """
    def parsear_operacion(self, nivel: int = 0) -> NodoOperacion:
        etiqueta = self.consumir("ETIQUETA_ABIERTA")
        tipo_op = self.extraer_tipo_operacion(etiqueta.lexema).upper()
        nodo: NodoOperacion
        if not tipo_op or tipo_op not in OPER_MAP:
        # nodo inválido (marca válido = False). Guardamos ? como tipo visual.
            nodo = NodoOperacion('?', [], valido=False)
        else:
            nodo = NodoOperacion(OPER_MAP[tipo_op], [], valido=True)

        # Capturar coordenadas de la etiqueta raíz
        nodo.fila = etiqueta.fila
        nodo.columna = etiqueta.columna

        # parsear contenido hasta etiqueta de cierre </Operacion>
        while self.posicion < len(self.tokens):
            t = self.peek()
            if t is None:
                nodo.valido = False
                raise Exception("Token EOF inesperado")
            if t.tipo == "ETIQUETA_CERRADA" and ("Operacion" in t.lexema or "OPERACION" in t.lexema):
                self.consumir("ETIQUETA_CERRADA")
                break
            elif t.tipo == "ETIQUETA_ABIERTA" and ("<Numero>" in t.lexema or "<NUMERO>" in t.lexema):
                try:
                    num = self.parsear_numero()
                    nodo.operandos.append(num)
                except Exception:
                    nodo.valido = False
                    # consumir para sincronizar si es preciso
            elif t.tipo == "ETIQUETA_ABIERTA" and ("<Operacion" in t.lexema or "<OPERACION" in t.lexema):
                try:
                    hijo = self.parsear_operacion(nivel + 1)
                    nodo.operandos.append(hijo)
                    if isinstance(hijo, NodoOperacion) and not hijo.valido:
                        nodo.valido = False
                except Exception:
                    nodo.valido = False
                    # intentar avanzar para no quedarse en bucle
                    try:
                        self.advance()
                    except:
                        pass
            elif t.tipo == "ETIQUETA_ABIERTA" and ("<P>" in t.lexema or "<P" in t.lexema):
                try:
                    p = self.parsear_parametro_p()
                    nodo.operandos.insert(0, p)
                except Exception:
                    nodo.valido = False
            elif t.tipo == "ETIQUETA_ABIERTA" and ("<R>" in t.lexema or "<R" in t.lexema):
                try:
                    r = self.parsear_parametro_r()
                    nodo.operandos.insert(0, r)
                except Exception:
                    nodo.valido = False
            else:
                # avanzar para evitar bucle
                self.advance()

        # si no hay operandos, marcar inválido
        if not nodo.operandos:
            nodo.valido = False

        return nodo
    #valida y retorna numeros como operandos.
    def parsear_numero(self) -> float:
        self.consumir("ETIQUETA_ABIERTA")
        valor = 0.0
        if self.esperar("NUMERO"):
            tok = self.advance()
            try:
                valor = float(tok.lexema)# type: ignore
            except Exception:
                raise Exception(f"Valor numérico inválido: {tok.lexema}")# type: ignore
        self.consumir("ETIQUETA_CERRADA")
        return valor
    #parametros de etiqueta abierta o cerrada
    def parsear_parametro_p(self) -> float:
        self.consumir("ETIQUETA_ABIERTA")
        valor = 0.0
        if self.esperar("NUMERO"):
            valor = float(self.advance().lexema)# type: ignore
        self.consumir("ETIQUETA_CERRADA")
        return valor
    
    def parsear_parametro_r(self) -> float:
        self.consumir("ETIQUETA_ABIERTA")
        valor = 0.0
        if self.esperar("NUMERO"):
            valor = float(self.advance().lexema)# type: ignore
        self.consumir("ETIQUETA_CERRADA")
        return valor

class Evaluador:
    def __init__(self):
        pass
    #aplica la operación correspondiente al tipo del nodo.

    """
    Evalua recursivamente el arbol de operaciones.
    Cada nodo representa un operador y sus operandos.
    Retorna el resultado numerico final.
    """
    def evaluar(self, nodo: Union[NodoOperacion, float, List]) -> Union[float, List[float]]:
        if isinstance(nodo, list):
            res = []
            for op in nodo:
                res.append(self.evaluar(op))
            return res
        if isinstance(nodo, (int, float)):
            return float(nodo)
        if isinstance(nodo, NodoOperacion):
            if not nodo.valido:
                raise Exception("Operación marcada como inválida (error en alguna parte del árbol)")
            if nodo.tipo == '+':
                return self.suma(nodo.operandos)
            if nodo.tipo == '-':
                return self.resta(nodo.operandos)
            if nodo.tipo == '*':
                return self.multiplicacion(nodo.operandos)
            if nodo.tipo == '/':
                return self.division(nodo.operandos)
            if nodo.tipo == '^':
                return self.potencia(nodo.operandos)
            if nodo.tipo == 'r':
                return self.raiz(nodo.operandos)
            if nodo.tipo == 'i':
                return self.inverso(nodo.operandos)
            if nodo.tipo == '%':
                return self.modulo(nodo.operandos)
        raise Exception(f"Tipo de nodo desconocido: {type(nodo)}")
    #Realiza la suma
    def suma(self, operandos: List) -> float:
        total = 0.0
        for op in operandos:
            total += self.evaluar(op)# type: ignore
        return total
    #Realiza la resta
    def resta(self, operandos: List) -> float:
        if not operandos:
            return 0.0
        total = self.evaluar(operandos[0])
        for op in operandos[1:]:
            total -= self.evaluar(op)# type: ignore
        return total# type: ignore
    #Realiza la multiplicacion
    def multiplicacion(self, operandos: List) -> float:
        total = 1.0
        for op in operandos:
            total *= self.evaluar(op)# type: ignore
        return total
    #Realiza la divicion
    def division(self, operandos: List) -> float:
        if not operandos:
            return 0.0
        total = self.evaluar(operandos[0])
        for op in operandos[1:]:
            div = self.evaluar(op)
            if div == 0:
                raise Exception("División por cero")
            total /= div# type: ignore
        return total# type: ignore
    #Realiza la potencia
    def potencia(self, operandos: List) -> float:
        if len(operandos) < 2:
            raise Exception("POTENCIA requiere 2 operandos")
        ex = self.evaluar(operandos[0])
        base = self.evaluar(operandos[1])
        return base ** ex# type: ignore
    #Realiza la raiz
    def raiz(self, operandos: List) -> float:
        if len(operandos) < 2:
            raise Exception("RAIZ requiere 2 operandos")
        indice = self.evaluar(operandos[0])
        rad = self.evaluar(operandos[1])
        if indice == 0:
            raise Exception("Índice de raíz no puede ser cero")
        if rad < 0 and int(indice) % 2 == 0:# type: ignore
            raise Exception("Raíz par de número negativo")
        return rad ** (1 / indice)# type: ignore
    #Realiza la inversion (creo que esto esta mal escrito porque tecnicamente en artmetica es raiz/potencia pero hay se pregunta a la ingeniera)
    def inverso(self, operandos: List) -> float:
        if not operandos:
            raise Exception("INVERSO requiere 1 operando")
        val = self.evaluar(operandos[0])
        if val == 0:
            raise Exception("Inverso de cero")
        return 1.0 / val# type: ignore
    #Realiza las modificaciones
    def modulo(self, operandos: List) -> float:
        if len(operandos) < 2:
            raise Exception("MOD requiere 2 operandos")
        res = int(self.evaluar(operandos[0]))# type: ignore
        for op in operandos[1:]:
            d = int(self.evaluar(op))# type: ignore
            if d == 0:
                raise Exception("MOD: divisor cero")
            res = res % d
        return float(res)
    #Realiza la exprecion final para la tabla de expresiones y posterior jala para el HTML

    def generar_expresion(self, nodo: Union[NodoOperacion, float, List]) -> str:
        if isinstance(nodo, list):
            exprs = []
            for i, op in enumerate(nodo, 1):
                exprs.append(f"{i}. {self.generar_expresion(op)}")
            return "\n".join(exprs)
        if isinstance(nodo, (int, float)):
            if isinstance(nodo, float) and nodo.is_integer():
                return str(int(nodo))
            return str(nodo)
        if isinstance(nodo, NodoOperacion):
            operandos_str = [self.generar_expresion(op) for op in nodo.operandos]
            op = nodo.tipo
            if op == '+':
                return "(" + "+".join(operandos_str) + ")"
            if op == '-':
                return "(" + "-".join(operandos_str) + ")"
            if op == '*':
                return "(" + "*".join(operandos_str) + ")"
            if op == '/':
                return "(" + "/".join(operandos_str) + ")"
            if op == '^':
                if len(operandos_str) >= 2:
                    return f"({operandos_str[1]}^{operandos_str[0]})"
                return "(potencia_error)"
            if op == 'r':
                if len(operandos_str) >= 2:
                    return f"(√[{operandos_str[0]}]{operandos_str[1]})"
                return "(raiz_error)"
            if op == 'i':
                if operandos_str:
                    return f"(1/{operandos_str[0]})"
                return "(inverso_error)"
            if op == '%':
                return "(" + "%".join(operandos_str) + ")"
        return str(nodo)

# ============================================================================ 
# INTERFAZ GRÁFICA (Tkinter) - incluye pestaña "Errores" con la tabla solicitada
# ============================================================================
#lo mas complicado apare del HTML y el grafo de arboles

class AnalizadorGUI:
    #que construye la ventana principal y todas las pestañas (Resultados, Errores, Árbol). es el corazon :)
    def __init__(self, root):
        self.root = root
        self.root.title("Analizador de Operaciones Aritméticas - LFA 2025")
        self.root.geometry("1200x800")
        self.root.config(bg="#f0f0f0")

        self.archivo_actual = None
        self.arbol_actual = None
        self.evaluador_actual = None
        self.tokens_actual: List[Token] = []
        self.scanner_actual: Optional[ScannerLexico] = None
        self.ultimos_errores_operaciones: List[tuple] = []  # (idx, mensaje, fila, columna)

        self.crear_widgets()
        self.ruta_manual_usuario = os.path.join(os.path.dirname(__file__), "ManualUsuario.pdf")
        self.ruta_manual_tecnico = os.path.join(os.path.dirname(__file__), "ManualTecnico.pdf")

    def crear_widgets(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        archivo_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=archivo_menu)
        archivo_menu.add_command(label="Abrir", command=self.abrir_archivo)
        archivo_menu.add_command(label="Guardar", command=self.guardar_archivo)
        archivo_menu.add_command(label="Guardar Como", command=self.guardar_como)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Exportar HTML", command=self.exportar_html)
        archivo_menu.add_separator()
        archivo_menu.add_command(label="Salir", command=self.root.quit)

        ayuda_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ayuda", menu=ayuda_menu)
        ayuda_menu.add_command(label="Acerca de", command=self.acerca_de)

        frame_top = tk.Frame(self.root, bg="#f0f0f0")
        frame_top.pack(pady=10)

        tk.Button(frame_top, text="Abrir", command=self.abrir_archivo, width=12, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_top, text="Guardar", command=self.guardar_archivo, width=12, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_top, text="Guardar Como", command=self.guardar_como, width=12, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_top, text="Analizar", command=self.analizar, width=12, bg="#FF9800", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_top, text="Exportar HTML", command=self.exportar_html, width=12, bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_top, text="Manual de Usuario (PDF)", command=self.mostrar_manual_usuario, width=18, bg="#607D8B", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_top, text="Manual Técnico (PDF)", command=self.mostrar_manual_tecnico, width=18, bg="#607D8B", fg="white").pack(side=tk.LEFT, padx=5)

        frame_main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        frame_main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Panel izquierdo - editor de entrada
        frame_left = ttk.Frame(frame_main)
        frame_main.add(frame_left, weight=1)

        tk.Label(frame_left, text="Código Fuente:", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(anchor=tk.W)
        self.entrada_text = scrolledtext.ScrolledText(frame_left, height=25, width=45, font=("Courier", 10))
        self.entrada_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Panel derecho - notebook con resultados y errores
        frame_right = ttk.Frame(frame_main)
        frame_main.add(frame_right, weight=1)

        tk.Label(frame_right, text="Resultados:", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(anchor=tk.W)
        self.notebook = ttk.Notebook(frame_right)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # Tab tokens
        self.tab_tokens = scrolledtext.ScrolledText(self.notebook, height=15, width=45, font=("Courier", 9))
        self.notebook.add(self.tab_tokens, text="Tokens")

        # Tab árbol
        frame_tree = ttk.Frame(self.notebook)
        self.notebook.add(frame_tree, text="Árbol")
        frame_tree_buttons = ttk.Frame(frame_tree)
        frame_tree_buttons.pack(pady=10)
        self.label_arbol_info = tk.Label(frame_tree, text="", font=("Arial", 10, "bold"), bg="white")
        self.label_arbol_info.pack()
        tk.Button(frame_tree_buttons, text="← Anterior", command=self.anterior_arbol, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_tree_buttons, text="Siguiente →", command=self.siguiente_arbol, width=15).pack(side=tk.LEFT, padx=5)
        self.canvas_arbol = tk.Canvas(frame_tree, bg="white", highlightthickness=0)
        self.canvas_arbol.pack(fill=tk.BOTH, expand=True)
        self.arbol_index_actual = 0

        # Tab expresion y resultado
        self.tab_expresion = scrolledtext.ScrolledText(self.notebook, height=15, width=45, font=("Courier", 10))
        self.notebook.add(self.tab_expresion, text="Expresión y Resultado")

        # Tab errores (tabla en el formato pedido)
        frame_errores = ttk.Frame(self.notebook)
        self.notebook.add(frame_errores, text="Errores")

        columns = ("No", "Lexema", "Tipo", "COLUMNA", "FILA")
        self.tree_errores = ttk.Treeview(frame_errores, columns=columns, show="headings", height=18)
        for col in columns:
            self.tree_errores.heading(col, text=col)
            # Anchos: No pequeño, Lexema mediano, Tipo mediano, COLUMNA/FILA pequeños
            if col == "No":
                self.tree_errores.column(col, width=40, anchor="center")
            elif col == "Lexema":
                self.tree_errores.column(col, width=120, anchor="w")
            elif col == "Tipo":
                self.tree_errores.column(col, width=120, anchor="w")
            else:
                self.tree_errores.column(col, width=70, anchor="center")

        scrollbar_err = ttk.Scrollbar(frame_errores, orient=tk.VERTICAL, command=self.tree_errores.yview)
        self.tree_errores.configure(yscroll=scrollbar_err.set)# type: ignore
        self.tree_errores.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_err.pack(side=tk.RIGHT, fill=tk.Y)

    # ----------------------- Gestión de archivos -----------------------
    #abre un archivo ya existente
    def abrir_archivo(self):
        archivo = filedialog.askopenfilename(filetypes=[("Texto", "*.txt"), ("XML", "*.xml"), ("Todos", "*.*")])
        if archivo:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
            self.entrada_text.delete(1.0, tk.END)
            self.entrada_text.insert(1.0, contenido)
            self.archivo_actual = archivo
            self.root.title(f"Analizador - {os.path.basename(archivo)}")
    #guarda el archivo que abriste
    def guardar_archivo(self):
        if not self.archivo_actual:
            self.guardar_como()
            return
        contenido = self.entrada_text.get(1.0, tk.END)
        with open(self.archivo_actual, 'w', encoding='utf-8') as f:
            f.write(contenido)
        messagebox.showinfo("Éxito", "Archivo guardado correctamente")
    #guarda de otra forma o en otra carpeta un arcivo
    def guardar_como(self):
        archivo = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texto", "*.txt"), ("XML", "*.xml"), ("Todos", "*.*")])
        if archivo:
            contenido = self.entrada_text.get(1.0, tk.END)
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write(contenido)
            self.archivo_actual = archivo
            self.root.title(f"Analizador - {os.path.basename(archivo)}")
            messagebox.showinfo("Éxito", "Archivo guardado correctamente")

    # ----------------------- Helpers para parsing parcial -----------------------
    def _extraer_subtokens_operacion(self, tokens: List[Token], start_idx: int) -> List[Token]:
        subtokens: List[Token] = []
        i = start_idx
        profundidad = 0
        last_token = None
        while i < len(tokens):
            t = tokens[i]
            subtokens.append(t)
            last_token = t
            if t.tipo == "ETIQUETA_ABIERTA" and ("Operacion" in t.lexema or "OPERACION" in t.lexema):
                profundidad += 1
            elif t.tipo == "ETIQUETA_CERRADA" and ("Operacion" in t.lexema or "OPERACION" in t.lexema):
                profundidad -= 1
                if profundidad == 0:
                    break
            i += 1
        if last_token:
            subtokens.append(Token("EOF", "", last_token.fila, last_token.columna))
        else:
            subtokens.append(Token("EOF", "", 0, 0))
        return subtokens

    # ----------------------- Análisis (principal) -----------------------
    #llama al scanner, parser y evaluador, llena las pestañas, y genera reportes.
    def analizar(self):
        texto = self.entrada_text.get(1.0, tk.END)
        try:
            self.arbol_index_actual = 0
            self.ultimos_errores_operaciones = []

            # Léxico
            self.scanner_actual = ScannerLexico(texto)
            self.tokens_actual = self.scanner_actual.scanear()

            # Mostrar tokens
            self.tab_tokens.delete(1.0, tk.END)
            for token in self.tokens_actual:
                if token.tipo != "EOF":
                    self.tab_tokens.insert(tk.END, f"{token.tipo:20} | {token.lexema:30} | Fila:{token.fila} Col:{token.columna}\n")

            # Intento de parse global
            operaciones_brutas = None
            try:
                parser = Parser(self.tokens_actual)
                operaciones_brutas = parser.parsear()
            except Exception:
                operaciones_brutas = None

            operaciones_validas = []
            errores_operaciones = []

            if operaciones_brutas is not None:
                if isinstance(operaciones_brutas, list):
                    lista_raices = operaciones_brutas
                else:
                    lista_raices = [operaciones_brutas]
                evaluador = Evaluador()
                for idx, raiz in enumerate(lista_raices, 1):
                    # si parser ya marcó inválida
                    if isinstance(raiz, NodoOperacion) and not raiz.valido:
                        fila = getattr(raiz, "fila", "-")
                        col = getattr(raiz, "columna", "-")
                        errores_operaciones.append((idx, "Operación inválida (error en alguna parte del árbol)", fila, col))
                        continue
                    try:
                        _ = evaluador.evaluar(raiz)
                        operaciones_validas.append(raiz)
                    except Exception as e_eval:
                        # incluir fila/columna si están disponibles
                        fila = getattr(raiz, "fila", "-")
                        col = getattr(raiz, "columna", "-")
                        errores_operaciones.append((idx, str(e_eval), fila, col))
            else:
                # fallback: extraer por raíces desde tokens
                indices = []
                for i, tok in enumerate(self.tokens_actual):
                    if tok.tipo == "ETIQUETA_ABIERTA" and ("Operacion" in tok.lexema or "OPERACION" in tok.lexema):
                        indices.append(i)
                evaluador = Evaluador()
                contador = 0
                for si in indices:
                    contador += 1
                    try:
                        subtoks = self._extraer_subtokens_operacion(self.tokens_actual, si)
                        parser_sub = Parser(subtoks)
                        nodo = parser_sub.parsear()
                        if isinstance(nodo, NodoOperacion) and not nodo.valido:
                            fila = getattr(nodo, "fila", self.tokens_actual[si].fila if si < len(self.tokens_actual) else "-")
                            col = getattr(nodo, "columna", self.tokens_actual[si].columna if si < len(self.tokens_actual) else "-")
                            errores_operaciones.append((contador, "Operación inválida (error en alguna parte del árbol)", fila, col))
                            continue
                        try:
                            _ = evaluador.evaluar(nodo)
                            operaciones_validas.append(nodo)
                        except Exception as e_eval:
                            fila = getattr(nodo, "fila", self.tokens_actual[si].fila if si < len(self.tokens_actual) else "-")
                            col = getattr(nodo, "columna", self.tokens_actual[si].columna if si < len(self.tokens_actual) else "-")
                            errores_operaciones.append((contador, str(e_eval), fila, col))
                    except Exception as e_sub:
                        # si no pudimos extraer posición, intentar usar el token de inicio
                        fila = self.tokens_actual[si].fila if si < len(self.tokens_actual) else "-"
                        col = self.tokens_actual[si].columna if si < len(self.tokens_actual) else "-"
                        errores_operaciones.append((contador, str(e_sub), fila, col))

            # Guardar árbol final con solo raíces válidas
            if not operaciones_validas:
                self.arbol_actual = None
            elif len(operaciones_validas) == 1:
                self.arbol_actual = operaciones_validas[0]
            else:
                self.arbol_actual = operaciones_validas

            # Guardar errores (para HTML y GUI)
            self.ultimos_errores_operaciones = errores_operaciones

            # Mostrar expresiones válidas con 3 decimales
            self.evaluador_actual = Evaluador()
            self.tab_expresion.delete(1.0, tk.END)

            if self.arbol_actual is None:
                contenido = "No se analizaron operaciones válidas.\n"
                if errores_operaciones:
                    contenido += "Operaciones con errores:\n"
                    for idx, msg, fila, col in errores_operaciones:
                        contenido += f"- Operación {idx} (fila {fila}, col {col}): {msg}\n"
                self.tab_expresion.insert(1.0, contenido)
            else:
                if isinstance(self.arbol_actual, list):
                    contenido = ""
                    for i, op in enumerate(self.arbol_actual, 1):
                        try:
                            res = self.evaluador_actual.evaluar(op)
                            expr = self.evaluador_actual.generar_expresion(op)
                            contenido += f"{i}. {expr} = {res:.3f}\n"
                        except Exception as e_eval:
                            fila = getattr(op, "fila", "-")
                            col = getattr(op, "columna", "-")
                            errores_operaciones.append((i, str(e_eval), fila, col))
                    self.tab_expresion.insert(1.0, contenido)
                else:
                    try:
                        res = self.evaluador_actual.evaluar(self.arbol_actual)
                        expr = self.evaluador_actual.generar_expresion(self.arbol_actual)
                        self.tab_expresion.insert(1.0, f"1. {expr} = {res:.3f}")
                    except Exception as e_eval:
                        fila = getattr(self.arbol_actual, "fila", "-")
                        col = getattr(self.arbol_actual, "columna", "-")
                        errores_operaciones.append((1, str(e_eval), fila, col))
                        self.tab_expresion.insert(1.0, "No se pudo evaluar la operación válida encontrada.\n")

            # Mostrar árbol visual (solo válidos)
            self.mostrar_arbol_visual()

            # Llenar tabla de errores en GUI con formato pedido (No, Lexema, Tipo, COLUMNA, FILA)
            self.tree_errores.delete(*self.tree_errores.get_children())
            fila_no = 1
            # primero errores léxicos del scanner
            if self.scanner_actual and self.scanner_actual.errores:
                for err in self.scanner_actual.errores:
                    # err contiene keys: No, Lexema, Tipo, Columna, Fila, Mensaje
                    # USO: mostrar el número que ya asignó el scanner si existe, sino fila_no
                    self.tree_errores.insert('', tk.END, values=(
                        err.get("No", fila_no),
                        err.get("Lexema", ""),
                        err.get("Tipo", "Error"),
                        err.get("Columna", "-"),
                        err.get("Fila", "-")
                    ))
                    fila_no += 1
            # luego errores de operación (ahora con fila/columna)
            if self.ultimos_errores_operaciones:
                for idx, msg, fila, col in self.ultimos_errores_operaciones:
                    display_fila = fila if fila is not None else "-"
                    display_col = col if col is not None else "-"
                    self.tree_errores.insert('', tk.END, values=(
                        fila_no,
                        f"Operacion {idx}",
                        "Error",
                        display_col,
                        display_fila
                    ))
                    fila_no += 1
            if fila_no == 1:
                # sin errores
                self.tree_errores.insert('', tk.END, values=("-", "-", "✓", "-", "-"))

            # Mensaje final con todos los errores de operación (si existen)
            if self.ultimos_errores_operaciones:
                mensaje = "Análisis completado con errores:\n"
                for idx, msg, fila, col in self.ultimos_errores_operaciones:
                    mensaje += f"- Operación {idx} (fila {fila}, col {col}): {msg}\n"
                if operaciones_validas:
                    mensaje += "Las demás operaciones se procesaron correctamente."
                else:
                    mensaje += "No se procesaron operaciones correctamente."
                messagebox.showwarning("Análisis con errores", mensaje)
            else:
                total_ops = len(operaciones_validas) if operaciones_validas else 0
                messagebox.showinfo("Éxito", f"Análisis completado exitosamente\n\nOperaciones analizadas correctamente: {total_ops}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.tree_errores.delete(*self.tree_errores.get_children())
            self.tree_errores.insert('', tk.END, values=(1, "", "Error de Parsing", "-", "-"))
            self.tab_expresion.delete(1.0, tk.END)
            self.canvas_arbol.delete("all")
            messagebox.showerror("Error", f"Error durante el análisis:\n{str(e)}")

    # ----------------------- Visualización del árbol -----------------------
    def generar_arbol_canvas(self, nodo: Union[NodoOperacion, float], x: float = 250, y: float = 30,
                            offset: float = 100, canvas = None) -> float:
        if canvas is None:
            return x
        if isinstance(nodo, (int, float)):
            canvas.create_rectangle(x-35, y-20, x+35, y+20, fill="white", outline="black", width=2)
            canvas.create_text(x, y, text=f"{nodo:.2f}" if isinstance(nodo, float) else str(nodo),
                               font=("Arial", 9))
            return x
        if isinstance(nodo, NodoOperacion):
            num_hijos = len(nodo.operandos) if nodo.operandos else 0
            if num_hijos == 0:
                rect_color = "red" if not nodo.valido else "black"
                canvas.create_rectangle(x-50, y-25, x+50, y+25, fill="white", outline=rect_color, width=2)
                canvas.create_text(x, y, text=nodo.tipo if nodo.tipo else "?", font=("Arial", 9, "bold"), width=90)
            else:
                total_width = num_hijos * offset
                inicio_x = x - total_width // 2
                posiciones = []
                for i, operando in enumerate(nodo.operandos):
                    hijo_x = inicio_x + i * offset + offset // 2
                    canvas.create_line(x, y + 30, hijo_x, y + 70, fill="black", width=1)
                    posiciones.append(hijo_x)
                rect_color = "red" if not nodo.valido else "black"
                canvas.create_rectangle(x-50, y-25, x+50, y+25, fill="white", outline=rect_color, width=2)
                canvas.create_text(x, y, text=nodo.tipo if nodo.tipo else "?", font=("Arial", 11, "bold"), width=90)
                for i, operando in enumerate(nodo.operandos):
                    new_offset = max(50, int(offset // 1.5))
                    self.generar_arbol_canvas(operando, posiciones[i], y + 100, new_offset, canvas)
            return x
        return x

    def anterior_arbol(self):
        if isinstance(self.arbol_actual, list):
            if self.arbol_index_actual > 0:
                self.arbol_index_actual -= 1
                self.mostrar_arbol_visual()

    def siguiente_arbol(self):
        if isinstance(self.arbol_actual, list):
            if self.arbol_index_actual < len(self.arbol_actual) - 1:
                self.arbol_index_actual += 1
                self.mostrar_arbol_visual()

    def calcular_altura_arbol(self, nodo: Union[NodoOperacion, float]) -> int:
        if isinstance(nodo, (int, float)):
            return 1
        if isinstance(nodo, NodoOperacion):
            if not nodo.operandos:
                return 1
            max_altura = max(self.calcular_altura_arbol(op) for op in nodo.operandos)
            return max_altura + 1
        return 1

    def mostrar_arbol_visual(self):
        try:
            self.canvas_arbol.delete("all")
            arbol = self.arbol_actual
            titulo = ""
            if isinstance(self.arbol_actual, list):
                if len(self.arbol_actual) > 0:
                    if self.arbol_index_actual >= len(self.arbol_actual):
                        self.arbol_index_actual = len(self.arbol_actual) - 1
                    if self.arbol_index_actual < 0:
                        self.arbol_index_actual = 0
                    arbol = self.arbol_actual[self.arbol_index_actual]
                    num_act = self.arbol_index_actual + 1
                    total_ops = len(self.arbol_actual)
                    titulo = f"Mostrando operación {num_act} de {total_ops}"
                    self.label_arbol_info.config(text=titulo)
            else:
                self.label_arbol_info.config(text="Árbol de operación única")
            if arbol is None:
                return
            altura = self.calcular_altura_arbol(arbol) * 100 + 50# type: ignore
            self.canvas_arbol.config(scrollregion=(0, 0, 800, max(altura, 400)))
            self.generar_arbol_canvas(arbol, y=50, canvas=self.canvas_arbol)# type: ignore
        except Exception as e:
            self.canvas_arbol.delete("all")
            self.canvas_arbol.create_text(250, 200, text=f"Error al generar árbol:\n{str(e)}", fill="red", font=("Arial", 10))

    # ----------------------- Exportar HTML -----------------------
    #genera archivos HTML con los resultados, errores y árbol.
    def exportar_html(self):
        if self.arbol_actual is None and not (self.scanner_actual and self.scanner_actual.errores):
            messagebox.showwarning("Advertencia", "No hay resultados válidos ni errores para exportar. Primero analiza el código.")
            return
        carpeta = filedialog.askdirectory(title="Seleccione la carpeta donde guardar Resultados.html y Errores.html")
        if not carpeta:
            return
        try:
            # Resultados (solo válidos)
            if self.arbol_actual is None:
                resultados_rows = "<tr><td colspan='3' style='text-align:center; color:red;'>No hay resultados válidos</td></tr>\n"
                total_ops = 0
            else:
                expresion_full = self.evaluador_actual.generar_expresion(self.arbol_actual)# type: ignore
                resultado_full = self.evaluador_actual.evaluar(self.arbol_actual)# type: ignore
                resultados_rows = ""
                if isinstance(resultado_full, list):
                    lineas = expresion_full.split('\n')
                    for idx, (linea, res) in enumerate(zip(lineas, resultado_full), 1):
                        expr_pura = linea.split('. ', 1)[1] if '. ' in linea else linea
                        resultados_rows += f"<tr><td>{idx}</td><td>{expr_pura}</td><td>{res:.3f}</td></tr>\n"
                else:
                    resultados_rows += f"<tr><td>1</td><td>{expresion_full}</td><td>{resultado_full:.3f}</td></tr>\n"
                total_ops = len(resultado_full) if isinstance(resultado_full, list) else 1

            resultados_html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><title>Resultados - Operaciones</title>
<style>body{{font-family:Arial,sans-serif;padding:20px;background:#f6f6f6}}.container{{background:#fff;padding:20px;border-radius:8px}}</style>
</head><body><div class="container"><h1>Resultados de Operaciones</h1><p>Total de operaciones: <strong>{total_ops}</strong></p>
<table border="1" cellpadding="6" style="border-collapse:collapse;"><thead><tr><th>#</th><th>Expresión</th><th>Resultado</th></tr></thead><tbody>
{resultados_rows}
</tbody></table></div></body></html>"""
            resultados_path = os.path.join(carpeta, "Resultados.html")
            with open(resultados_path, 'w', encoding='utf-8') as f:
                f.write(resultados_html)

            # Errores: combinar errores léxicos + errores de operación en la tabla con encabezado No | Lexema | Tipo | COLUMNA | FILA
            errores_rows_html = ""
            # errores léxicos
            if self.scanner_actual and self.scanner_actual.errores:
                for err in self.scanner_actual.errores:
                    errores_rows_html += "<tr>"
                    errores_rows_html += f"<td>{err.get('No','')}</td>"
                    errores_rows_html += f"<td>{err.get('Lexema','')}</td>"
                    errores_rows_html += f"<td>{err.get('Tipo','Error')}</td>"
                    errores_rows_html += f"<td>{err.get('Columna','-')}</td>"
                    errores_rows_html += f"<td>{err.get('Fila','-')}</td>"
                    errores_rows_html += "</tr>\n"
            # errores de operación
            start_num = len(self.scanner_actual.errores) if (self.scanner_actual and self.scanner_actual.errores) else 0
            if self.ultimos_errores_operaciones:
                for i, (idx, msg, fila, col) in enumerate(self.ultimos_errores_operaciones, 1):
                    errores_rows_html += "<tr>"
                    errores_rows_html += f"<td>{start_num + i}</td>"
                    errores_rows_html += f"<td>Operacion {idx}</td>"
                    errores_rows_html += f"<td>Error</td>"
                    errores_rows_html += f"<td>{col if col is not None else '-'}</td>"
                    errores_rows_html += f"<td>{fila if fila is not None else '-'}</td>"
                    errores_rows_html += "</tr>\n"
            if errores_rows_html == "":
                errores_rows_html = "<tr><td colspan='5' style='text-align:center;color:green;'>✓ No hay errores</td></tr>\n"

            errores_html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><title>Errores</title>
<style>body{{font-family:Arial,sans-serif;padding:20px;background:#f6f6f6}}.container{{background:#fff;padding:20px;border-radius:8px}}</style>
</head><body><div class="container"><h1>Errores Léxicos y de Operación</h1>
<table border="1" cellpadding="6" style="border-collapse:collapse;"><thead><tr><th>No</th><th>Lexema</th><th>Tipo</th><th>COLUMNA</th><th>FILA</th></tr></thead><tbody>
{errores_rows_html}
</tbody></table></div></body></html>"""
            errores_path = os.path.join(carpeta, "Errores.html")
            with open(errores_path, 'w', encoding='utf-8') as f:
                f.write(errores_html)

            messagebox.showinfo("Éxito", f"Archivos generados:\n- {resultados_path}\n- {errores_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar HTML:\n{str(e)}")

    # ----------------------- Abrir manuales -----------------------
    #Muestra el manual de usuario
    def mostrar_manual_usuario(self):
        if os.path.exists(self.ruta_manual_usuario):
            try:
                if os.name == 'nt':
                    os.startfile(self.ruta_manual_usuario)
                else:
                    opener = "open" if sys.platform == "darwin" else "xdg-open"
                    subprocess.Popen([opener, self.ruta_manual_usuario])
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el Manual de Usuario:\n{str(e)}")
        else:
            messagebox.showerror("Error", f"No se encontró el archivo:\n{self.ruta_manual_usuario}")
    #Muestra el manual tecnico
    def mostrar_manual_tecnico(self):
        if os.path.exists(self.ruta_manual_tecnico):
            try:
                if os.name == 'nt':
                    os.startfile(self.ruta_manual_tecnico)
                else:
                    opener = "open" if sys.platform == "darwin" else "xdg-open"
                    subprocess.Popen([opener, self.ruta_manual_tecnico])
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el Manual Técnico:\n{str(e)}")
        else:
            messagebox.showerror("Error", f"No se encontró el archivo:\n{self.ruta_manual_tecnico}")

    def _abrir_archivo_externo(self, ruta):
        try:
            if os.name == 'nt':
                os.startfile(ruta)
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.Popen([opener, ruta])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el archivo:\n{str(e)}")
    #las ayudas que peria la ingeniera arriba a la izquiera se mira
    def acerca_de(self):
        messagebox.showinfo("Acerca de",
            "Analizador de Operaciones Aritméticas\n\n"
            "Versión: 1.0\n"
            "Fase 2 - Proyecto LFA 2025\n\n"
            "Funcionalidades:\n"
            "Análisis Léxico\n"
            "Análisis Sintáctico\n"
            "Evaluación de Operaciones\n"
            "Visualización de Árbol\n"
            "Exportación a HTML\n"
            "Reporte de Errores\n"
            "Creadores:\n"
            "Rodrigo Ruiz - 1037623\n"
            "Pablo Cossio - 1054723\n")

# ----------------------- MAIN -----------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = AnalizadorGUI(root)
    root.mainloop()
