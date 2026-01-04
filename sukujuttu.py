import streamlit as st
from st_audiorec import st_audiorec
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import datetime
import random

# --- ASETUKSET ---
st.set_page_config(page_title="Sukumuistot", page_icon="🎙️")

# Kysymyslista (näitä voi olla satoja)
KYSYMYKSET = [
    "Kuka oli paras ystäväsi lapsuudessa?",
    "Mitä söitte jouluna, kun olit pieni?",
    "Kerro ensimmäisestä koulupäivästäsi.",
    "Millainen oli isäsi/äitisi luonne?",
    "Mikä on ollut elämäsi onnellisin hetki?",
    "Millaista oli asua lapsuudenkodissasi?",
]

# --- SÄHKÖPOSTIN LÄHETYSFUNKTIO ---
def send_email(recipient_email, subject, body, audio_data):
    # Nämä haetaan piilotetuista asetuksista (st.secrets)
    sender_email = st.secrets["EMAIL_USER"]
    password = st.secrets["EMAIL_PASSWORD"]

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Liitetään äänitiedosto
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(audio_data)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="muisto.wav"')
    msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Virhe lähetyksessä: {e}")
        return False

# --- KÄYTTÖLIITTYMÄ ---

# Otsikko isosti
st.markdown("<h1 style='text-align: center; color: #2E86C1;'>🎙️ Sukumuistot Talteen</h1>", unsafe_allow_html=True)

st.divider()

# Päivän kysymyksen logiikka (arvotaan päivän mukaan tai satunnaisesti)
# Tässä yksinkertaistettu versio: Satunnainen kysymys napin painalluksella
if 'current_question' not in st.session_state:
    st.session_state['current_question'] = random.choice(KYSYMYKSET)

if st.button("🔄 Vaihda kysymys"):
    st.session_state['current_question'] = random.choice(KYSYMYKSET)

# Kysymys VALTAVALLA fontilla
st.markdown(f"""
<div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center;'>
    <h2 style='color: #333;'>{st.session_state['current_question']}</h2>
</div>
""", unsafe_allow_html=True)

st.write("") # Tyhjää tilaa

# --- NAUHOITUS ---
st.subheader("1. Nauhoita vastaus")
st.info("Paina punaista nappia aloittaaksesi ja lopettaaksesi.")

# Tämä luo nauhoitusnapin
wav_audio_data = st_audiorec()

# --- LÄHETYS ---
if wav_audio_data is not None:
    st.success("Nauhoitus onnistui! Voit kuunnella sen yläpuolelta.")
    
    st.subheader("2. Lähetä muisto talteen")
    
    with st.form("send_form"):
        # Vastaanottajan sähköposti (voi olla oma tai sukulaisen)
        recipient = st.text_input("Mihin sähköpostiin muisto lähetetään?", placeholder="esim. matti@suku.fi")
        submitted = st.form_submit_button("📤 LÄHETÄ MUISTO")
        
        if submitted and recipient:
            with st.spinner("Lähetetään muistoa..."):
                success = send_email(
                    recipient, 
                    f"Sukumuisto: {st.session_state['current_question']}", 
                    "Tässä on uusi nauhoitettu tarina liitteenä.", 
                    wav_audio_data
                )
                if success:
                    st.balloons()
                    st.success("Muisto lähetetty onnistuneesti sähköpostiin!")