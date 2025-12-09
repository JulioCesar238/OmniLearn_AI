import streamlit as st
import google.generativeai as genai

# =======================================================
# 1. CONFIGURACIÓN DEL CEREBRO DE LA APP (PROMPT)
# =======================================================

# Instrucción del Sistema extraída y compilada de todos tus requerimientos:
SYSTEM_INSTRUCTION = """
Eres un sistema de gestión de aprendizaje avanzado y altamente estructurado llamado "OmniLearn".

Tu tarea principal es servir como tutor y generador de contenido con las siguientes reglas estrictas, basadas en los requerimientos del usuario:

1.  **Formato de Lección y Contenido:**
    * El contenido debe ser educativo y detallado, ajustándose estrictamente al tema, subtema y nivel solicitado (Básico, Medio o Alto).
    * Debes usar el tool de búsqueda (Search Grounding) para acceder a información en tiempo real y garantizar la precisión.
    * Cada lección debe terminar OBLIGATORIAMENTE con una sección de Referencias. Las referencias deben incluir los enlaces de las fuentes utilizadas por el Search Grounding.
    * Las referencias textuales y bibliográficas deben adherirse estrictamente a las normas de citación **APA**.

2.  **Imágenes y Diagramas:**
    * Aunque esta implementación simplifica la vista a un chat, si se te pide un diagrama o ilustración, debes responder con una descripción detallada y, si es posible, ofrecer un enlace de Wikimedia Commons con la referencia **APA** correspondiente, en lugar de generar una imagen directamente.

3.  **Evaluación (Cuestionario):**
    * Si el usuario pide un cuestionario, debe consistir **exactamente en 5 preguntas cerradas**.
    * Cada pregunta debe tener **exactamente 4 opciones** de respuesta.
    * Las opciones de respuesta deben tener una extensión aproximada similar (evita variaciones extremas en longitud).

4.  **Estructura del Curso:**
    * Responde a solicitudes de temas, subtemas y lecciones de manera estructurada y concisa.

5.  **Pensamiento Complejo:** Utiliza tu modo de "pensamiento complejo" para planificar la estructura del contenido, integrar la información de búsqueda de Google y estructurar las respuestas y cuestionarios de manera coherente y cumpliendo con el formato.
"""

# =======================================================
# 2. ESTRUCTURA DE STREAMLIT Y LÓGICA DE CHAT
# =======================================================

st.set_page_config(page_title="OmniLearn IA", page_icon="🧠")
st.title("🧠 OmniLearn IA")
st.write("Bienvenido a tu asistente de aprendizaje. Ingresa el tema, nivel y el formato que deseas (ej: 'Quiero un curso básico de física cuántica con 3 subtemas y un cuestionario').")

# 🛑 NOTA IMPORTANTE DE SEGURIDAD:
# La clave API se lee de los "Secrets" de Streamlit, NO se pega aquí.
try:
    # Esto busca la clave en los "Secretos" de Streamlit
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ No se encontró la API Key. Configúrala en los 'Secrets' de Streamlit.")
    st.stop() 

# Configuración del Modelo (Usando el Prompt definido)
model = genai.GenerativeModel(
    model_name="gemini-pro", # <--- ¡CAMBIO AQUÍ!
    system_instruction=SYSTEM_INSTRUCTION
)

# Historial del Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar mensajes anteriores en pantalla
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Capturar la pregunta del usuario
if prompt := st.chat_input("Escribe tu pregunta aquí..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        # Se usa el historial para mantener el contexto
        chat = model.start_chat(history=[
            {"role": m["role"], "parts": [m["content"]]} 
            for m in st.session_state.messages
        ])
        response = chat.send_message(prompt)
        
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "model", "content": response.text})
    except Exception as e:
        st.error(f"Ocurrió un error: {e}")           
