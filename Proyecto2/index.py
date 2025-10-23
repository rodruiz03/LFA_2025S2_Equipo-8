import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import os
from dataclasses import dataclass
from typing import List, Optional, Union

# ============================================================================
# CLASES DEL ANALIZADOR
# ============================================================================

@dataclass
class Token:
    tipo: str
    lexema: str
    fila: int
    columna: int

class ScannerLexico:
    PALABRAS_RESERVADAS = {'SUMA', 'RESTA', 'MULTIPLICACION', 'DIVISION', 'POTENCIA', 'RAIZ', 'INVERSO', 'MOD'}
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
        char = self.texto[self.posicion]
        self.posicion += 1
        if char == '\n':
            self.fila += 1
            self.columna = 1
        else:
            self.columna += 1
        return char
    
    def es_digito(self, char: Optional[str]) -> bool:
        return char is not None and '0' <= char <= '9'
    
    def es_letra(self, char: Optional[str]) -> bool:
        return char is not None and (('A' <= char <= 'Z') or ('a' <= char <= 'z'))
    
    def es_espacio(self, char: Optional[str]) -> bool:
        return char in (' ', '\t', '\n', '\r')
    
    def registrar_error(self, mensaje: str, fila: int, columna: int, lexema: str):
        self.errores.append({
            'numero': len(self.errores) + 1,
            'lexema': lexema,
            'tipo': 'Error Léxico',
            'columna': columna,
            'fila': fila,
            'mensaje': mensaje
        })
    
    def extraer_numero(self) -> Token:
        inicio_fila = self.fila
        inicio_columna = self.columna
        numero = ""
        
        while self.es_digito(self.peek()):
            numero += self.advance()
        
        if self.peek() == '.':
            numero += self.advance()
            while self.es_digito(self.peek()):
                numero += self.advance()
        
        return Token("NUMERO", numero, inicio_fila, inicio_columna)
    
    def extraer_palabra_o_etiqueta(self) -> Token:
        inicio_fila = self.fila
        inicio_columna = self.columna
        palabra = ""
        
        while self.es_letra(self.peek()) or self.peek() == '_':
            palabra += self.advance()
        
        if palabra in self.PALABRAS_RESERVADAS:
            return Token("PALABRA_RESERVADA", palabra, inicio_fila, inicio_columna)
        
        # Si es una etiqueta, esto significa que fue mal escrita
        if palabra in self.ETIQUETAS:
            return Token("IDENTIFICADOR", palabra, inicio_fila, inicio_columna)
        
        return Token("IDENTIFICADOR", palabra, inicio_fila, inicio_columna)
    
    def extraer_etiqueta_abierta(self) -> Token:
        inicio_fila = self.fila
        inicio_columna = self.columna
        etiqueta_completa = ""
        
        # Consumir <
        etiqueta_completa += self.advance()  # <
        
        # Extraer nombre de etiqueta
        nombre_etiqueta = ""
        while self.es_letra(self.peek()) or self.peek() == '_':
            nombre_etiqueta += self.advance()
        
        # Validar que sea nombre válido
        if nombre_etiqueta not in self.ETIQUETAS:
            self.registrar_error(f"Etiqueta no válida: {nombre_etiqueta}", inicio_fila, inicio_columna, f"<{nombre_etiqueta}")
            # Consumir hasta >
            while self.peek() and self.peek() != '>':
                self.advance()
            if self.peek() == '>':
                self.advance()
            return Token("ETIQUETA_ABIERTA", f"<{nombre_etiqueta}>", inicio_fila, inicio_columna)
        
        etiqueta_completa += nombre_etiqueta
        
        # Si hay =, es una etiqueta con atributo (solo Operacion puede tener)
        if self.peek() == '=':
            etiqueta_completa += self.advance()  # =
            
            # Saltar espacios después del =
            while self.es_espacio(self.peek()) and self.peek() != '\n':
                self.advance()
            
            # Extraer tipo de operación (debe ser palabra reservada)
            tipo_operacion = ""
            while self.es_letra(self.peek()) or self.peek() == '_':
                tipo_operacion += self.advance()
            
            if tipo_operacion not in self.PALABRAS_RESERVADAS:
                self.registrar_error(f"Tipo de operación no válido: {tipo_operacion}", self.fila, self.columna, tipo_operacion)
                while self.peek() and self.peek() != '>':
                    self.advance()
                if self.peek() == '>':
                    self.advance()
                return Token("ETIQUETA_ABIERTA", etiqueta_completa + tipo_operacion + ">", inicio_fila, inicio_columna)
            
            etiqueta_completa += tipo_operacion
        
        # Saltar espacios antes de >
        while self.es_espacio(self.peek()) and self.peek() != '\n':
            self.advance()
        
        # Consumir >
        if self.peek() == '>':
            etiqueta_completa += self.advance()
        else:
            self.registrar_error("Se esperaba '>' para cerrar etiqueta", self.fila, self.columna, self.peek() or "EOF")
        
        return Token("ETIQUETA_ABIERTA", etiqueta_completa, inicio_fila, inicio_columna)
    
    def extraer_etiqueta_cerrada(self) -> Token:
        inicio_fila = self.fila
        inicio_columna = self.columna
        etiqueta = ""
        
        # Consumir <
        etiqueta += self.advance()
        
        # Consumir /
        if self.peek() != '/':
            self.registrar_error("Se esperaba '/' en etiqueta de cierre", self.fila, self.columna, self.peek() or "")
            return Token("ETIQUETA_CERRADA", etiqueta, inicio_fila, inicio_columna)
        etiqueta += self.advance()
        
        # Extraer nombre de etiqueta
        palabra = ""
        while self.es_letra(self.peek()) or self.peek() == '_':
            palabra += self.advance()
        
        if palabra not in self.ETIQUETAS:
            self.registrar_error(f"Etiqueta de cierre no valida: {palabra}", inicio_fila, inicio_columna, f"</{palabra}")
        
        etiqueta += palabra
        
        # Consumir >
        if self.peek() == '>':
            etiqueta += self.advance()
        else:
            self.registrar_error("Se esperaba '>'", self.fila, self.columna, "")
        
        return Token("ETIQUETA_CERRADA", etiqueta, inicio_fila, inicio_columna)
    
    def scanear(self) -> List[Token]:
        while self.posicion < len(self.texto):
            char = self.peek()
            
            if self.es_espacio(char):
                self.advance()
                continue
            
            # Números
            if self.es_digito(char):
                self.tokens.append(self.extraer_numero())
            
            # Etiquetas y símbolos especiales
            elif char == '<':
                # Verificar si es etiqueta de cierre </...>
                if self.peek(1) == '/':
                    self.tokens.append(self.extraer_etiqueta_cerrada())
                else:
                    # Es etiqueta de apertura <...>
                    self.tokens.append(self.extraer_etiqueta_abierta())
            
            # Otros símbolos solos (que no sean parte de etiquetas)
            elif char == '=' and not self._en_etiqueta():
                self.tokens.append(Token("IGUAL", self.advance(), self.fila, self.columna - 1))
            
            elif char == '>' and not self._en_etiqueta():
                self.tokens.append(Token("MAYOR", self.advance(), self.fila, self.columna - 1))
            
            # Palabras (reservadas o identificadores)
            elif self.es_letra(char) or char == '_':
                self.tokens.append(self.extraer_palabra_o_etiqueta())
            
            # Caracteres inválidos
            else:
                char_invalido = self.advance()
                self.registrar_error(f"Caracter no reconocido", self.fila, self.columna - 1, char_invalido)
                self.tokens.append(Token("ERROR", char_invalido, self.fila, self.columna - 1))
        
        self.tokens.append(Token("EOF", "", self.fila, self.columna))
        return self.tokens
    
    def _en_etiqueta(self) -> bool:
        """Verifica si estamos dentro de una etiqueta (para no confundir = y >)"""
        # Esta es una verificación simple - normalmente esto se maneja mejor
        return False

