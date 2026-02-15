# VoiceBridge - Guía de Instalación para Windows

Esta guía te llevará paso a paso por la instalación y configuración de VoiceBridge en Windows.

## 📋 Requisitos Previos

- Windows 10 o superior
- Python 3.9 o superior
- Git para Windows
- Conexión a internet

---

## 🚀 Instalación Paso a Paso

### 1. Instalar Python

Si no tienes Python instalado:

1. Descarga Python desde: https://www.python.org/downloads/
2. **IMPORTANTE**: Durante la instalación, marca la opción **"Add Python to PATH"**
3. Verifica la instalación:
   ```powershell
   python --version
   ```

### 2. Clonar el Repositorio

```powershell
# Abrir PowerShell o CMD
cd C:\Users\TuUsuario\Documents
git clone https://github.com/YoSoyDavidB/voicebridge.git
cd voicebridge
```

### 3. Instalar VoiceBridge

```powershell
# Instalar VoiceBridge en modo desarrollo
pip install -e .
```

Este comando instalará VoiceBridge y creará el comando global `voicebridge`.

### 4. Configurar API Keys

```powershell
# Copiar archivo de ejemplo
copy .env.example .env

# Editar con Notepad
notepad .env
```

**Edita las siguientes líneas con tus API keys:**

```bash
DEEPGRAM_API_KEY=tu_api_key_de_deepgram
OPENAI_API_KEY=tu_api_key_de_openai
ELEVENLABS_API_KEY=tu_api_key_de_elevenlabs
ELEVENLABS_VOICE_ID=tu_voice_id_clonado
```

**Dónde obtener las API keys:**
- **Deepgram**: https://deepgram.com/ (Gratis: $200 de crédito)
- **OpenAI**: https://platform.openai.com/ (Pay-as-you-go)
- **ElevenLabs**: https://elevenlabs.io/ (Gratis: 10k chars/mes, Creator $5/mes para voice cloning)

### 5. Verificar Instalación

```powershell
# Verificar que el comando funciona
voicebridge --help

# Verificar configuración
voicebridge check
```

---

## 🎤 Instalación de Dispositivo Virtual (VB-CABLE)

Para usar VoiceBridge con Teams/Zoom, necesitas un dispositivo de audio virtual.

### Instalación de VB-CABLE

1. **Descargar VB-CABLE**:
   - Ir a: https://vb-audio.com/Cable/
   - Descargar "VBCABLE_Driver_Pack43.zip"

2. **Instalar**:
   - Extraer el archivo ZIP
   - **Clic derecho** en `VBCABLE_Setup_x64.exe` (o `_x86.exe` si tienes Windows 32-bit)
   - Seleccionar **"Ejecutar como administrador"**
   - Clic en **"Install Driver"**
   - Esperar a que termine la instalación

3. **Reiniciar Windows** (importante!)

### Verificar Instalación

Después de reiniciar:

```powershell
voicebridge devices
```

Deberías ver algo como:

```
🔊 OUTPUT DEVICES (Speakers/Virtual Devices)
────────────────────────────────────────────────────────────────
ID 1: Speakers (Realtek High Definition Audio) [DEFAULT]
ID 4: CABLE Input (VB-Audio Virtual Cable) [VIRTUAL - Windows]
       Channels: 2
       Sample Rate: 48000 Hz
```

El **ID 4** sería tu dispositivo virtual (el número puede variar).

---

## ⚙️ Configuración Inicial

### Configurar Perfil para Testing

Primero, prueba que todo funciona:

```powershell
# Configurar modo testing (escucharás las traducciones)
voicebridge profile testing

# Iniciar VoiceBridge
voicebridge
```

Habla en español y deberías escuchar la traducción en inglés desde tus altavoces.

Presiona `Ctrl+C` para detener.

### Configurar Perfil para Teams/Zoom

Una vez que verificaste que funciona:

```powershell
# Listar dispositivos para encontrar el ID de VB-CABLE
voicebridge devices

# Configurar modo Teams con el ID de CABLE Input (ejemplo: 4)
voicebridge profile teams -d 4

# Verificar configuración
voicebridge profile
```

Deberías ver:

```
Profile: TEAMS/ZOOM MODE
  - Output device: 4
  - Audio playback: Disabled (silent)
  - Teams/Zoom captures from virtual device
```

---

## 🎯 Uso con Microsoft Teams/Zoom

### Configurar Teams

1. **Abrir Microsoft Teams**
2. Ir a **Configuración** (⚙️) → **Dispositivos**
3. En **Micrófono**, seleccionar: **"CABLE Output (VB-Audio Virtual Cable)"**
4. En **Altavoces**, dejar tu dispositivo de audio normal

