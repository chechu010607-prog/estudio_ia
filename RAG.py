import chromadb
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv


load_dotenv()


client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

chroma_client = chromadb.PersistentClient(path="./cerebro_digital")
coleccion = chroma_client.get_or_create_collection(name="mis_apuntes")

def generar_embedding(texto, tipo_tarea="RETRIEVAL_DOCUMENT"):
    """
    Convierte texto en números usando el SDK de Google.
    """
    try:
        
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=texto,
            config=types.EmbedContentConfig(
                task_type=tipo_tarea
            )
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"Error generando embedding: {e}")
        return []

def guardar_memoria(texto, nombre_archivo):
    """
    Corta el texto y lo guarda en la base de datos.
    """
    tamano_trozo = 1000
    trozos = [texto[i:i+tamano_trozo] for i in range(0, len(texto), tamano_trozo)]
    
    print(f"Guardando {len(trozos)} fragmentos de {nombre_archivo}")

    ids = []
    embeddings = []
    metadatos = []
    documentos = []

    for i, trozo in enumerate(trozos):
        id_unico = f"{nombre_archivo}_parte_{i}"
        
        vector = generar_embedding(trozo, "RETRIEVAL_DOCUMENT")
        
        if vector:
            ids.append(id_unico)
            embeddings.append(vector)
            metadatos.append({"fuente": nombre_archivo})
            documentos.append(trozo)

    if ids:
        coleccion.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatos,
            documents=documentos
        )
        return f"He memorizado {len(ids)} fragmentos del archivo {nombre_archivo}."
    else:
        return "Error: No se pudo generar ningún embedding."

def buscar_memoria(pregunta):
    """
    Busca información relevante.
    """
    vector_pregunta = generar_embedding(pregunta, "RETRIEVAL_QUERY")

    if not vector_pregunta:
        return "Error al procesar la pregunta."

    resultados = coleccion.query(
        query_embeddings=[vector_pregunta],
        n_results=3 
    )

    if not resultados['documents'] or not resultados['documents'][0]:
        return "No encontré información relevante en mis apuntes."

    contexto = "\n---\n".join(resultados['documents'][0])
    fuentes = [meta['fuente'] for meta in resultados['metadatas'][0]]
    
    return f"INFORMACIÓN ENCONTRADA EN ({set(fuentes)}):\n{contexto}"

def listar_archivos_guardados()->str:
    """
    Muestra qué archivos tiene el agente en su cerebro.
    """
    try:
        datos = coleccion.get()
        metadatos = datos['metadatas']
        nombres_unicos = set([meta['fuente'] for meta in metadatos])
        
        if not nombres_unicos:
            return "La memoria está vacía."
            
        return f"Archivos estudiados: {', '.join(nombres_unicos)}"
    except Exception as e:
        return f"Error leyendo memoria: {e}"