@dataclass
class NodoOperacion:
    tipo: str
    operandos: List[Union['NodoOperacion', float]]

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.posicion = 0
        self.errores: List[str] = []
    
    def peek(self, offset: int = 0) -> Optional[Token]:
        pos = self.posicion + offset
        return self.tokens[pos] if pos < len(self.tokens) else None
    
    def advance(self) -> Optional[Token]:
        token = self.peek()
        self.posicion += 1
        return token
    
    def esperar(self, tipo: str) -> bool:
        return self.peek() and self.peek().tipo == tipo
    
    def consumir(self, tipo: str) -> Token:
        if not self.esperar(tipo):
            raise Exception(f"Se esperaba {tipo}, se encontro {self.peek().tipo if self.peek() else 'EOF'}")
        return self.advance()
    
    def extraer_tipo_operacion(self, lexema: str) -> str:
        """Extrae el tipo de operacion del lexema de etiqueta abierta"""
        # Ejemplos: 
        # <Operacion= SUMA> -> SUMA
        # <Operacion=SUMA> -> SUMA
        # <Numero> -> vacío
        
        # Si no tiene =, no es operación con tipo
        if '=' not in lexema:
            return ""
        
        try:
            # Dividir por = y tomar la parte después
            partes = lexema.split('=', 1)  # Usar maxsplit=1 por seguridad
            if len(partes) != 2:
                return ""
            
            # Tomar la parte después del = y antes del >
            tipo = partes[1].replace('>', '').strip()
            
            # Validar que no esté vacío
            if not tipo:
                return ""
            
            return tipo
        except Exception as e:
            print(f"Error extrayendo tipo de operacion: {e}")
            return ""
    
    def parsear(self) -> List[Union[NodoOperacion, float]]:
        """Parsea multiples operaciones"""
        operaciones = []
        
        while self.posicion < len(self.tokens):
            token = self.peek()
            
            if token is None or token.tipo == "EOF":
                break
            
            # Parsear operación o número
            if token.tipo == "ETIQUETA_ABIERTA":
                if "Operacion" in token.lexema:
                    operaciones.append(self.parsear_operacion())
                elif "Numero" in token.lexema:
                    operaciones.append(self.parsear_numero())
                else:
                    self.advance()
            else:
                self.advance()
        
        # Si hay solo una operación, retornarla directamente
        # Si hay múltiples, retornar lista
        if len(operaciones) == 1:
            return operaciones[0]
        elif len(operaciones) > 1:
            return operaciones
        else:
            raise Exception("No se encontraron operaciones para analizar")
    
    def parsear_operacion(self) -> NodoOperacion:
        etiqueta_abierta = self.consumir("ETIQUETA_ABIERTA")
        tipo_op = self.extraer_tipo_operacion(etiqueta_abierta.lexema)
        
        # Validar que se extrajo el tipo de operación
        if not tipo_op or tipo_op == "":
            raise Exception(f"No se pudo extraer tipo de operacion de: '{etiqueta_abierta.lexema}'")
        
        # Validar que sea una operación válida
        operaciones_validas = {'SUMA', 'RESTA', 'MULTIPLICACION', 'DIVISION', 'POTENCIA', 'RAIZ', 'INVERSO', 'MOD'}
        if tipo_op not in operaciones_validas:
            raise Exception(f"Tipo de operacion no valido: '{tipo_op}'")
        
        operandos: List[Union[NodoOperacion, float]] = []
        parametros: dict = {}
        
        # Parsear operandos y parámetros hasta encontrar </Operacion>
        while self.posicion < len(self.tokens):
            token = self.peek()
            
            if token is None:
                raise Exception("Token EOF inesperado")
            
            # Fin de la operación
            if token.tipo == "ETIQUETA_CERRADA" and "Operacion" in token.lexema:
                self.consumir("ETIQUETA_CERRADA")
                break
            
            # Números directos
            elif token.tipo == "ETIQUETA_ABIERTA" and "<Numero>" in token.lexema:
                operandos.append(self.parsear_numero())
            
            # Operaciones anidadas
            elif token.tipo == "ETIQUETA_ABIERTA" and "<Operacion=" in token.lexema:
                operandos.append(self.parsear_operacion())
            
            # Parámetro P (exponente)
            elif token.tipo == "ETIQUETA_ABIERTA" and "<P>" in token.lexema:
                parametros['P'] = self.parsear_parametro_p()
            
            # Parámetro R (índice raíz)
            elif token.tipo == "ETIQUETA_ABIERTA" and "<R>" in token.lexema:
                parametros['R'] = self.parsear_parametro_r()
            
            else:
                self.advance()
        
        # Validar que haya al menos un operando
        if not operandos and not parametros:
            raise Exception(f"Operacion {tipo_op} sin operandos")
        
        # Agregar parámetros al inicio de operandos
        if 'P' in parametros:
            operandos.insert(0, parametros['P'])
        if 'R' in parametros:
            operandos.insert(0, parametros['R'])
        
        return NodoOperacion(tipo_op, operandos)
    
    def parsear_numero(self) -> float:
        self.consumir("ETIQUETA_ABIERTA")
        valor = 0.0
        if self.esperar("NUMERO"):
            valor = float(self.advance().lexema)
        self.consumir("ETIQUETA_CERRADA")
        return valor
    
    def parsear_numero_simple(self) -> float:
        return float(self.advance().lexema)
    
    def parsear_parametro_p(self) -> float:
        self.consumir("ETIQUETA_ABIERTA")
        valor = 0.0
        if self.esperar("NUMERO"):
            valor = float(self.advance().lexema)
        self.consumir("ETIQUETA_CERRADA")
        return valor
    
    def parsear_parametro_r(self) -> float:
        self.consumir("ETIQUETA_ABIERTA")
        valor = 0.0
        if self.esperar("NUMERO"):
            valor = float(self.advance().lexema)
        self.consumir("ETIQUETA_CERRADA")
        return valor

