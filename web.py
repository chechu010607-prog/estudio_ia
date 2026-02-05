import streamlit as st
import tempfile
import os
from google.genai import types

# --- 1. IMPORTAMOS TUS HERRAMIENTAS ACTUALIZADAS ---
from config import obtener_cliente
# Añadimos aprender_varios_pdfs y lista_archivos
from tools import (
    leer_contenido_pdf, 
    aprender_pdf, 
    aprender_varios_pdfs, 
    lista_archivos, 
    consultar_cerebro, 
    generar_mazo_anki
)

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Eriii", page_icon="🧠", layout="wide")

st.title("🧠 Asistente de Estudio IA")
st.markdown("Sube tus apuntes a la izquierda y pregunta lo que quieras.")

# --- BARRA LATERAL (Subir archivos) ---
with st.sidebar:
    st.header("📂 Tus Apuntes")
    
    # SECCIÓN 1: INVENTARIO (NUEVO)
    # Para ver qué tiene la IA en la cabeza
    with st.expander("Ver archivos memorizados"):
        if st.button("🔄 Actualizar lista"):
            archivos = lista_archivos() # Llamamos a la herramienta
            st.write(archivos)

    st.divider()

    # SECCIÓN 2: SUBIDA DE ARCHIVOS
    archivos_subidos = st.file_uploader("Sube tus PDFs", type=["pdf"], accept_multiple_files=True)
    
    if archivos_subidos:
        st.info(f"✅ {len(archivos_subidos)} archivos cargados.")
        
        # --- BOTÓN 1: MEMORIZAR (VERSIÓN LOTE / BATCH) ---
        if st.button("🧠 Memorizar TODOS"):
            with st.spinner("Procesando biblioteca completa..."):
                
                rutas_temporales = []
                barrita = st.progress(0)
                
                # A) PREPARACIÓN: Guardamos todo en disco temporal
                for i, pdf in enumerate(archivos_subidos):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(pdf.read())
                        rutas_temporales.append(tmp_file.name)
                    # Reseteamos el lector por si acaso
                    pdf.seek(0)
                    barrita.progress((i + 1) / len(archivos_subidos))

                # B) EJECUCIÓN: Llamamos a la herramienta DE LOTE
                try:
                    # Le pasamos la lista entera a la función nueva de tools.py
                    resultado = aprender_varios_pdfs(rutas_temporales)
                    st.success(resultado)
                except Exception as e:
                    st.error(f"Error aprendiendo: {e}")
                
                # C) LIMPIEZA
                for ruta in rutas_temporales:
                    try:
                        os.remove(ruta)
                    except:
                        pass

        st.divider()

        # --- BOTÓN 2: GENERAR ANKI ---
        cantidad = st.slider('Preguntas por archivo:', 1, 20, 5)
        
        if st.button("🃏 Crear Flashcards Anki"):
            with st.spinner("La IA está estudiando para crear el mazo..."):
                
                rutas_anki_temp = []
                
                # A) Preparación
                for pdf in archivos_subidos:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(pdf.read())
                        rutas_anki_temp.append(tmp_file.name)
                    pdf.seek(0)
                
                # B) Ejecución (Mazo Completo)
                ruta_final = generar_mazo_anki(rutas_anki_temp, cantidad)
                
                # C) Limpieza
                for ruta in rutas_anki_temp:
                    try:
                        os.remove(ruta)
                    except:
                        pass
                
                # D) Descarga
                if "Error" in ruta_final:
                    st.error(ruta_final)
                else:
                    st.success("¡Mazo creado con éxito!")
                    with open(ruta_final, "rb") as file:
                        st.download_button(
                            label="📥 Descargar Mazo .apkg",
                            data=file,
                            file_name="repaso_examen_completo.apkg",
                            mime="application/apkg"
                        )

# --- CHAT PRINCIPAL ---

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

if "chat_session" not in st.session_state:
    client = obtener_cliente()
    
    # --- 2. AQUÍ REGISTRAMOS LAS NUEVAS HERRAMIENTAS PARA EL CHAT ---
    mis_herramientas = [
        lista_archivos,        # Para que sepa decirte qué tiene
        aprender_varios_pdfs,  # Para que pueda aprender si se lo pides por texto
        consultar_cerebro,     # Para responder dudas
        generar_mazo_anki      # Para hacer anki por chat
    ]
    
    instrucciones = """
    Eres un tutor experto llamado Eriii.
    1. Si te preguntan qué sabes, usa 'lista_archivos'.
    2. Si te preguntan algo del temario, usa SIEMPRE 'consultar_cerebro'.
    3. Si te piden estudiar archivos, usa las herramientas de aprender.
    Sé didáctico, claro y amable.
    """
    
    st.session_state.chat_session = client.chats.create(
        model='models/gemini-1.5-flash', # Recomiendo flash 1.5 por estabilidad
        config=types.GenerateContentConfig(
            tools=mis_herramientas,
            system_instruction=instrucciones,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=False, 
                maximum_remote_calls=3
            )
        )
    )

# Pintar historial
for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["rol"]):
        st.markdown(mensaje["texto"])

# Input usuario
if pregunta := st.chat_input("Pregunta sobre tus apuntes..."):
    
    with st.chat_message("user"):
        st.markdown(pregunta)
    st.session_state.mensajes.append({"rol": "user", "texto": pregunta})

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            try:
                response = st.session_state.chat_session.send_message(pregunta)
                texto_respuesta = response.text
                st.markdown(texto_respuesta)
                st.session_state.mensajes.append({"rol": "assistant", "texto": texto_respuesta})
            except Exception as e:
                st.error(f"Error: {e}")