### Configurar Zoom

1. **Abrir Zoom**
2. Ir a **Configuración** → **Audio**
3. En **Micrófono**, seleccionar: **"CABLE Output (VB-Audio Virtual Cable)"**
4. En **Altavoz**, dejar tu dispositivo de audio normal

### Iniciar VoiceBridge

```powershell
# Asegurarse de estar en modo Teams
voicebridge profile teams

# Iniciar VoiceBridge
voicebridge
```

Verás:

```
[CLI] 🔇 Audio output disabled (silent mode)
[Pipeline] 📝 Transcript logging enabled: C:\Users\TuUsuario\voicebridge_sessions\...
[Pipeline] 🔗 Connecting components with queues
```

### Unirse a una Reunión

1. **Mantén VoiceBridge ejecutándose**
2. **Únete a la reunión de Teams/Zoom**
3. **Habla en español** → Los participantes escuchan en inglés
4. **Tú no escuchas la traducción** (modo silencioso, evita confusión)

---

## 📝 Transcripciones Automáticas

Todas tus traducciones se guardan automáticamente en:

```
C:\Users\TuUsuario\voicebridge_sessions\
```

Formato: `session_YYYY-MM-DD_HH-MM-SS.md`

Puedes revisar estos archivos después de las reuniones para estudiar inglés.

---

## 🔄 Cambiar entre Modos

### Modo Testing (Probar antes de reunión)

```powershell
voicebridge profile testing
voicebridge
```

- ✅ Escuchas las traducciones
- ✅ Perfecto para probar

### Modo Teams (Durante reuniones)

```powershell
voicebridge profile teams
voicebridge
```

- ✅ Modo silencioso (no escuchas)
- ✅ Teams/Zoom captura el audio
- ✅ Sin confusión durante llamadas

---

## ❌ Solución de Problemas

### Teams no me escucha

**Problema**: Los participantes no escuchan nada

**Solución**:
1. Verificar que VoiceBridge esté ejecutándose
2. En Teams, verificar que el micrófono sea **"CABLE Output"**
3. Verificar el ID del dispositivo:
   ```powershell
   voicebridge devices
   voicebridge profile teams -d <ID_CORRECTO>
   ```

### Audio distorsionado

**Problema**: El audio suena distorsionado o robótico

**Solución**:
Editar `.env` y reducir el gain:
```bash
AUDIO_INPUT_GAIN=0.8  # O 0.5 si sigue distorsionado
```

### VB-CABLE no aparece

**Problema**: Después de instalar VB-CABLE, no aparece en los dispositivos

**Solución**:
1. Verificar que instalaste **como administrador**
2. **Reiniciar Windows** (obligatorio)
3. Verificar en Panel de Control → Sonido → Dispositivos de grabación
4. Si no aparece, reinstalar VB-CABLE

### Comando 'voicebridge' no encontrado

**Problema**: `voicebridge` no se reconoce como comando

**Solución**:
1. Verificar que Python esté en PATH:
   ```powershell
   python --version
   ```
2. Reinstalar VoiceBridge:
   ```powershell
   pip install -e .
   ```
3. Reiniciar PowerShell/CMD

### Error de permisos al instalar

**Problema**: Error al ejecutar `pip install -e .`

**Solución**:
```powershell
# Ejecutar PowerShell como Administrador
# Clic derecho en PowerShell → Ejecutar como administrador
pip install -e .
```

---

## 🎓 Tips para Windows

### Crear Acceso Directo

Puedes crear un archivo `.bat` para iniciar VoiceBridge rápidamente:

1. Crear archivo `start_voicebridge.bat`:
   ```batch
   @echo off
   cd C:\Users\TuUsuario\Documents\voicebridge
   voicebridge
   pause
   ```

2. Hacer doble clic en el archivo para iniciar VoiceBridge

### Iniciar Automáticamente con Windows

Para que VoiceBridge inicie con Windows:

1. Presionar `Win + R`
2. Escribir: `shell:startup`
3. Copiar tu archivo `.bat` a esa carpeta

---

## 🔗 Recursos Adicionales

- **Documentación completa**: `docs/VIRTUAL_AUDIO_SETUP.md`
- **Referencia rápida**: `QUICK_REFERENCE.md`
- **Setup rápido**: `QUICK_START_VIRTUAL_AUDIO.md`

---

## 📞 Soporte

Si encuentras problemas:

1. Revisar esta guía de solución de problemas
2. Verificar los logs de VoiceBridge en la consola
3. Revisar archivos en `voicebridge_sessions/` para ver si se está traduciendo

---

**¡Listo para traducir en tiempo real! 🎉**