class Evaluador:
    def __init__(self):
        self.historial = []
    
    def evaluar(self, nodo: Union[NodoOperacion, float, List]) -> Union[float, List[float]]:
        """Evalúa recursivamente el arbol o lista de arboles"""
        
        # Si es una lista, evaluar cada elemento
        if isinstance(nodo, list):
            resultados = []
            for op in nodo:
                resultados.append(self.evaluar(op))
            return resultados
        
        # Si es número
        if isinstance(nodo, (int, float)):
            return float(nodo)
        
        # Si es operación
        if isinstance(nodo, NodoOperacion):
            if nodo.tipo == 'SUMA':
                return self.suma(nodo.operandos)
            elif nodo.tipo == 'RESTA':
                return self.resta(nodo.operandos)
            elif nodo.tipo == 'MULTIPLICACION':
                return self.multiplicacion(nodo.operandos)
            elif nodo.tipo == 'DIVISION':
                return self.division(nodo.operandos)
            elif nodo.tipo == 'POTENCIA':
                return self.potencia(nodo.operandos)
            elif nodo.tipo == 'RAIZ':
                return self.raiz(nodo.operandos)
            elif nodo.tipo == 'INVERSO':
                return self.inverso(nodo.operandos)
            elif nodo.tipo == 'MOD':
                return self.modulo(nodo.operandos)
        
        raise Exception(f"Tipo de nodo desconocido: {type(nodo)}")
    
    def suma(self, operandos: List) -> float:
        resultado = 0
        for op in operandos:
            resultado += self.evaluar(op)
        return resultado
    
    def resta(self, operandos: List) -> float:
        if not operandos:
            return 0
        resultado = self.evaluar(operandos[0])
        for op in operandos[1:]:
            resultado -= self.evaluar(op)
        return resultado
    
    def multiplicacion(self, operandos: List) -> float:
        resultado = 1
        for op in operandos:
            resultado *= self.evaluar(op)
        return resultado
    
    def division(self, operandos: List) -> float:
        if not operandos:
            return 0
        resultado = self.evaluar(operandos[0])
        for op in operandos[1:]:
            divisor = self.evaluar(op)
            if divisor == 0:
                raise Exception("División por cero")
            resultado /= divisor
        return resultado
    
    def potencia(self, operandos: List) -> float:
        if len(operandos) < 2:
            raise Exception("POTENCIA requiere 2 operandos")
        exponente = self.evaluar(operandos[0])
        base = self.evaluar(operandos[1])
        return base ** exponente
    
    def raiz(self, operandos: List) -> float:
        if len(operandos) < 2:
            raise Exception("RAIZ requiere 2 operandos")
        indice = self.evaluar(operandos[0])
        radicando = self.evaluar(operandos[1])
        
        if indice == 0:
            raise Exception("Índice de raiz no puede ser cero")
        
        if radicando < 0 and int(indice) % 2 == 0:
            raise Exception(f"Raíz {int(indice)} de numero negativo")
        
        return radicando ** (1 / indice)
    
    def inverso(self, operandos: List) -> float:
        if not operandos:
            raise Exception("INVERSO requiere 1 operando")
        valor = self.evaluar(operandos[0])
        if valor == 0:
            raise Exception("Inverso de cero")
        return 1 / valor
    
    def modulo(self, operandos: List) -> float:
        if len(operandos) < 2:
            raise Exception("MOD requiere 2 operandos")
        resultado = int(self.evaluar(operandos[0]))
        for op in operandos[1:]:
            divisor = int(self.evaluar(op))
            if divisor == 0:
                raise Exception("MOD: divisor cero")
            resultado = resultado % divisor
        return float(resultado)
    
    def generar_expresion(self, nodo: Union[NodoOperacion, float, List]) -> str:
        """Genera representación en notación matematica"""
        
        # Si es una lista, generar expresión para cada operación
        if isinstance(nodo, list):
            expresiones = []
            for i, op in enumerate(nodo, 1):
                expr = self.generar_expresion(op)
                expresiones.append(f"{i}. {expr}")
            return "\n".join(expresiones)
        
        if isinstance(nodo, (int, float)):
            return str(nodo)
        
        if isinstance(nodo, NodoOperacion):
            operandos_str = []
            
            # Procesar cada operando recursivamente
            for op in nodo.operandos:
                operandos_str.append(self.generar_expresion(op))
            
            if nodo.tipo == 'SUMA':
                return "(" + "+".join(operandos_str) + ")"
            elif nodo.tipo == 'RESTA':
                return "(" + "-".join(operandos_str) + ")"
            elif nodo.tipo == 'MULTIPLICACION':
                return "(" + "*".join(operandos_str) + ")"
            elif nodo.tipo == 'DIVISION':
                return "(" + "/".join(operandos_str) + ")"
            elif nodo.tipo == 'POTENCIA':
                if len(operandos_str) >= 2:
                    return f"({operandos_str[1]}^{operandos_str[0]})"
                return "(potencia_error)"
            elif nodo.tipo == 'RAIZ':
                if len(operandos_str) >= 2:
                    return f"(√[{operandos_str[0]}]{operandos_str[1]})"
                return "(raiz_error)"
            elif nodo.tipo == 'INVERSO':
                if operandos_str:
                    return f"(1/{operandos_str[0]})"
                return "(inverso_error)"
            elif nodo.tipo == 'MOD':
                return "(" + "%".join(operandos_str) + ")"
        
        return str(nodo)

