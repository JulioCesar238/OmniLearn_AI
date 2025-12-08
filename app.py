import streamlit as st
import google.generativeai as genai

# 1. Configuración de la página
st.set_page_config(page_title="OmniLearn IA", page_icon="🧠")
st.title("🧠 OmniLearn IA")
st.write("Bienvenido a tu asistente de aprendizaje. Pregúntame lo que quieras.")

# 2. Conexión segura con la API Key
try:
    # Esto busca la clave en los "Secretos" de Streamlit
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ No se encontró la API Key. Configúrala en los 'Secrets' de Streamlit.")
    st.stop() # Detiene la ejecución si no hay clave

# 3. Configuración del Modelo
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="Eres un profesor experto y paciente. Explica conceptos complejos de forma sencilla y con ejemplos."
)

# 4. Historial del Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar mensajes anteriores en pantalla
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Capturar la pregunta del usuario
if prompt := st.chat_input("Escribe tu pregunta aquí..."):
    # Mostrar lo que el usuario escribió
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Generar y mostrar respuesta
    try:
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
