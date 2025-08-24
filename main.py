import streamlit as st
import openai
import os
import requests
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
import math
import time

# --- CONFIGURAÇÃO INICIAL ---
# Configura o título da página e o layout
st.set_page_config(page_title="Gerador de Animação IA", layout="centered")
st.title("🎙️ Transforme Áudio em Animação de Quadro Branco 🎨")
st.write("Faça o upload de um áudio e a IA criará uma animação ilustrando o que foi dito!")

# Carrega a chave da API do Replit Secrets
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    client = openai.OpenAI(api_key=openai.api_key)
except KeyError:
    st.error("Chave da API da OpenAI não encontrada! Por favor, configure a variável 'OPENAI_API_KEY' nos Secrets do Replit.")
    st.stop()

# Cria um diretório para armazenar arquivos temporários, se não existir
if not os.path.exists("temp"):
    os.makedirs("temp")

# --- FUNÇÕES AUXILIARES ---

# Função para transcrever o áudio usando a API Whisper da OpenAI
def transcribe_audio(audio_path):
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcription.text

# Função para dividir o texto em sentenças (uma abordagem simples)
def segment_text(text):
    sentences = text.replace('!', '.').replace('?', '.').split('.')
    # Filtra sentenças vazias e remove espaços extras
    return [s.strip() for s in sentences if s.strip()]

# Função para gerar uma imagem para cada sentença usando DALL-E 3
def generate_image_for_sentence(sentence, style_prompt, index):
    # Prompt de base para garantir o estilo de quadro branco
    base_prompt = (
        "Crie uma ilustração no estilo de animação de quadro branco (video scribing), "
        "minimalista, com desenhos de linha simples em preto sobre um fundo totalmente branco. "
        "A imagem deve ser limpa e clara, como se estivesse sendo desenhada em tempo real. "
        "Ilustre o seguinte conceito ou cena: "
    )

    # Combina o prompt base, a sentença e o estilo escolhido pelo usuário
    full_prompt = f"{base_prompt} '{sentence}'. {style_prompt}"

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        # Baixa a imagem e salva localmente
        image_data = requests.get(image_url).content
        image_path = os.path.join("temp", f"image_{index}.png")
        with open(image_path, "wb") as f:
            f.write(image_data)
        return image_path
    except Exception as e:
        st.error(f"Erro ao gerar imagem para: '{sentence}'. Erro: {e}")
        return None

# Função para criar o vídeo final com as imagens e o áudio
def create_video_from_images(image_paths, audio_path, output_path="final_animation.mp4"):
    audio_clip = AudioFileClip(audio_path)
    total_duration = audio_clip.duration
    duration_per_image = total_duration / len(image_paths)

    clips = []
    for image_path in image_paths:
        # Cria um clipe de imagem com a duração calculada
        clip = ImageClip(image_path).set_duration(duration_per_image)
        # Adiciona um efeito de fade-in para suavizar as transições
        clip = clip.fadein(0.5)
        clips.append(clip)

    # Concatena todos os clipes de imagem
    final_clip = concatenate_videoclips(clips, method="compose")
    # Define o áudio do clipe final
    final_clip = final_clip.set_audio(audio_clip)

    # Escreve o arquivo de vídeo
    final_clip.write_videofile(output_path, codec="libx264", fps=24)
    return output_path


# --- INTERFACE DO USUÁRIO (STREAMLIT) ---

# Campo para upload do arquivo de áudio
uploaded_file = st.file_uploader("Escolha um arquivo de áudio (MP3, WAV, M4A)...", type=["mp3", "wav", "m4a"])

# Seleção de estilo de ilustração
style_options = {
    "Padrão (Linhas Simples)": "Mantenha o estilo de desenho o mais simples possível.",
    "Estilo Cartoon": "Use um estilo de desenho animado (cartoon) amigável e expressivo.",
    "Mais Detalhado": "Adicione um pouco mais de detalhes e sombreamento leve, mas ainda mantendo a aparência de quadro branco."
}
selected_style = st.selectbox("Escolha um estilo para a animação:", options=list(style_options.keys()))

# Botão para iniciar o processo
# --- NOVO BLOCO DE CÓDIGO (MAIS ESTÁVEL) ---
if st.button("Gerar Animação ✨"):
    if uploaded_file is not None:
        # Salva o arquivo de áudio temporariamente
        audio_path = os.path.join("temp", uploaded_file.name)
        with open(audio_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Usa uma barra de progresso para todos os passos
        progress_bar = st.progress(0, text="Iniciando o processo...")

        # Passo 1: Transcrição
        progress_bar.progress(10, text="Passo 1/3: Transcrevendo o áudio...")
        transcribed_text = transcribe_audio(audio_path)
        with st.expander("Ver transcrição do áudio"):
            st.write(transcribed_text)
        
        sentences = segment_text(transcribed_text)
        if not sentences:
            st.error("Não foi possível extrair sentenças do áudio. Tente um áudio mais claro.")
            st.stop()

        # Passo 2: Geração de Imagens
        image_paths = []
        total_sentences = len(sentences)
        for i, sentence in enumerate(sentences):
            # Atualiza o texto e o progresso
            progress_text = f"Passo 2/3: Gerando imagem {i + 1}/{total_sentences}..."
            current_progress = 10 + int(80 * (i + 1) / total_sentences)
            progress_bar.progress(current_progress, text=progress_text)

            image_path = generate_image_for_sentence(sentence, style_options[selected_style], i)
            if image_path:
                image_paths.append(image_path)
        
        if not image_paths:
            st.error("Nenhuma imagem foi gerada. Verifique os logs de erro.")
            st.stop()

        # Passo 3: Criação do Vídeo
        progress_bar.progress(95, text="Passo 3/3: Montando o vídeo final...")
        video_path = create_video_from_images(image_paths, audio_path)
        
        # Finaliza a barra de progresso e mostra o resultado
        progress_bar.progress(100, text="Processo concluído!")
        time.sleep(1) # Dá um segundo para o usuário ver a conclusão
        progress_bar.empty() # Remove a barra de progresso

        st.success("Animação criada com sucesso!")
        st.header("Assista sua Animação!")
        
        video_file = open(video_path, 'rb')
        video_bytes = video_file.read()
        st.video(video_bytes)

        st.download_button(
            label="Baixar Vídeo 📥",
            data=video_bytes,
            file_name="animacao_gerada.mp4",
            mime="video/mp4"
        )
        
        # Limpa os arquivos temporários em segundo plano
        for file in os.listdir("temp"):
            os.remove(os.path.join("temp", file))
    
    else:
        st.warning("Por favor, faça o upload de um arquivo de áudio primeiro.")
