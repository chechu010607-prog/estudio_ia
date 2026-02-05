import os
import PyPDF2
import genanki
import json
import random
import time
import html
from typing import List 
from google.genai import types
from config import obtener_cliente
from RAG import guardar_memoria, buscar_memoria, listar_archivos_guardados


def leer_contenido_pdf(ruta_archivo: str) -> str:
    """
    Lee el texto de un PDF dado su ruta.
    Esta función es auxiliar y suele ser llamada por otras herramientas.
    """
    texto_completo = ""
    try:
        with open(ruta_archivo, 'rb') as archivo:
            lector = PyPDF2.PdfReader(archivo)
            for pagina in lector.pages:
                texto = pagina.extract_text()
                if texto: texto_completo += texto + "\n"
    except Exception as e:
        print(f"Error PDF: {e}")
        return ""
    return texto_completo

# --- 2. HERRAMIENTA PARA MEMORIZAR (RAG) ---
def aprender_pdf(ruta_pdf: str) -> str:
    """
    Usa esta herramienta cuando el usuario te pida explícitamente que 'aprendas',
    'memorices', 'estudies' o 'guardes en tu cerebro' un archivo PDF específico.
    
    Args:
        ruta_pdf (str): La ruta del archivo que debes memorizar.
    """
    print(f"📖 Leyendo {ruta_pdf}...")
    texto = leer_contenido_pdf(ruta_pdf)
    nombre_archivo = os.path.basename(ruta_pdf)
    resultado = guardar_memoria(texto, nombre_archivo)
    return resultado
# --- EN tools.py ---

def aprender_varios_pdfs(rutas_pdfs: List[str]) -> str:
    """
    Usa esta herramienta cuando el usuario te pida memorizar, aprender o estudiar
    VARIOS archivos PDF a la vez.
    
    Args:
        rutas_pdfs (List[str]): Lista de las rutas de los archivos.
    """
    total = len(rutas_pdfs)
    aprendidos = 0
    
    for i, ruta in enumerate(rutas_pdfs):
        print(f"🧠 Memorizando archivo {i+1} de {total}: {ruta}")
        
        # Reutilizamos la función individual que ya tienes
        resultado = aprender_pdf(ruta)
        
        if "Error" not in resultado:
            aprendidos += 1
            
        # Opcional: Pequeña pausa para no saturar la base de datos si son muchísimos
        # time.sleep(2) 
    
    return f"Proceso finalizado. He memorizado {aprendidos} de {total} documentos correctamente."

# --- 3. HERRAMIENTA PARA RESPONDER PREGUNTAS (RAG) ---
def consultar_cerebro(pregunta: str) -> str:
    """
    Usa esta herramienta SIEMPRE que el usuario te haga una pregunta sobre 
    un tema, apuntes o documentos que hayas estudiado previamente.
    Busca la respuesta en tu base de datos de conocimiento.
    
    Args:
        pregunta (str): La duda o cuestión del usuario.
    """
    return buscar_memoria(pregunta)

# --- 4. HERRAMIENTA DE INVENTARIO ---
def lista_archivos() -> str:
    """
    Usa esta herramienta cuando el usuario pregunte qué archivos, documentos 
    o apuntes tienes guardados actualmente en tu memoria.
    
    Returns:
        str: Una lista de nombres de archivos separados por comas.
    """
    return listar_archivos_guardados()

# --- 5. HERRAMIENTA DE ANKI (Flashcards) ---
def generar_mazo_anki(rutas_pdfs: List[str], cantidad: int) -> str:
    """
    Usa esta herramienta cuando el usuario quiera crear tarjetas de estudio,
    flashcards, mazos de repaso o preparar un examen usando Anki.
    
    Args:
        rutas_pdfs (List[str]): Lista de rutas de los archivos a procesar.
        cantidad (int): Número de tarjetas a generar por cada archivo.
    """
    client = obtener_cliente()
    mazo_id = random.randrange(1 << 30, 1 << 31)
    mazo = genanki.Deck(mazo_id, "Repaso Examen (IA)")
    
    modelo = genanki.Model(
        1607392319, 'Modelo IA Simple',
        fields=[{'name': 'Pregunta'}, {'name': 'Respuesta'}],
        templates=[{'name': 'Tarjeta', 'qfmt': '{{Pregunta}}', 'afmt': '{{FrontSide}}<hr id="answer">{{Respuesta}}<br><small>IA</small>'}]
    )

    total_archivos = len(rutas_pdfs)
    
    for i, ruta in enumerate(rutas_pdfs):
        print(f"🔄 Procesando archivo {i+1} de {total_archivos}: {ruta}")
        
        texto = leer_contenido_pdf(ruta)
        if not texto or len(texto) < 50: continue
        
        # Prompt mejorado para examen
        prompt = f"""
        Actúa como profesor. Analiza el texto y genera {cantidad} tarjetas Anki.
        Prioriza conceptos clave para examen.
        Responde SOLO JSON válido: [{{'pregunta': '...', 'respuesta': '...'}}]
        """
        contenido = prompt + "\nTEXTO:\n" + texto[:30000]

        try:
           
            response = client.models.generate_content(
                model='models/gemini-3-flash-preview', 
                contents=[types.Content(role="user", parts=[types.Part(text=contenido)])],
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            limpio = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(limpio)
            
            tarjetas_creadas = 0
            if isinstance(data, list):
                for t in data:
                    if 'pregunta' in t and 'respuesta' in t:
                        # Limpieza HTML para evitar avisos en Anki
                        p = html.escape(t['pregunta'])
                        r = html.escape(t['respuesta'])
                        mazo.add_note(genanki.Note(model=modelo, fields=[p, r]))
                        tarjetas_creadas += 1
            
            print(f"✅ Éxito: {tarjetas_creadas} tarjetas creadas.")

        except Exception as e:
            print(f"❌ Error en {ruta}: {e}")
        
        if i < total_archivos - 1:
            print("⏳ Enfriando motores (esperando 30s)...")
            time.sleep(30)

    nombre_salida = "mazo_completo.apkg"
    genanki.Package(mazo).write_to_file(nombre_salida)
    return nombre_salida