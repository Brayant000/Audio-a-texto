from flask import Flask, render_template, request, send_file
import speech_recognition as sr
from pydub import AudioSegment, effects
import os
import uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    texto_completo = None
    nombre_transcripcion = None
    error = None

    if request.method == 'POST':
        archivo = request.files.get('audio')
        if not archivo or archivo.filename == '':
            return render_template('index.html', error="Archivo no válido.")

        ext = archivo.filename.rsplit('.', 1)[-1].lower()
        nombre_audio = f"{uuid.uuid4()}.{ext}"
        ruta_audio = os.path.join(UPLOAD_FOLDER, nombre_audio)
        archivo.save(ruta_audio)

        # Convertir a WAV con parámetros ideales para reconocimiento
        ruta_wav = ruta_audio.replace(f'.{ext}', '.wav')
        sonido = AudioSegment.from_file(ruta_audio)
        sonido = sonido.set_channels(1).set_frame_rate(16000)  
        sonido = effects.normalize(sonido)  # Normalizar volumen
        sonido.export(ruta_wav, format="wav")

        recognizer = sr.Recognizer()
        texto_completo = ""

        duracion = len(sonido)
        fragmento_duracion = 20000 if duracion < 360000 else 40000  

        for inicio in range(0, duracion, fragmento_duracion):
            fragmento = sonido[inicio:inicio + fragmento_duracion]
            frag_path = os.path.join(UPLOAD_FOLDER, f"frag_{inicio}.wav")
            fragmento.export(frag_path, format="wav")

            with sr.AudioFile(frag_path) as source:
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio_data = recognizer.record(source)
                    texto_completo += recognizer.recognize_google(audio_data, language="es-ES") + " "
                except sr.UnknownValueError:
                    texto_completo += "[Inaudible] "
                except sr.RequestError:
                    texto_completo += "[Error de conexión] "

            os.remove(frag_path)

        nombre_transcripcion = f"{uuid.uuid4()}.txt"
        with open(os.path.join(UPLOAD_FOLDER, nombre_transcripcion), "w", encoding="utf-8") as f:
            f.write(texto_completo)

        for f in [ruta_audio, ruta_wav]:
            if os.path.exists(f):
                os.remove(f)

    return render_template('index.html', texto=texto_completo, nombre_transcripcion=nombre_transcripcion, error=error)

@app.route('/descargar/<filename>')
def descargar(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)