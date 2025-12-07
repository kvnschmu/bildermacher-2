from http.server import BaseHTTPRequestHandler
import json
import os
import base64
import google.generativeai as genai

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # 1. Body-Länge lesen und Daten empfangen
            content_length = int(self.headers.get('Content-Length', 0))
            body_str = self.rfile.read(content_length).decode('utf-8')
            body = json.loads(body_str)

            image_data = body.get('image')
            mime_type = body.get('mime_type')

            if not image_data:
                self.send_json_response(400, {'error': 'Kein Bild empfangen'})
                return

            # 2. API Key Setup
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                self.send_json_response(500, {'error': 'API Key fehlt'})
                return

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash-lite')

            # 3. Base64 Cleaning (Dein bewährter Fix)
            cleaned_image_data = image_data.strip().replace('\n', '').replace('\r', '')
            missing_padding = len(cleaned_image_data) % 4
            if missing_padding:
                cleaned_image_data += '=' * (4 - missing_padding)

            try:
                image_bytes = base64.b64decode(cleaned_image_data)
            except Exception:
                image_bytes = base64.urlsafe_b64decode(cleaned_image_data)

            # 4. Prompt
            system_prompt = """
Du bist ein Experte für KI-Prompts (Midjourney/Stable Diffusion).
        
        DEINE AUFGABE:
        Analysiere das hochgeladene Bild (Stil, Licht, Stimmung, technischer Look).
        Erstelle basierend darauf einen Prompt, der für eine "Image-to-Image" Generierung genutzt wird.
        
        WICHTIGE STRUKTUR DES OUTPUTS (Halte dich exakt daran):
        1. Beginne IMMER mit dem Satzteil: 
           "Ein [Adjektive passend zum Bildstil] Portrait der Person, basierend auf dem hochgeladenen Referenzbild. Detailgetreue Wiedergabe der Gesichtszüge..."
        2. Füge dann die spezifische Analyse des Bildes hinzu:
           - Beschreibe die exakte Beleuchtung (z.B. "sanfte Studiobeleuchtung", "harter Schatten", "Neonlicht").
           - Beschreibe den Hintergrund.
           - Beschreibe die Pose und den Ausdruck.
           - Beschreibe den künstlerischen Stil (z.B. "35mm Analogfilm", "Pixar-Stil", "Ölgemälde", "schwarz-weiß Fotografie").
        3. Ende mit dem Hinweis: 
           "Stil: [Kurze Zusammenfassung des Stils]."

        SPRACHE: Deutsch.
        
        Gib NUR den fertigen Prompt zurück.
            """

            # 5. Generierung
            image_parts = [{"mime_type": mime_type, "data": image_bytes}]
            response = model.generate_content([system_prompt, image_parts[0]])
            
            # Erfolgreiche Antwort senden
            self.send_json_response(200, {'prompt': response.text.strip()})

        except Exception as e:
            self.send_json_response(500, {'error': str(e)})

    # Hilfsfunktion für JSON-Antworten
    def send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        # CORS Header sind wichtig, falls Frontend & Backend getrennt laufen
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    # Wichtig für Preflight-Requests (CORS)
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