# ============================================================================
# INTERFAZ GRÁFICA CON TKINTER
# ============================================================================

class AnalizadorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Analizador de Operaciones Aritmeticas - LFA 2025")
        self.root.geometry("1200x800")
        self.root.config(bg="#f0f0f0")
        
        self.archivo_actual = None
        self.arbol_actual = None
        self.evaluador_actual = None
        self.tokens_actual = []
        self.scanner_actual = None
        self.crear_widgets()
    
    def crear_widgets(self):
        # Barra de menú
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
        
        # Frame superior con botones
        frame_botones = tk.Frame(self.root, bg="#f0f0f0")
        frame_botones.pack(pady=10)
        
        tk.Button(frame_botones, text="Abrir", command=self.abrir_archivo, width=12, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones, text="Guardar", command=self.guardar_archivo, width=12, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones, text="Guardar Como", command=self.guardar_como, width=12, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones, text="Analizar", command=self.analizar, width=12, bg="#FF9800", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones, text="Exportar HTML", command=self.exportar_html, width=12, bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=5)
        
        # Frame principal con dos columnas
        frame_principal = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        frame_principal.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Panel izquierdo - Entrada
        frame_entrada = ttk.Frame(frame_principal)
        frame_principal.add(frame_entrada, weight=1)
        
        tk.Label(frame_entrada, text="Código Fuente:", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(anchor=tk.W)
        
        self.entrada_text = scrolledtext.ScrolledText(frame_entrada, height=25, width=45, font=("Courier", 10))
        self.entrada_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Panel derecho - Resultados
        frame_resultados = ttk.Frame(frame_principal)
        frame_principal.add(frame_resultados, weight=1)
        
        tk.Label(frame_resultados, text="Resultados:", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(anchor=tk.W)
        
        # Notebook para tabs
        self.notebook = ttk.Notebook(frame_resultados)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tab 1: Tokens
        self.tab_tokens = scrolledtext.ScrolledText(self.notebook, height=15, width=45, font=("Courier", 9))
        self.notebook.add(self.tab_tokens, text="Tokens")
        
        # Tab 2: Árbol
        frame_arbol_container = ttk.Frame(self.notebook)
        self.notebook.add(frame_arbol_container, text="Árbol")
        
        # Frame para botones de navegación
        frame_botones_arbol = ttk.Frame(frame_arbol_container)
        frame_botones_arbol.pack(pady=10)
        
        self.label_arbol_info = tk.Label(frame_arbol_container, text="", font=("Arial", 10, "bold"), bg="white")
        self.label_arbol_info.pack()
        
        tk.Button(frame_botones_arbol, text="← Anterior", command=self.anterior_arbol, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_botones_arbol, text="Siguiente →", command=self.siguiente_arbol, width=15).pack(side=tk.LEFT, padx=5)
        
        self.canvas_arbol = tk.Canvas(frame_arbol_container, bg="white", highlightthickness=0)
        self.canvas_arbol.pack(fill=tk.BOTH, expand=True)
        
        self.arbol_index_actual = 0  # Índice del árbol actual siendo mostrado
        
        # Tab 3: Expresión
        self.tab_expresion = scrolledtext.ScrolledText(self.notebook, height=15, width=45, font=("Courier", 9))
        self.notebook.add(self.tab_expresion, text="Expresion")
        
        # Tab 4: Resultado
        self.tab_resultado = scrolledtext.ScrolledText(self.notebook, height=15, width=45, font=("Courier", 9))
        self.notebook.add(self.tab_resultado, text="Resultado")
        
        # Tab 5: Errores Detallados
        frame_errores = ttk.Frame(self.notebook)
        self.notebook.add(frame_errores, text="Errores")
        
        self.tabla_errores = ttk.Treeview(frame_errores, columns=('#', 'Lexema', 'Tipo', 'Fila', 'Columna', 'Mensaje'), height=15)
        self.tabla_errores.column('#0', width=0, stretch=tk.NO)
        self.tabla_errores.column('#', width=30, anchor=tk.CENTER)
        self.tabla_errores.column('Lexema', width=80, anchor=tk.W)
        self.tabla_errores.column('Tipo', width=80, anchor=tk.W)
        self.tabla_errores.column('Fila', width=50, anchor=tk.CENTER)
        self.tabla_errores.column('Columna', width=70, anchor=tk.CENTER)
        self.tabla_errores.column('Mensaje', width=150, anchor=tk.W)
        
        self.tabla_errores.heading('#', text="#")
        self.tabla_errores.heading('Lexema', text="Lexema")
        self.tabla_errores.heading('Tipo', text="Tipo")
        self.tabla_errores.heading('Fila', text="Fila")
        self.tabla_errores.heading('Columna', text="Columna")
        self.tabla_errores.heading('Mensaje', text="Mensaje")
        
        scrollbar = ttk.Scrollbar(frame_errores, orient=tk.VERTICAL, command=self.tabla_errores.yview)
        self.tabla_errores.configure(yscroll=scrollbar.set)
        
        self.tabla_errores.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def abrir_archivo(self):
        archivo = filedialog.askopenfilename(filetypes=[("Texto", "*.txt"), ("XML", "*.xml"), ("Todos", "*.*")])
        if archivo:
            with open(archivo, 'r') as f:
                contenido = f.read()
            self.entrada_text.delete(1.0, tk.END)
            self.entrada_text.insert(1.0, contenido)
            self.archivo_actual = archivo
            self.root.title(f"Analizador - {os.path.basename(archivo)}")
    
    def guardar_archivo(self):
        if not self.archivo_actual:
            self.guardar_como()
            return
        
        contenido = self.entrada_text.get(1.0, tk.END)
        with open(self.archivo_actual, 'w') as f:
            f.write(contenido)
        messagebox.showinfo("Éxito", "Archivo guardado correctamente")
    
    def guardar_como(self):
        archivo = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texto", "*.txt"), ("XML", "*.xml"), ("Todos", "*.*")])
        if archivo:
            contenido = self.entrada_text.get(1.0, tk.END)
            with open(archivo, 'w') as f:
                f.write(contenido)
            self.archivo_actual = archivo
            self.root.title(f"Analizador - {os.path.basename(archivo)}")
            messagebox.showinfo("Éxito", "Archivo guardado correctamente")
    
    def analizar(self):
        texto = self.entrada_text.get(1.0, tk.END)
        
        try:
            # Reiniciar índice de árbol
            self.arbol_index_actual = 0
            
            # Análisis léxico
            self.scanner_actual = ScannerLexico(texto)
            self.tokens_actual = self.scanner_actual.scanear()
            
            # Debug: mostrar primeros tokens
            print("=== TOKENS GENERADOS ===")
            for i, token in enumerate(self.tokens_actual[:20]):
                if token.tipo != "EOF":
                    print(f"{i}: {token.tipo} = '{token.lexema}'")
            
            # Mostrar tokens
            self.tab_tokens.delete(1.0, tk.END)
            for token in self.tokens_actual:
                if token.tipo != "EOF":
                    self.tab_tokens.insert(tk.END, f"{token.tipo:20} | {token.lexema:20} | Fila:{token.fila} Col:{token.columna}\n")
            
            # Parsing
            parser = Parser(self.tokens_actual)
            self.arbol_actual = parser.parsear()
            
            print(f"Arbol generado: {self.arbol_actual}")
            
            # Evaluación
            self.evaluador_actual = Evaluador()
            resultado = self.evaluador_actual.evaluar(self.arbol_actual)
            expresion = self.evaluador_actual.generar_expresion(self.arbol_actual)
            
            # Validar expresión
            if not expresion or expresion == "":
                raise Exception("No se pudo generar la expresion matematica")
            
            # Mostrar expresión
            self.tab_expresion.delete(1.0, tk.END)
            self.tab_expresion.insert(1.0, f"Expresiones:\n{expresion}")
            
            # Mostrar resultado(s)
            self.tab_resultado.delete(1.0, tk.END)
            if isinstance(resultado, list):
                resultado_texto = "Resultados:\n"
                for i, res in enumerate(resultado, 1):
                    resultado_texto += f"{i}. {res:.10f}\n"
                self.tab_resultado.insert(1.0, resultado_texto)
                resultado_mostrar = f"Operaciones analizadas: {len(resultado)}"
            else:
                self.tab_resultado.insert(1.0, f"Resultado:\n{resultado:.10f}")
                resultado_mostrar = f"Resultado: {resultado:.10f}"
            
            # Mostrar árbol visual
            self.mostrar_arbol_visual()
            
            # Mostrar errores léxicos
            self.tabla_errores.delete(*self.tabla_errores.get_children())
            if self.scanner_actual and self.scanner_actual.errores:
                for error in self.scanner_actual.errores:
                    self.tabla_errores.insert('', tk.END, values=(
                        error['numero'],
                        error['lexema'],
                        error['tipo'],
                        error['fila'],
                        error['columna'],
                        error['mensaje']
                    ))
            else:
                self.tabla_errores.insert('', tk.END, values=(
                    "-", "-", "✓", "-", "-", "No hay errores lexicos"
                ))
            
            messagebox.showinfo("Éxito", f"Analisis completado exitosamente\n\n{resultado_mostrar}")
            
        except Exception as e:
            print(f"EXCEPCION: {e}")
            import traceback
            traceback.print_exc()
            
            self.tabla_errores.delete(*self.tabla_errores.get_children())
            self.tabla_errores.insert('', tk.END, values=(
                "1", "", "Error de Parsing", "-", "-", str(e)
            ))
            self.tab_expresion.delete(1.0, tk.END)
            self.tab_resultado.delete(1.0, tk.END)
            self.canvas_arbol.delete("all")
            messagebox.showerror("Error", f"Error durante el analisis:\n{str(e)}")
    
    def generar_arbol_canvas(self, nodo: Union[NodoOperacion, float], x: float = 250, y: float = 30, 
                            offset: float = 100, canvas = None) -> float:
        """Dibuja el árbol directamente en Canvas (solo librerias nativas)"""
        if canvas is None:
            return x
        
        if isinstance(nodo, (int, float)):
            # Dibujar número (cuadrado blanco con borde)
            canvas.create_rectangle(x-35, y-20, x+35, y+20, fill="white", outline="black", width=2)
            canvas.create_text(x, y, text=f"{nodo:.2f}" if isinstance(nodo, float) else str(nodo), 
                             font=("Arial", 9))
            return x
        
        if isinstance(nodo, NodoOperacion):
            # Calcular posición de hijos
            num_hijos = len(nodo.operandos) if nodo.operandos else 0
            
            if num_hijos == 0:
                # Operación sin operandos
                canvas.create_rectangle(x-50, y-25, x+50, y+25, fill="white", outline="black", width=2)
                canvas.create_text(x, y, text=nodo.tipo, font=("Arial", 9, "bold"), width=90)
            else:
                # Calcular espaciamiento
                total_width = num_hijos * offset
                inicio_x = x - total_width // 2
                
                # Dibujar líneas a hijos
                posiciones_hijos = []
                for i, operando in enumerate(nodo.operandos):
                    hijo_x = inicio_x + i * offset + offset // 2
                    canvas.create_line(x, y + 30, hijo_x, y + 70, fill="black", width=1)
                    posiciones_hijos.append(hijo_x)
                
                # Dibujar operación (cuadrado blanco con borde)
                canvas.create_rectangle(x-50, y-25, x+50, y+25, fill="white", outline="black", width=2)
                canvas.create_text(x, y, text=nodo.tipo, font=("Arial", 9, "bold"), width=90)
                
                # Dibujar hijos recursivamente
                for i, operando in enumerate(nodo.operandos):
                    nuevo_offset = max(50, offset // 1.5)
                    self.generar_arbol_canvas(operando, posiciones_hijos[i], y + 100, nuevo_offset, canvas)
            
            return x
        
        return x
    
    def anterior_arbol(self):
        """Muestra el arbol anterior"""
        if isinstance(self.arbol_actual, list):
            if self.arbol_index_actual > 0:
                self.arbol_index_actual -= 1
                self.mostrar_arbol_visual()
    
    def siguiente_arbol(self):
        """Muestra el siguiente árbol"""
        if isinstance(self.arbol_actual, list):
            if self.arbol_index_actual < len(self.arbol_actual) - 1:
                self.arbol_index_actual += 1
                self.mostrar_arbol_visual()
    
    def calcular_altura_arbol(self, nodo: Union[NodoOperacion, float]) -> int:
        """Calcula la altura del árbol para ajustar el canvas"""
        if isinstance(nodo, (int, float)):
            return 1
        
        if isinstance(nodo, NodoOperacion):
            if not nodo.operandos:
                return 1
            max_altura = max(self.calcular_altura_arbol(op) for op in nodo.operandos)
            return max_altura + 1
        
        return 1
        """Calcula la altura del árbol para ajustar el canvas"""
        if isinstance(nodo, (int, float)):
            return 1
        
        if isinstance(nodo, NodoOperacion):
            if not nodo.operandos:
                return 1
            max_altura = max(self.calcular_altura_arbol(op) for op in nodo.operandos)
            return max_altura + 1
        
        return 1
    
    def mostrar_arbol_visual(self):
        """Dibuja el arbol directamente en Canvas sin librerias externas (Se intento con Pil no salio bien no le enti)"""
        try:
            self.canvas_arbol.delete("all")
            
            # Si es una lista de operaciones, mostrar según índice
            arbol_a_mostrar = self.arbol_actual
            titulo = ""
            
            if isinstance(self.arbol_actual, list):
                if len(self.arbol_actual) > 0:
                    # Asegurar que el índice esté dentro de rango
                    if self.arbol_index_actual >= len(self.arbol_actual):
                        self.arbol_index_actual = len(self.arbol_actual) - 1
                    if self.arbol_index_actual < 0:
                        self.arbol_index_actual = 0
                    
                    arbol_a_mostrar = self.arbol_actual[self.arbol_index_actual]
                    numero_actual = self.arbol_index_actual + 1
                    total_operaciones = len(self.arbol_actual)
                    
                    titulo = f"Mostrando operacion {numero_actual} de {total_operaciones}"
                    
                    # Actualizar label de información
                    self.label_arbol_info.config(text=titulo)
            else:
                self.label_arbol_info.config(text="Árbol de operacion unica")
            
            # Calcular altura del árbol para ajustar canvas
            altura_arbol = self.calcular_altura_arbol(arbol_a_mostrar) * 100 + 50
            
            # Crear scrollregion apropiada
            self.canvas_arbol.config(scrollregion=(0, 0, 500, max(altura_arbol, 400)))
            
            # Dibujar árbol
            self.generar_arbol_canvas(arbol_a_mostrar, y=50, canvas=self.canvas_arbol)
            
        except Exception as e:
            self.canvas_arbol.delete("all")
            self.canvas_arbol.create_text(250, 200, text=f"Error al generar arbol:\n{str(e)}", 
                                         fill="red", font=("Arial", 10))
    
    def exportar_html(self):
        """Exporta los resultados completos a HTML"""
        if not self.arbol_actual or not self.evaluador_actual:
            messagebox.showwarning("Advertencia", "Primero debes analizar el codigo")
            return
        
        archivo = filedialog.asksaveasfilename(defaultextension=".html", filetypes=[("HTML", "*.html"), ("Todos", "*.*")])
        if not archivo:
            return
        
        try:
            # Recolectar datos
            tokens_html = ""
            for token in self.tokens_actual:
                if token.tipo != "EOF":
                    tokens_html += f"<tr><td>{token.tipo}</td><td>{token.lexema}</td><td>{token.fila}</td><td>{token.columna}</td></tr>\n"
            
            expresion = self.evaluador_actual.generar_expresion(self.arbol_actual)
            resultado = self.evaluador_actual.evaluar(self.arbol_actual)
            
            errores_html = ""
            if self.scanner_actual and self.scanner_actual.errores:
                for error in self.scanner_actual.errores:
                    errores_html += f"<tr><td>{error['numero']}</td><td>{error['lexema']}</td><td>{error['tipo']}</td><td>{error['fila']}</td><td>{error['columna']}</td><td>{error['mensaje']}</td></tr>\n"
            else:
                errores_html = "<tr><td colspan='6' style='text-align:center; color:green;'>✓ No hay errores léxicos</td></tr>\n"
            
            total_tokens = len([t for t in self.tokens_actual if t.tipo != 'EOF'])
            total_errores = len(self.scanner_actual.errores) if self.scanner_actual else 0
            
            # Generar HTML
            html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Análisis - Operaciones Aritméticas</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 15px;
            font-size: 1.8em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        table th {{
            background-color: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        table tr:hover {{
            background-color: #f5f5f5;
        }}
        table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .expresion {{
            background: #f0f0f0;
            padding: 15px;
            border-left: 4px solid #667eea;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 1.1em;
            margin: 10px 0;
        }}
        .valor {{
            background: #e8f5e9;
            padding: 15px;
            border-left: 4px solid #4CAF50;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 1.1em;
            margin: 10px 0;
            color: #2e7d32;
        }}
        .footer {{
            background: #f5f5f5;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #ddd;
        }}
        code {{
            background: #f0f0f0;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> Reporte de Análisis</h1>
            <p>Analizador de Operaciones Aritméticas - Fase 2</p>
        </div>
        
        <div class="content">
            <!-- SECCIÓN DE RESULTADO -->
            <div class="section">
                <h2>Resultado Final</h2>
                <div class="expresion">
                    <strong>Expresión:</strong><br>{expresion}
                </div>
                <div class="valor">
                    <strong>Valor:</strong><br>{resultado:.10f}
                </div>
            </div>
            
            <!-- SECCIÓN DE TOKENS -->
            <div class="section">
                <h2> Tokens Reconocidos</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Tipo</th>
                            <th>Lexema</th>
                            <th>Fila</th>
                            <th>Columna</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tokens_html}
                    </tbody>
                </table>
            </div>
            
            <!-- SECCIÓN DE ERRORES -->
            <div class="section">
                <h2>Errores Léxicos</h2>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Lexema</th>
                            <th>Tipo</th>
                            <th>Fila</th>
                            <th>Columna</th>
                            <th>Mensaje</th>
                        </tr>
                    </thead>
                    <tbody>
                        {errores_html}
                    </tbody>
                </table>
            </div>
            
            <!-- SECCIÓN DE INFORMACIÓN -->
            <div class="section">
                <h2>ℹ Información del Análisis</h2>
                <table>
                    <tr>
                        <td><strong>Total de Tokens:</strong></td>
                        <td>{total_tokens}</td>
                    </tr>
                    <tr>
                        <td><strong>Total de Errores:</strong></td>
                        <td>{total_errores}</td>
                    </tr>
                    <tr>
                        <td><strong>Estado:</strong></td>
                        <td><span style="color: green; font-weight: bold;">✓ Análisis completado exitosamente</span></td>
                    </tr>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p>Generado por: Analizador de Operaciones Aritméticas v1.0</p>
            <p>Proyecto LFA 2025 - Fase 2</p>
        </div>
    </div>
</body>
</html>
"""
            
            with open(archivo, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            messagebox.showinfo("Éxito", f"Reporte exportado a:\n{archivo}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar HTML:\n{str(e)}")
    
    def acerca_de(self):
        messagebox.showinfo("Acerca de", 
            "Analizador de Operaciones Aritméticas\n\n"
            "Versión: 1.0\n"
            "Fase 2 - Proyecto LFA 2025\n\n"
            "Funcionalidades:\n"
            " Análisis Léxico\n"
            " Análisis Sintáctico\n"
            " Evaluación de Operaciones\n"
            " Visualización de Árbol\n"
            " Exportación a HTML\n"
            " Reporte de Errores")

if __name__ == "__main__":
    root = tk.Tk()
    app = AnalizadorGUI(root)
    root.mainloop()